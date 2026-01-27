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

# Try to import Gemini Agent Orchestrator (Function Calling)
try:
    from gemini_agent_orchestrator import get_orchestrator

    ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    ORCHESTRATOR_AVAILABLE = False
    print(f"⚠️  Gemini Agent Orchestrator not available: {e}")

# Try to import TaskLoop (Ralph-style execution)
try:
    from task_loop import get_task_loop

    TASK_LOOP_AVAILABLE = True
except ImportError as e:
    TASK_LOOP_AVAILABLE = False
    print(f"⚠️  TaskLoop not available: {e}")

# Try to import API v1 Router (from src/youtube_extension)
try:
    from youtube_extension.backend.api.v1.router import router as api_v1_router
    API_V1_AVAILABLE = True
except ImportError as e:
    API_V1_AVAILABLE = False
    print(f"⚠️  API v1 Router not available: {e}")


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


class VideoExecuteRequest(BaseModel):
    """Request body for /execute_video endpoint (E2E autonomous execution)"""

    video_url: str
    goal: Optional[str] = "Build the application shown in the video"
    target_project: str = "uvai-730bb"
    auto_deploy: bool = False


class LearnAndApplyRequest(BaseModel):
    """Request body for /learn_and_apply endpoint (Ralph-style learning)

    This endpoint LEARNS from video content and APPLIES changes to UVAI itself.
    Unlike execute_video which deploys external apps, this improves UVAI.
    """

    video_url: str
    target_component: str = "prescient-twin"
    auto_commit: bool = False  # Set True to commit changes automatically


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

# Add CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://uvai.io",
        "https://www.uvai.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 Router
if API_V1_AVAILABLE:
    app.include_router(api_v1_router)
    print("✅ API v1 Router mounted at /api/v1")


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


@app.post("/analyze_video_v2")
async def analyze_video_with_orchestrator(request: VideoAnalyzeRequest):
    """
    Analyze a video URL using Gemini Function Calling with MCP Agent pipeline.

    This is the enhanced version that:
    1. Extracts YouTube transcript (if available)
    2. Uses Gemini Function Calling to orchestrate analysis
    3. Generates actionable tasks from video content

    Use this for full video-to-action transformation.
    """
    if not ORCHESTRATOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Gemini Agent Orchestrator not available. Check installation.",
        )

    try:
        orchestrator = get_orchestrator()

        if not orchestrator.available:
            raise HTTPException(
                status_code=503,
                detail="Orchestrator not initialized. Check API key.",
            )

        # Use the orchestrator for function calling based analysis
        result = await orchestrator.analyze_video(
            request.video_url,
            request.task or "summarize this video and extract key insights",
        )

        if result["success"]:
            # Record lesson
            record_lesson(
                f"Analyzed video with Function Calling: {request.video_url[:50]}",
                {
                    "video_url": request.video_url,
                    "method": result.get("method"),
                    "function_calls": len(result.get("function_calls", [])),
                },
            )

        return {
            "status": "completed" if result["success"] else "failed",
            "video_url": request.video_url,
            "method": result.get("method", "gemini_function_calling"),
            "model": result.get("model", "gemini-2.5-flash"),
            "analysis": result.get("analysis"),
            "function_calls": result.get("function_calls", []),
            "processing_time_ms": result.get("processing_time_ms"),
            "error": result.get("error"),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Video analysis v2 failed: {str(e)}"
        )


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


# --- E2E Autonomous Execution (The "Advisory Hump" Breaker) ---


