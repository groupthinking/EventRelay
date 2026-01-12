"""
Prescient Twin - FastAPI Entry Point

The "Nerve Center" that connects the agent ecosystem to the outside world.
Exposes endpoints for:
- /evolve: Trigger agent evolution tasks
- /tools: Manage evolved tools
- /stats: Get system statistics
- /health: Health check
"""

import os
import sys
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add parent directory to path for video processor imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import our modules
from router import HybridRouter, ModelBrain
from memory import get_tool_stats, get_lessons, record_lesson
from sandbox_tool import SafeSandboxTool

# Try to import video processor
try:
    from youtube_extension.backend.enhanced_video_processor import (
        get_enhanced_video_processor,
    )

    VIDEO_PROCESSOR_AVAILABLE = True
except ImportError as e:
    VIDEO_PROCESSOR_AVAILABLE = False
    print(f"⚠️  Video processor not available: {e}")

# Try to import Gemini video analyzer (native URL context)
try:
    from gemini_video_analyzer import get_gemini_video_analyzer

    GEMINI_ANALYZER_AVAILABLE = True
except ImportError as e:
    GEMINI_ANALYZER_AVAILABLE = False
    print(f"⚠️  Gemini video analyzer not available: {e}")

# Try to import dogfooding pipeline
try:
    from dogfooding_pipeline import get_dogfooding_pipeline

    DOGFOODING_AVAILABLE = True
except ImportError as e:
    DOGFOODING_AVAILABLE = False
    print(f"⚠️  Dogfooding pipeline not available: {e}")


# --- Request/Response Models ---


class EvolveRequest(BaseModel):
    """Request body for /evolve endpoint"""

    task: str
    force_brain: Optional[str] = None


class ExecuteRequest(BaseModel):
    """Request body for /execute endpoint"""

    code: str


class LessonRequest(BaseModel):
    """Request body for /lesson endpoint"""

    lesson: str
    context: Optional[dict] = None


class VideoProcessRequest(BaseModel):
    """Request body for /process_video endpoint"""

    youtube_url: str
    include_transcript: bool = True
    include_ai_analysis: bool = True


class VideoAnalyzeRequest(BaseModel):
    """Request body for /analyze_video endpoint (native Gemini URL context)"""

    video_url: str
    task: Optional[str] = None  # Optional custom task/question


class DogfoodRequest(BaseModel):
    """Request body for /dogfood endpoint (self-improvement)"""

    video_url: str
    target_component: str = "frontend"  # frontend, backend, or shared


# --- Lifespan Management ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    print("🚀 Prescient Twin Starting...")

    # Initialize components - enable full agents if ENABLE_FULL_AGENTS=true
    enable_full = os.getenv("ENABLE_FULL_AGENTS", "false").lower() == "true"
    app.state.router = HybridRouter(enable_agents=enable_full)
    app.state.sandbox = SafeSandboxTool()

    print("✅ Prescient Twin Ready")
    print(f"📊 Available brains: {app.state.router.get_stats()['available_brains']}")

    yield

    print("👋 Prescient Twin Shutting Down...")


# --- FastAPI App ---

app = FastAPI(
    title="Prescient Twin",
    description="Self-evolving agent ecosystem with hybrid model routing",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Endpoints ---


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "prescient-twin"}


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "router": app.state.router.get_stats(),
        "memory": get_tool_stats(),
        "lessons": len(get_lessons(limit=100)),
    }


@app.post("/evolve")
async def trigger_evolution(request: EvolveRequest, background_tasks: BackgroundTasks):
    """
    The Dashboard calls this endpoint to start an evolution job.
    Runs in background so the API doesn't hang.
    """
    force_brain = None
    if request.force_brain:
        try:
            force_brain = ModelBrain(request.force_brain)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid brain: {request.force_brain}. Valid options: gemini, claude, grok, local",
            )

    # For now, run synchronously for simplicity
    # In production, use background_tasks.add_task()
    result = app.state.router.route(request.task, force_brain=force_brain)

    return {
        "status": "completed" if result["success"] else "failed",
        "brain_used": result["brain"],
        "result": result["result"],
        "stats": result["stats"],
    }


@app.post("/execute")
async def execute_in_sandbox(request: ExecuteRequest):
    """
    Execute code in the E2B sandbox.
    Safe remote execution - nothing touches local filesystem.
    """
    result = app.state.sandbox.forward(request.code)
    return {"output": result}


@app.post("/lesson")
async def record_new_lesson(request: LessonRequest):
    """Record a lesson learned by the agent"""
    record_lesson(request.lesson, request.context)
    return {"status": "recorded", "lesson": request.lesson[:50] + "..."}


