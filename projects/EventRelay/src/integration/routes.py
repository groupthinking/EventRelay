"""
Integration API Routes
----------------------
FastAPI routes for all external service integrations.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


# ============ Request/Response Models ============

class VideoAnalysisRequest(BaseModel):
    video_url: str
    prompt: Optional[str] = "Analyze this video and extract key events"
    generate_code: bool = False
    target_framework: str = "nextjs"
    media_resolution: str = "high"  # "low" or "high" - high for text-heavy videos
    thinking_level: str = "high"    # "low" or "high" - high for complex reasoning


class TechnicalBreakdownRequest(BaseModel):
    video_url: str


class VideoQuestionRequest(BaseModel):
    video_url: str
    question: str


class YouTubeMetadataRequest(BaseModel):
    video_url: str
    include_transcript: bool = True


class DeployRequest(BaseModel):
    source_dir: Optional[str] = None
    github_repo: Optional[str] = None
    branch: str = "main"
    project_name: str
    production: bool = False
    env_vars: Optional[dict] = None


class StripeProductRequest(BaseModel):
    name: str
    description: str = ""
    price_cents: int
    currency: str = "usd"
    recurring_interval: Optional[str] = None  # "month" or "year"


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str
    mode: str = "payment"
    customer_email: Optional[str] = None


class SupabaseQueryRequest(BaseModel):
    table: str
    operation: str  # "select", "insert", "update", "delete"
    data: Optional[dict] = None
    filters: Optional[dict] = None
    columns: str = "*"


# ============ Gemini Video Routes (Gemini 3 Pro Preview) ============

@router.post("/gemini/analyze")
async def analyze_video_with_gemini(request: VideoAnalysisRequest):
    """
    Analyze video content using Gemini 3 Pro Preview.
    
    - media_resolution: 'low' (70 tokens/frame) or 'high' (280 tokens/frame)
      Use 'high' for text-heavy videos (code tutorials, slides)
    - thinking_level: 'low' for simple tasks, 'high' for complex reasoning
    """
    from src.integrations.gemini_video import GeminiVideoService
    
    try:
        service = GeminiVideoService()
        
        if request.generate_code:
            code = await service.generate_code_from_video(
                request.video_url,
                request.target_framework
            )
            await service.close()
            return {"code": code, "framework": request.target_framework}
        
        result = await service.analyze_video(
            request.video_url, 
            request.prompt,
            media_resolution=request.media_resolution,
            thinking_level=request.thinking_level
        )
        await service.close()
        
        return {
            "summary": result.summary,
            "key_events": result.key_events,
            "timestamps": result.timestamps,
            "apis_detected": result.apis_detected,
            "model": "gemini-2.5-pro"
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/gemini/technical-breakdown")
async def extract_technical_breakdown(request: TechnicalBreakdownRequest):
    """
    Extract technical breakdown from video including APIs, endpoints, and capabilities.
    Optimized for code tutorials and technical demos using Gemini 3's high resolution.
    """
    from src.integrations.gemini_video import GeminiVideoService
    
    try:
        service = GeminiVideoService()
        result = await service.extract_technical_breakdown(request.video_url)
        await service.close()
        
        return {
            "summary": result.summary,
            "apis_detected": result.apis_detected,
            "key_events": result.key_events,
            "timestamps": result.timestamps,
            "model": "gemini-2.5-pro"
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/gemini/transcript")
async def extract_transcript(request: TechnicalBreakdownRequest):
    """Extract timestamped transcript with speaker detection."""
    from src.integrations.gemini_video import GeminiVideoService
    
    try:
        service = GeminiVideoService()
        result = await service.extract_transcript_with_timestamps(request.video_url)
        await service.close()
        return {"transcript": result, "model": "gemini-2.5-pro"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/gemini/question")
async def answer_video_question(request: VideoQuestionRequest):
    """Answer a specific question based on video content."""
    from src.integrations.gemini_video import GeminiVideoService
    
    try:
        service = GeminiVideoService()
        answer = await service.answer_video_question(request.video_url, request.question)
        await service.close()
        return {"answer": answer, "question": request.question, "model": "gemini-2.5-pro"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ============ YouTube API Routes ============

@router.post("/youtube/metadata")
async def get_youtube_metadata(request: YouTubeMetadataRequest):
    """Get video metadata and optionally transcript."""
    from src.integrations import YouTubeAPIService
    
    try:
        service = YouTubeAPIService()
        video_id = service.extract_video_id(request.video_url)
        
        metadata = await service.get_video_metadata(video_id)
        response = {
            "video_id": metadata.video_id,
            "title": metadata.title,
            "description": metadata.description,
            "channel": metadata.channel_title,
            "duration": metadata.duration,
            "views": metadata.view_count,
            "likes": metadata.like_count,
            "tags": metadata.tags,
            "thumbnail": metadata.thumbnail_url
        }
        
        if request.include_transcript:
            try:
                transcript = await service.get_full_transcript_text(video_id)
                response["transcript"] = transcript
            except Exception:
                response["transcript"] = None
                response["transcript_error"] = "Transcript not available"
        
        await service.close()
        return response
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/youtube/search")
async def search_youtube(query: str, max_results: int = 10):
    """Search YouTube videos."""
    from src.integrations import YouTubeAPIService
    
    try:
        service = YouTubeAPIService()
        results = await service.search_videos(query, max_results)
        await service.close()
        return {"results": results}
    except Exception as e:
        raise HTTPException(500, str(e))


# ============ Vercel Deployment Routes ============

@router.post("/vercel/deploy")
async def deploy_to_vercel(request: DeployRequest):
    """Deploy to Vercel from local dir or GitHub."""
    from src.integrations import VercelDeployService
    
    try:
        service = VercelDeployService()
        
        if request.github_repo:
            result = await service.deploy_from_github(
                request.github_repo,
                request.branch,
                request.project_name
            )
        elif request.source_dir:
            result = await service.deploy_directory(
                request.source_dir,
                request.project_name,
                request.production
            )
        else:
            raise HTTPException(400, "Either source_dir or github_repo required")
        
        # Set env vars if provided
        if request.env_vars:
            await service.set_env_vars(result.project_name, request.env_vars)
        
        await service.close()
        
        return {
            "deployment_id": result.deployment_id,
            "url": result.url,
            "state": result.state,
            "project": result.project_name
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/vercel/projects")
async def list_vercel_projects():
    """List all Vercel projects."""
    from src.integrations import VercelDeployService
    
    try:
        service = VercelDeployService()
        projects = await service.list_projects()
        await service.close()
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(500, str(e))


# ============ Stripe Payment Routes ============

@router.post("/stripe/product")
async def create_stripe_product(request: StripeProductRequest):
    """Create a product with price."""
    from src.integrations import StripePaymentService
    
    try:
        service = StripePaymentService()
        
        product = await service.create_product(request.name, request.description)
        price = await service.create_price(
            product.id,
            request.price_cents,
            request.currency,
            request.recurring_interval
        )
        
        await service.close()
        
        return {
            "product_id": product.id,
            "product_name": product.name,
            "price_id": price.id,
            "amount": price.unit_amount,
            "currency": price.currency
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/stripe/checkout")
async def create_checkout_session(request: CheckoutRequest):
    """Create a Stripe checkout session."""
    from src.integrations import StripePaymentService
    
    try:
        service = StripePaymentService()
        session = await service.create_checkout_session(
            request.price_id,
            request.success_url,
            request.cancel_url,
            request.mode,
            request.customer_email
        )
        await service.close()
        
        return {
            "session_id": session.id,
            "checkout_url": session.url
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/stripe/products")
async def list_stripe_products():
    """List all Stripe products."""
    from src.integrations import StripePaymentService
    
    try:
        service = StripePaymentService()
        products = await service.list_products()
        await service.close()
        
        return {
            "products": [
                {"id": p.id, "name": p.name, "price_id": p.default_price_id}
                for p in products
            ]
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ============ Supabase Database Routes ============

@router.post("/supabase/query")
async def execute_supabase_query(request: SupabaseQueryRequest):
    """Execute a Supabase database operation."""
    from src.integrations import SupabaseDBService
    
    try:
        service = SupabaseDBService()
        
        if request.operation == "select":
            result = await service.select(
                request.table,
                request.columns,
                request.filters
            )
        elif request.operation == "insert":
            if not request.data:
                raise HTTPException(400, "Data required for insert")
            result = await service.insert(request.table, request.data)
        elif request.operation == "update":
            if not request.data or not request.filters:
                raise HTTPException(400, "Data and filters required for update")
            result = await service.update(request.table, request.data, request.filters)
        elif request.operation == "delete":
            if not request.filters:
                raise HTTPException(400, "Filters required for delete")
            result = await service.delete(request.table, request.filters)
        else:
            raise HTTPException(400, f"Unknown operation: {request.operation}")
        
        await service.close()
        
        if result.error:
            raise HTTPException(400, result.error)
        
        return {"data": result.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ============ OpenAI Voice Agent Routes ============

class TranscribeRequest(BaseModel):
    audio_base64: str  # Base64 encoded audio
    model: str = "gpt-4o-transcribe"
    language: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    model: str = "gpt-4o-mini-tts"
    voice: str = "alloy"  # alloy, echo, fable, onyx, nova, shimmer
    response_format: str = "mp3"
    speed: float = 1.0


class VoiceToVoiceRequest(BaseModel):
    audio_base64: str
    system_prompt: str = "You are a helpful assistant."
    voice: str = "alloy"


@router.post("/openai/transcribe")
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcribe audio to text using OpenAI's latest models.
    
    Models:
    - gpt-4o-transcribe: High accuracy
    - gpt-4o-mini-transcribe: Cost efficient
    """
    from src.integrations.openai_voice import OpenAIVoiceService
    import base64
    
    try:
        service = OpenAIVoiceService()
        audio_data = base64.b64decode(request.audio_base64)
        
        result = await service.transcribe_audio(
            audio_data,
            model=request.model,
            language=request.language
        )
        await service.close()
        
        return {
            "text": result.text,
            "language": result.language,
            "duration": result.duration,
            "model": request.model
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/openai/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using OpenAI's TTS models.
    Returns base64 encoded audio.
    
    Models: gpt-4o-mini-tts, tts-1, tts-1-hd
    Voices: alloy, echo, fable, onyx, nova, shimmer
    """
    from src.integrations.openai_voice import OpenAIVoiceService
    import base64
    
    try:
        service = OpenAIVoiceService()
        result = await service.text_to_speech(
            request.text,
            model=request.model,
            voice=request.voice,
            response_format=request.response_format,
            speed=request.speed
        )
        await service.close()
        
        return {
            "audio_base64": base64.b64encode(result.audio_data).decode(),
            "format": result.format,
            "model": request.model,
            "voice": request.voice
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/openai/voice-to-voice")
async def voice_to_voice_chained(request: VoiceToVoiceRequest):
    """
    Complete voice-to-voice pipeline (Chained architecture):
    1. gpt-4o-transcribe → text
    2. gpt-4.1 → response text
    3. gpt-4o-mini-tts → audio
    
    Returns both text response and audio.
    """
    from src.integrations.openai_voice import OpenAIVoiceService
    import base64
    
    try:
        service = OpenAIVoiceService()
        audio_data = base64.b64decode(request.audio_base64)
        
        response_text, audio_result = await service.voice_to_voice_chained(
            audio_data,
            system_prompt=request.system_prompt,
            voice=request.voice
        )
        await service.close()
        
        return {
            "response_text": response_text,
            "audio_base64": base64.b64encode(audio_result.audio_data).decode(),
            "format": audio_result.format,
            "pipeline": "transcribe → gpt-4.1 → tts"
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ============ Health Check ============

@router.get("/health")
async def integrations_health():
    """Check status of all integrations."""
    status = {
        "gemini": bool(os.environ.get("GEMINI_API_KEY")),
        "youtube": bool(os.environ.get("YOUTUBE_API_KEY")),
        "vercel": bool(os.environ.get("VERCEL_TOKEN")),
        "stripe": bool(os.environ.get("STRIPE_SECRET_KEY")),
        "supabase": bool(os.environ.get("SUPABASE_URL")),
        "openai": bool(os.environ.get("OPENAI_API_KEY"))
    }
    return {
        "status": "healthy" if all(status.values()) else "partial",
        "services": status,
        "models": {
            "gemini": "gemini-2.5-pro",
            "openai_transcribe": "gpt-4o-transcribe",
            "openai_tts": "gpt-4o-mini-tts",
            "openai_chat": "gpt-4.1"
        }
    }