@app.post("/execute_video")
async def execute_video(request: VideoExecuteRequest):
    """
    🚀 E2E AUTONOMOUS EXECUTION - This endpoint BUILDS, not advises.

    Unlike /analyze_video which provides summaries and suggestions,
    this endpoint:
    1. Watches the tutorial video
    2. Extracts what needs to be built
    3. GENERATES THE ACTUAL CODE
    4. Optionally deploys to Cloud Run
    5. Returns deployment-ready assets or live URL

    This is the "Advisory Hump" breaker - transforming advice into action.

    Example:
    - Input: YouTube tutorial URL
    - Output: Generated code + deployment URL

    Set auto_deploy=true to deploy immediately to Cloud Run.
    """
    if not ORCHESTRATOR_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Gemini Agent Orchestrator not available. Check google-genai installation.",
        )

    try:
        orchestrator = get_orchestrator()
        if not orchestrator.available:
            raise HTTPException(
                status_code=503,
                detail="Orchestrator not initialized. Check GOOGLE_API_KEY.",
            )

        result = await orchestrator.execute_video(
            video_url=request.video_url,
            goal=request.goal,
            target_project=request.target_project,
            auto_deploy=request.auto_deploy,
        )

        if not result.get("success"):
            return {
                "status": "failed",
                "error": result.get("error"),
                "video_url": request.video_url,
                "method": result.get("method"),
            }

        return {
            "status": "completed",
            "mode": "E2E_AUTONOMOUS_EXECUTION",
            "video_url": request.video_url,
            "goal": request.goal,
            "steps_executed": result.get("steps_executed", []),
            "generated_app": result.get("generated_app"),
            "code_content": result.get("code_content"),
            "deployment": result.get("deployment"),
            "revenue_stream": result.get("revenue_stream"),
            "processing_time_ms": result.get("processing_time_ms"),
            "model": result.get("model"),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Autonomous execution failed: {str(e)}"
        )


# --- Ralph-Style Learning (The Correct Pattern) ---


@app.post("/learn_and_apply")
async def learn_and_apply(request: LearnAndApplyRequest):
    """
    🎓 LEARN AND APPLY - Ralph-style autonomous improvement.

    This endpoint LEARNS from video content and APPLIES changes to UVAI itself.
    Unlike /execute_video which deploys external apps, this IMPROVES UVAI.

    The key insight: Don't deploy summary pages about what we learned.
    Instead, IMPLEMENT the learnings directly in our codebase.

    Flow:
    1. Extract video transcript
    2. Identify actionable implementation tasks
    3. For each task: Implement → Test → (Commit)
    4. Return results with actual code changes made

    Example use case:
    - Video about new Google UCP protocol
    - Output: New UCP integration code in prescient-twin
    - NOT: HTML landing page about UCP
    """
    if not TASK_LOOP_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="TaskLoop not available. Check google-genai installation.",
        )

    try:
        # Get transcript first
        from youtube_transcript_api import YouTubeTranscriptApi
        import re

        # Extract video ID
        video_id_match = re.search(
            r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", request.video_url
        )
        if not video_id_match:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        video_id = video_id_match.group(1)

        # Get transcript
        api = YouTubeTranscriptApi()
        transcript_data = api.fetch(video_id)
        transcript_text = " ".join([entry.text for entry in transcript_data])

        # Run the TaskLoop
        task_loop = get_task_loop()
        result = await task_loop.run(
            content=transcript_text,
            content_type="video_transcript",
            target_component=request.target_component,
            auto_commit=request.auto_commit,
        )

        return {
            "status": "completed" if result.success else "partial",
            "mode": "LEARN_AND_APPLY",
            "video_url": request.video_url,
            "target_component": request.target_component,
            "tasks_completed": result.tasks_completed,
            "tasks_failed": result.tasks_failed,
            "total_tasks": result.total_tasks,
            "files_modified": result.files_modified,
            "commits_made": result.commits_made,
            "lessons_learned": result.lessons_learned,
            "duration_seconds": result.duration_seconds,
            "message": (
                f"Applied {result.tasks_completed} improvements to {request.target_component}"
                if result.success
                else f"Partially applied: {result.tasks_completed}/{result.total_tasks} tasks"
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Learn and apply failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    print(f"🌐 Starting Prescient Twin on port {port}")

    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