@app.get("/lessons")
async def get_recent_lessons(limit: int = 10):
    """Get recent lessons"""
    return {"lessons": get_lessons(limit=limit)}


@app.get("/tools")
async def list_evolved_tools():
    """List all evolved tools"""
    stats = get_tool_stats()
    return {"total": stats["total_tools"], "tools": stats["tools"]}


@app.post("/process_video")
async def process_video(
    request: VideoProcessRequest, background_tasks: BackgroundTasks
):
    """
    Process a YouTube video using the enhanced video processor.
    Returns multimodal AI analysis including transcript, insights, and action items.
    """
    if not VIDEO_PROCESSOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Video processor not available. Check server logs for import errors.",
        )

    try:
        processor = get_enhanced_video_processor()
        result = await processor.process_video(request.youtube_url)

        # Record this as a lesson for the AI
        record_lesson(
            f"Processed video: {result.get('metadata', {}).get('title', 'Unknown')}",
            {"url": request.youtube_url, "result_keys": list(result.keys())},
        )

        return {
            "status": "completed",
            "video_url": request.youtube_url,
            "metadata": result.get("metadata", {}),
            "transcript": (
                result.get("transcript", {}) if request.include_transcript else None
            ),
            "ai_analysis": (
                result.get("ai_analysis", {}) if request.include_ai_analysis else None
            ),
            "markdown_summary": result.get("markdown", ""),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Video processing failed: {str(e)}"
        )


@app.post("/analyze_video")
async def analyze_video_with_gemini(request: VideoAnalyzeRequest):
    """
    Analyze a video URL using native Gemini URL context.
    This uses Vertex AI's URL context capability for direct video analysis.
    No need for smolagents - uses google-genai SDK directly.
    """
    if not GEMINI_ANALYZER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Gemini video analyzer not available. Check GOOGLE_API_KEY.",
        )

    try:
        analyzer = get_gemini_video_analyzer()

        if not analyzer.available:
            raise HTTPException(
                status_code=503,
                detail="Gemini analyzer not initialized. Check API key.",
            )

        if request.task:
            result = analyzer.analyze_with_instructions(request.video_url, request.task)
        else:
            result = analyzer.analyze_video_url(request.video_url)

        if result["success"]:
            # Record lesson
            record_lesson(
                f"Analyzed video with Gemini URL context: {request.video_url[:50]}",
                {"video_url": request.video_url, "model": result.get("model")},
            )

        return {
            "status": "completed" if result["success"] else "failed",
            "video_url": request.video_url,
            "model": result.get("model", "gemini-2.5-flash"),
            "analysis": result.get("result"),
            "url_metadata": result.get("url_context_metadata"),
            "error": result.get("error"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}")


@app.post("/dogfood")
async def run_dogfooding(request: DogfoodRequest):
    """
    Dogfooding endpoint: Analyze a video and generate self-improvement suggestions.

    This is the closed-loop self-enhancement endpoint:
    1. Analyzes the video for relevant patterns/techniques
    2. Extracts actionable improvement suggestions
    3. Generates code patch templates
    4. Records lessons for future reference

    Use this to make UVAI improve itself based on tutorial/demo videos.
    """
    if not DOGFOODING_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Dogfooding pipeline not available. Check installation.",
        )

    try:
        pipeline = get_dogfooding_pipeline()

        result = pipeline.analyze_for_improvements(
            request.video_url, request.target_component
        )

        if not result.get("success"):
            return {
                "status": "failed",
                "error": result.get("error"),
                "video_url": request.video_url,
            }

        return {
            "status": "completed",
            "video_url": request.video_url,
            "target_component": request.target_component,
            "suggestions_count": len(result.get("suggestions", [])),
            "patches_count": len(result.get("code_patches", [])),
            "suggestions": result.get("suggestions", [])[:10],  # Top 10
            "patches": result.get("code_patches", [])[:5],  # Top 5
            "analysis_excerpt": result.get("analysis", "")[:1000],  # First 1000 chars
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dogfooding failed: {str(e)}")


@app.get("/dogfood/summary")
async def get_dogfood_summary():
    """Get summary of all dogfooding enhancements."""
    if not DOGFOODING_AVAILABLE:
        raise HTTPException(
            status_code=503, detail="Dogfooding pipeline not available."
        )

    pipeline = get_dogfooding_pipeline()
    return pipeline.get_enhancement_summary()


# --- Main ---

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    print(f"🌐 Starting Prescient Twin on port {port}")

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
