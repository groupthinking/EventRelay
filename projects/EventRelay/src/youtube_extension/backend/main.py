#!/usr/bin/env python3
"""
FastAPI Backend for YouTube Extension
=====================================

ENHANCED WITH MCP + A2A ORCHESTRATION

This is the main FastAPI application that provides:
1. REST API endpoints for chat and video processing
2. WebSocket support for real-time communication
3. Integration with existing MCP services
4. CORS support for frontend integration
5. **NEW: MCP + A2A Orchestration for On-Demand Software Deployment**
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
import json
import logging
import os
import sys
import hashlib
import time
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import socket
import urllib.parse
import urllib.request

# Path setup for imports
project_root = Path(__file__).parent.parent

# Configure logging (must be before any logger usage)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Real API integration
try:
    from .real_api_endpoints import setup_real_api_endpoints, SERVICES_INITIALIZED
    HAS_REAL_API_SERVICES = SERVICES_INITIALIZED
except ImportError as e:
    logger.warning(f"Real API services not available: {e}")
    HAS_REAL_API_SERVICES = False
    setup_real_api_endpoints = None

try:
    from .services.real_youtube_api import get_youtube_service
except ImportError:
    get_youtube_service = None

try:
    from .services.video_processing_service import resolve_deployment_target
except ImportError:
    def resolve_deployment_target(target: Optional[str]) -> Dict[str, Any]:
        normalized = (target or "vercel").strip().lower()
        return {"requested": normalized, "resolved": "vercel", "alias_applied": normalized != "vercel"}

# --- Runtime mandatory environment variable guard ---
REQUIRED_ENV_VARS = ["YOUTUBE_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]
MISSING_ENV_VARS = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]

# Define custom error for missing dependency so that callers can raise if needed

class MissingDependencyError(RuntimeError):
    """Raised when a runtime dependency (e.g., mandatory environment var) is missing."""

if MISSING_ENV_VARS:
    # Log at startup but do NOT crash – allow degraded mode
    logger.warning(
        "🚨 Missing mandatory environment variables at startup: %s. "
        "The API will run in degraded mode (health endpoint returns 503).",
        ", ".join(MISSING_ENV_VARS),
    )

# Load environment (.env) for any start mode
try:
    load_dotenv()
except Exception:
    pass

# Simple in-process rate limiter and metrics
_metrics = {
    "requests_total": 0,
    "process_video_markdown_total": 0,
    "success_total": 0,
    "error_total": 0,
    "cached_total": 0,
    "transcript_success_total": 0,
    "fallback_success_total": 0,
}

from collections import deque
from time import time as _now

_recent_requests = deque(maxlen=1000)
_RATE_LIMIT_RPS = 5  # basic cap across process

def _rate_limit_ok():
    current = _now()
    # purge older than 1s
    while _recent_requests and current - _recent_requests[0] > 1.0:
        _recent_requests.popleft()
    return len(_recent_requests) < _RATE_LIMIT_RPS

# Connector health utilities
def _tcp_connect_ok(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def _http_health_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False

def _check_livekit_health() -> Dict[str, Any]:
    url = os.getenv("LIVEKIT_URL", "").strip()
    api_key = os.getenv("LIVEKIT_API_KEY", "").strip()
    api_secret = os.getenv("LIVEKIT_API_SECRET", "").strip()
    configured = bool(url)
    result: Dict[str, Any] = {
        "name": "livekit",
        "configured": configured,
        "reachable": False,
        "auth_configured": bool(api_key and api_secret),
        "details": {}
    }
    if not configured:
        result["status"] = "disabled"
        return result
    try:
        parsed = urllib.parse.urlparse(url)
        # Try common health path if HTTP(S)
        if parsed.scheme in ("http", "https"):
            for p in ("/health", "/livekit/health", "/"):
                if _http_health_ok(urllib.parse.urljoin(url, p)):
                    result["reachable"] = True
                    break
        else:
            host = parsed.hostname or "localhost"
            # Default to 443 for wss, 80 for ws if port not explicitly provided
            if parsed.port:
                port = parsed.port
            else:
                port = 443 if parsed.scheme == "wss" else 80
            result["reachable"] = _tcp_connect_ok(host, port)
        result["status"] = "healthy" if result["reachable"] else "unreachable"
    except Exception as e:
        result["status"] = "error"
        result["details"]["error"] = str(e)
    return result

def _check_mozilla_ai_health() -> Dict[str, Any]:
    url = os.getenv("MOZILLA_AI_URL", "").strip()
    configured = bool(url)
    result: Dict[str, Any] = {
        "name": "mozilla_ai",
        "configured": configured,
        "reachable": False,
        "details": {}
    }
    if not configured:
        result["status"] = "disabled"
        return result
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme in ("http", "https"):
            for path in ("/health", "/healthz", "/status", "/"):
                if _http_health_ok(urllib.parse.urljoin(url, path)):
                    result["reachable"] = True
                    break
        else:
            host = parsed.hostname or "localhost"
            port = parsed.port or 80
            result["reachable"] = _tcp_connect_ok(host, port)
        result["status"] = "healthy" if result["reachable"] else "unreachable"
    except Exception as e:
        result["status"] = "error"
        result["details"]["error"] = str(e)
    return result

# Create FastAPI app
app = FastAPI(
    title="YouTube Extension API - Real Integration",
    description="Backend API for YouTube Extension with real YouTube Data API, AI processing, and cost monitoring",
    version="2.0.0-real-api"
)

# Prometheus metrics instrumentation
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    logger.info("✅ Prometheus /metrics endpoint exposed")
except Exception as e:
    logger.warning(f"Prometheus instrumentation unavailable: {e}")

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Alternative dev server
        "https://youtube-extension-frontend.vercel.app",  # Production frontend
        "https://youtube-extension-frontend-jxk2359s8-garvs-projects-5153e7c7.vercel.app",  # Vercel preview
        "https://*.vercel.app",  # All Vercel domains
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for demo UI
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info("✅ Static files mounted at /static")

# Root route to serve demo UI
@app.get("/")
async def serve_demo_ui():
    """Serve the demo UI for video-to-software"""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(static_file)
    return {"message": "EventRelay Backend API - Use /docs for API documentation"}

# Setup Real API endpoints if available
if HAS_REAL_API_SERVICES and setup_real_api_endpoints:
    try:
        setup_real_api_endpoints(app)
        logger.info("✅ Real API endpoints integrated successfully")
    except Exception as e:
        logger.error(f"❌ Failed to setup real API endpoints: {e}")
        HAS_REAL_API_SERVICES = False

# Include integration routes (Gemini, YouTube, Vercel, Stripe, Supabase)
try:
    from src.integrations.routes import router as integrations_router
    app.include_router(integrations_router)
    logger.info("✅ Integration routes mounted at /api/v1/integrations")
except ImportError as e:
    logger.warning(f"Integration routes not available: {e}")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = "tooltip-assistant"
    session_id: Optional[str] = "default"

class VideoToSoftwareRequest(BaseModel):
    video_url: str
    project_type: str = "web"  # web, api, ml, mobile
    deployment_target: str = "vercel"  # vercel, netlify, aws
    features: Optional[List[str]] = []

class VideoCategoryRequest(BaseModel):
    category: str
    project_type: str = "web"
    deployment_target: str = "vercel"
    features: Optional[List[str]] = []
    query_override: Optional[str] = None
    max_results: int = 5
    order: str = "date"  # relevance, date, viewCount, rating, title
    published_within_days: int = 30


def _build_category_query(category: str) -> str:
    """Create a resilient search query for a category string."""
    normalized = category.replace("_", " ").strip()
    if not normalized:
        normalized = "developer tutorial"
    return f"{normalized} tutorial"


DEFAULT_CATEGORY_LIBRARY: Dict[str, List[Dict[str, str]]] = {
    "react": [
        {"video_id": "w7ejDZ8SWv8", "title": "React JS Crash Course", "channel": "Traversy Media", "published_at": "2020-09-11T00:00:00Z"},
        {"video_id": "bMknfKXIFA8", "title": "React 18 Tutorial for Beginners", "channel": "freeCodeCamp.org", "published_at": "2022-03-29T00:00:00Z"},
    ],
    "python": [
        {"video_id": "rfscVS0vtbw", "title": "Python for Beginners – Full Course", "channel": "freeCodeCamp.org", "published_at": "2019-07-11T00:00:00Z"},
        {"video_id": "kqtD5dpn9C8", "title": "Python for Everybody - Full University Course", "channel": "freeCodeCamp.org", "published_at": "2020-07-11T00:00:00Z"},
    ],
    "automation": [
        {"video_id": "B9nFMZIYQl0", "title": "Automate Excel With Python", "channel": "freeCodeCamp.org", "published_at": "2021-05-14T00:00:00Z"},
        {"video_id": "t_j2X1GpY1w", "title": "Automate the Boring Stuff with Python", "channel": "CS Dojo", "published_at": "2018-02-21T00:00:00Z"},
    ],
    "frontend": [
        {"video_id": "pQN-pnXPaVg", "title": "Frontend Web Development Bootcamp", "channel": "freeCodeCamp.org", "published_at": "2018-08-17T00:00:00Z"},
    ],
    "general": [
        {"video_id": "Z1RJmh_OqeA", "title": "Django Crash Course", "channel": "Traversy Media", "published_at": "2020-10-30T00:00:00Z"},
    ],
}

CATEGORY_SEARCH_TIMEOUT = float(os.getenv("CATEGORY_SEARCH_TIMEOUT", "15"))


def _fallback_video_for_category(category: str) -> Optional[Dict[str, str]]:
    """Return a deterministic fallback video when live search fails."""
    normalized = category.lower()
    for key, entries in DEFAULT_CATEGORY_LIBRARY.items():
        if key == "general":
            continue
        if key in normalized and entries:
            entry = random.choice(entries)
            return {
                **entry,
                "video_url": f"https://www.youtube.com/watch?v={entry['video_id']}",
                "source": "fallback",
            }
    general_entries = DEFAULT_CATEGORY_LIBRARY.get("general", [])
    if general_entries:
        entry = random.choice(general_entries)
        return {
            **entry,
            "video_url": f"https://www.youtube.com/watch?v={entry['video_id']}",
            "source": "fallback",
        }
    return None

class ChatResponse(BaseModel):
    response: str
    status: str
    session_id: str
    timestamp: datetime

class VideoProcessingRequest(BaseModel):
    video_url: str
    options: Optional[Dict[str, Any]] = {}

class VideoProcessingResponse(BaseModel):
    result: Dict[str, Any]
    status: str
    progress: Optional[float] = 0.0
    timestamp: datetime

class MarkdownRequest(BaseModel):
    video_url: str
    force_regenerate: Optional[bool] = False

class MarkdownResponse(BaseModel):
    video_id: str
    video_url: str
    metadata: Dict[str, Any]
    markdown_content: str
    cached: bool
    save_path: str
    processing_time: str
    status: str

USE_LANGEXTRACT_FALLBACK = os.getenv("USE_LANGEXTRACT_FALLBACK", "false").lower() in ("1","true","yes")

async def _try_langextract_fallback(video_url: str) -> Optional[Dict[str, Any]]:
    """When transcript or pipeline fails, attempt content extraction via MCP LangExtract."""
    try:
        import subprocess, json as _json
        payload = _json.dumps({
            "method": "tools/call",
            "params": {
                "name": "extract",
                "arguments": {"source_url": video_url}
            }
        }) + "\n"
        proc = subprocess.run(
            ["python3", "mcp_servers/langextract_mcp_server.py"],
            input=payload.encode(), capture_output=True, timeout=60
        )
        if proc.returncode != 0:
            logger.warning(f"LangExtract MCP call failed: {proc.stderr.decode()[:200]}")
            return None
        out = proc.stdout.decode().strip().splitlines()[-1]
        res = _json.loads(out).get("result", {})
        if "error" in res:
            logger.warning(f"LangExtract error: {res['error']}")
            return None
        text = res.get("text", "")
        if not text:
            return None
        # Minimal markdown packaging
        return {
            "video_id": CacheManager()._extract_video_id(video_url),
            "video_url": video_url,
            "metadata": {"source": "langextract_fallback"},
            "markdown_analysis": f"# Extracted Content\n\n{text[:4000]}",
            "save_path": "",
            "processing_time": datetime.now().isoformat(),
            "success": True
        }
    except Exception as e:
        logger.warning(f"LangExtract fallback exception: {e}")
        return None

# Initialize video processor and cache manager
_processor_singleton = None

def get_video_processor():
    """Get the working video processor with proper error handling"""
    try:
        global _processor_singleton
        if _processor_singleton is not None:
            return _processor_singleton
        
        # Import with proper path handling

        # Use the working factory to get a processor
        try:
            from .video_processor_factory import get_video_processor
            processor = get_video_processor("auto")
            _processor_singleton = processor
            logger.info("✅ Video processor initialized successfully via factory")
            return processor
        except Exception as e:
            logger.warning(f"Factory processor failed: {e}, trying direct import")
            # Fallback to direct import of working processors
            try:
                from .enhanced_video_processor import EnhancedVideoProcessor
                processor = EnhancedVideoProcessor()
                _processor_singleton = processor
                logger.info("✅ EnhancedVideoProcessor initialized successfully (direct)")
                return processor
            except ImportError:
                # Final fallback to original markdown processor
                from agents.markdown_video_processor import MarkdownVideoProcessor
                processor = MarkdownVideoProcessor()
                _processor_singleton = processor
                logger.info("✅ MarkdownVideoProcessor initialized successfully (fallback)")
                return processor
            
    except ImportError as e:
        logger.error(f"Failed to import video processors: {e}")
        return None
    except Exception as e:
        logger.error(f"Error initializing video processor: {e}")
        return None

class CacheManager:
    """Manages caching for processed markdown content"""
    
    def __init__(self, cache_dir: str = "youtube_processed_videos/markdown_analysis"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, video_url: str) -> str:
        """Generate cache key from video URL"""
        return hashlib.md5(video_url.encode()).hexdigest()[:12]
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        if len(url) == 11:
            return url
        
        raise ValueError(f"Could not extract video ID from: {url}")
    
    def get_cached_result(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Get cached markdown result if available (supports legacy and enhanced caches)"""
        try:
            video_id = self._extract_video_id(video_url)

            # 1) Legacy markdown_analysis cache
            for category_dir in self.cache_dir.iterdir():
                if category_dir.is_dir():
                    markdown_file = category_dir / f"{video_id}_analysis.md"
                    metadata_file = category_dir / f"{video_id}_metadata.json"

                    if markdown_file.exists() and metadata_file.exists():
                        age = time.time() - markdown_file.stat().st_mtime
                        if age < 86400:
                            with open(markdown_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            return {
                                'video_id': video_id,
                                'markdown_content': content,
                                'metadata': metadata,
                                'save_path': str(markdown_file),
                                'cached': True
                            }

            # 2) Enhanced enhanced_analysis cache
            enhanced_base = Path('youtube_processed_videos') / 'enhanced_analysis'
            if enhanced_base.exists():
                for category_dir in enhanced_base.iterdir():
                    if not category_dir.is_dir():
                        continue
                    # Find latest enhanced md for this video_id
                    candidates = sorted(category_dir.glob(f"{video_id}_*_enhanced.md"))
                    if candidates:
                        md_path = candidates[-1]
                        # Matching metadata file
                        meta_candidates = sorted(category_dir.glob(f"{video_id}_*_metadata.json"))
                        metadata = {}
                        if meta_candidates:
                            with open(meta_candidates[-1], 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                        with open(md_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        return {
                            'video_id': video_id,
                            'markdown_content': content,
                            'metadata': metadata,
                            'save_path': str(md_path),
                            'cached': True
                        }

            return None
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None
    
    def clear_cache(self, video_url: str = None):
        """Clear cache for specific video or all videos"""
        if video_url:
            try:
                video_id = self._extract_video_id(video_url)
                for category_dir in self.cache_dir.iterdir():
                    if category_dir.is_dir():
                        markdown_file = category_dir / f"{video_id}_analysis.md"
                        metadata_file = category_dir / f"{video_id}_metadata.json"
                        if markdown_file.exists():
                            markdown_file.unlink()
                        if metadata_file.exists():
                            metadata_file.unlink()
                logger.info(f"Cleared cache for video: {video_id}")
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
        else:
            # Clear all cache
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Cleared all cache")

cache_manager = CacheManager()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with real API integration status. Returns 503 if critical env vars are missing."""
    if MISSING_ENV_VARS:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "missing": MISSING_ENV_VARS},
        )

    processor = get_video_processor()
    processor_status = "available" if processor else "unavailable"
    
    # Check real API services
    real_api_status = {
        "enabled": HAS_REAL_API_SERVICES,
        "youtube_api_key": bool(os.getenv("YOUTUBE_API_KEY")),
        "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic_api_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "gemini_api_key": bool(os.getenv("GEMINI_API_KEY"))
    }
    
    connectors = {
        "livekit": {
            "configured": bool(os.getenv("LIVEKIT_URL", "").strip()),
        },
        "mozilla_ai": {
            "configured": bool(os.getenv("MOZILLA_AI_URL", "").strip()),
        }
    }
    
    overall_status = "healthy" if (processor_status == "available" and 
                                   (HAS_REAL_API_SERVICES or processor_status == "available")) else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0-real-api",
        "connections": len(manager.active_connections),
        "video_processor": processor_status,
        "real_api_integration": real_api_status,
        "connectors": connectors,
        "features": {
            "real_youtube_api": real_api_status["youtube_api_key"],
            "multi_provider_ai": any([real_api_status["openai_api_key"], 
                                    real_api_status["anthropic_api_key"], 
                                    real_api_status["gemini_api_key"]]),
            "cost_monitoring": HAS_REAL_API_SERVICES,
            "mock_fallback": not HAS_REAL_API_SERVICES
        }
    }

@app.get("/connectors/health")
async def connectors_health():
    """Verify external connectors (LiveKit, Mozilla AI) are reachable and properly configured."""
    try:
        lk = _check_livekit_health()
        moz = _check_mozilla_ai_health()
        overall = all(c.get("status") == "healthy" for c in (lk, moz) if c.get("configured"))
        return {
            "timestamp": datetime.now().isoformat(),
            "overall": "healthy" if overall else "degraded",
            "connectors": {
                "livekit": lk,
                "mozilla_ai": moz
            }
        }
    except Exception as e:
        logger.error(f"Connector health error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# The explicit /metrics implementation provided above has been replaced by
# Prometheus FastAPI Instrumentator. Any custom metrics should leverage the
# instrumentator callbacks moving forward.

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Handle chat requests from frontend with real AI processing"""
    try:
        logger.info(f"Chat request received: {request.message[:50]}...")
        
        # Get the video processor
        processor = get_video_processor()
        
        if processor:
            # Use real AI processing for chat responses
            try:
                # For now, use a simple AI response since process_chat_message doesn't exist
                # TODO: Implement process_chat_message in EnhancedVideoProcessor
                response_text = f"AI Assistant: I received your message: '{request.message}'. I'm here to help with video processing and analysis! Please provide a YouTube URL for video processing."
                
            except Exception as e:
                logger.error(f"Error in AI processing: {e}")
                response_text = f"AI Assistant: I received your message: '{request.message}'. (Processing error: {str(e)})"
        else:
            # Fallback response when processor is unavailable
            response_text = f"AI Assistant: I received your message: '{request.message}'. (Video processor unavailable - please check configuration)"
        
        response = ChatResponse(
            response=response_text,
            status="success",
            session_id=request.session_id,
            timestamp=datetime.now()
        )
        
        logger.info(f"Chat response sent successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-video-markdown", response_model=MarkdownResponse)
async def process_video_markdown(request: MarkdownRequest):
    """Process video and return markdown-formatted learning guide with caching"""
    # Rate limit check
    if not _rate_limit_ok():
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    _recent_requests.append(_now())
    _metrics["requests_total"] += 1
    _metrics["process_video_markdown_total"] += 1
    try:
        logger.info(f"Markdown processing request received: {request.video_url}")
        
        if not request.video_url:
            raise HTTPException(status_code=400, detail="Video URL required")
        
        # Check cache first unless force regenerate is requested
        if not request.force_regenerate:
            cached_result = cache_manager.get_cached_result(request.video_url)
            if cached_result:
                logger.info(f"Returning cached result for {cached_result['video_id']}")
                _metrics["cached_total"] += 1
                
                # Extract markdown content (skip frontmatter)
                content = cached_result['markdown_content']
                if content.startswith('---'):
                    end_idx = content.find('---', 3)
                    if end_idx != -1:
                        content = content[end_idx + 3:].strip()
                
                return MarkdownResponse(
                    video_id=cached_result['video_id'],
                    video_url=request.video_url,
                    metadata=cached_result['metadata'],
                    markdown_content=content,
                    cached=True,
                    save_path=cached_result['save_path'],
                    processing_time=datetime.now().isoformat(),
                    status="success"
                )
        
        # Get the video processor
        processor = get_video_processor()
        if not processor:
            raise HTTPException(status_code=503, detail="Video processor not available")
        
        try:
            # Process the video with enhanced markdown processor
            start_time = datetime.now()
            result = await processor.process_video(request.video_url)
            processing_duration = (datetime.now() - start_time).total_seconds()
            
            if not result or not result.get('success'):
                # Force fallback if primary pipeline didn't produce success
                if USE_LANGEXTRACT_FALLBACK:
                    fallback = await _try_langextract_fallback(request.video_url)
                    if fallback:
                        _metrics["success_total"] += 1
                        _metrics["fallback_success_total"] += 1
                        return MarkdownResponse(
                            video_id=fallback['video_id'],
                            video_url=request.video_url,
                            metadata=fallback['metadata'],
                            markdown_content=fallback['markdown_analysis'],
                            cached=False,
                            save_path=fallback['save_path'],
                            processing_time=fallback['processing_time'],
                            status="success"
                        )
                logger.warning("Primary pipeline returned no result/success. Fallback %s and returned %s",
                               "ENABLED" if USE_LANGEXTRACT_FALLBACK else "DISABLED",
                               "SUCCESS" if USE_LANGEXTRACT_FALLBACK else "N/A")
                raise HTTPException(status_code=500, detail="Video processing failed")
            
            # Extract markdown content (skip frontmatter)
            markdown_content = result.get('markdown_analysis', '')
            if markdown_content.startswith('---'):
                end_idx = markdown_content.find('---', 3)
                if end_idx != -1:
                    markdown_content = markdown_content[end_idx + 3:].strip()
            
            response = MarkdownResponse(
                video_id=result['video_id'],
                video_url=request.video_url,
                metadata=result['metadata'],
                markdown_content=markdown_content,
                cached=False,
                save_path=result['save_path'],
                processing_time=f"{processing_duration:.2f}s",
                status="success"
            )
            # Metrics for success path
            _metrics["success_total"] += 1
            # Heuristic: treat transcript_success if segments present in metadata
            try:
                meta = result.get('metadata', {})
                if meta.get('has_transcript') or (meta.get('transcript_segments', 0) or 0) > 0:
                    _metrics["transcript_success_total"] += 1
            except Exception:
                pass
            
            logger.info(f"Markdown processing completed in {processing_duration:.2f}s")
            return response
            
        except Exception as e:
            logger.exception(f"Error in markdown video processing (exception): {e}")
            # Fallback path using LangExtract
            if USE_LANGEXTRACT_FALLBACK:
                fallback = await _try_langextract_fallback(request.video_url)
                if fallback:
                    _metrics["success_total"] += 1
                    _metrics["fallback_success_total"] += 1
                    return MarkdownResponse(
                        video_id=fallback['video_id'],
                        video_url=request.video_url,
                        metadata=fallback['metadata'],
                        markdown_content=fallback['markdown_analysis'],
                        cached=False,
                        save_path=fallback['save_path'],
                        processing_time=fallback['processing_time'],
                        status="success"
                    )
            logger.warning("LangExtract fallback %s or returned empty; propagating 500",
                           "FAILED" if USE_LANGEXTRACT_FALLBACK else "DISABLED")
            raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
            
    except HTTPException:
        _metrics["error_total"] += 1
        raise
    except Exception as e:
        logger.error(f"Error in markdown processing endpoint: {e}")
        _metrics["error_total"] += 1
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/markdown/{video_id}")
async def get_markdown_analysis(video_id: str, format: str = "markdown"):
    """Get cached markdown analysis by video ID"""
    try:
        # Search for the video in cache directories
        cache_dir = Path("youtube_processed_videos/markdown_analysis")
        
        for category_dir in cache_dir.iterdir():
            if category_dir.is_dir():
                analysis_path = category_dir / f"{video_id}_analysis.md"
                metadata_path = category_dir / f"{video_id}_metadata.json"
                
                if analysis_path.exists():
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    metadata = {}
                    if metadata_path.exists():
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    # Skip the frontmatter if present
                    markdown_content = content
                    if content.startswith('---'):
                        end_idx = content.find('---', 3)
                        if end_idx != -1:
                            markdown_content = content[end_idx + 3:].strip()
                    
                    # Get file stats
                    file_stats = analysis_path.stat()
                    age_hours = (time.time() - file_stats.st_mtime) / 3600
                    
                    return {
                        "video_id": video_id,
                        "format": format,
                        "markdown_content": markdown_content,
                        "metadata": metadata,
                        "cached": True,
                        "cache_age_hours": round(age_hours, 2),
                        "file_size": file_stats.st_size,
                        "last_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                    }
        
        raise HTTPException(status_code=404, detail=f"Markdown analysis not found for video ID: {video_id}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving markdown analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-video", response_model=VideoProcessingResponse)
async def process_video_endpoint(request: VideoProcessingRequest):
    """Handle video processing requests with real processing"""
    try:
        logger.info(f"Video processing request received: {request.video_url}")
        
        if not request.video_url:
            raise HTTPException(status_code=400, detail="Video URL required")
        
        # Get the video processor
        processor = get_video_processor()
        
        if processor:
            try:
                # Process the video with markdown processor
                result = await processor.process_video(request.video_url)
                
                # Validate the result structure
                if not isinstance(result, dict):
                    result = {"processed_data": result, "status": "processed"}
                
                response = VideoProcessingResponse(
                    result=result,
                    status="success",
                    progress=100.0,
                    timestamp=datetime.now()
                )
                
                logger.info(f"Video processing completed successfully")
                return response
                
            except Exception as e:
                logger.error(f"Error in video processing: {e}")
                error_result = {
                    "video_url": request.video_url,
                    "status": "error",
                    "error": str(e),
                    "message": "Video processing failed"
                }
                
                response = VideoProcessingResponse(
                    result=error_result,
                    status="error",
                    progress=0.0,
                    timestamp=datetime.now()
                )
                return response
        else:
            # Return error when processor is unavailable
            error_result = {
                "video_url": request.video_url,
                "status": "unavailable",
                "message": "Video processor not available - check configuration"
            }
            
            response = VideoProcessingResponse(
                result=error_result,
                status="error",
                progress=0.0,
                timestamp=datetime.now()
            )
            return response
            
    except Exception as e:
        logger.error(f"Error in video processing endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        logger.info("WebSocket connection established")
        
        # Send welcome message
        welcome_message = {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to YouTube Extension API"
        }
        await manager.send_personal_message(json.dumps(welcome_message), websocket)
        
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                logger.info(f"WebSocket message received: {message.get('type', 'unknown')}")
                
                # Handle different message types
                if message.get("type") == "chat":
                    response = await handle_chat_message(message)
                    await manager.send_personal_message(json.dumps(response), websocket)
                    
                elif message.get("type") == "video_processing":
                    response = await handle_video_processing_message(message)
                    await manager.send_personal_message(json.dumps(response), websocket)
                    
                elif message.get("type") == "ping":
                    pong_response = {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_personal_message(json.dumps(pong_response), websocket)
                    
                else:
                    # Unknown message type
                    error_response = {
                        "type": "error",
                        "message": f"Unknown message type: {message.get('type', 'unknown')}",
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_personal_message(json.dumps(error_response), websocket)
                    
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                manager.disconnect(websocket)
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                error_response = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(json.dumps(error_response), websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                error_response = {
                    "type": "error",
                    "message": f"Internal server error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(json.dumps(error_response), websocket)
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        manager.disconnect(websocket)

async def handle_chat_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle chat messages via WebSocket with real processing"""
    try:
        chat_text = message.get("message", "")
        session_id = message.get("session_id", "default")
        
        # Get the video processor
        processor = get_video_processor()
        
        if processor:
            try:
                # For now, use a simple AI response since process_chat_message doesn't exist
                # TODO: Implement process_chat_message in EnhancedVideoProcessor
                response_text = f"AI Assistant: I received your message: '{chat_text}'. I'm here to help with video processing and analysis! Please provide a YouTube URL for video processing."
            except Exception as e:
                logger.error(f"Error in AI processing: {e}")
                response_text = f"AI Assistant: I received your message: '{chat_text}'. (Processing error: {str(e)})"
        else:
            response_text = f"AI Assistant: I received your message: '{chat_text}'. (Video processor unavailable)"
        
        return {
            "type": "chat_response",
            "response": response_text,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        return {
            "type": "error",
            "message": f"Error processing chat message: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

async def handle_video_processing_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Handle video processing messages via WebSocket with real processing"""
    try:
        video_url = message.get("video_url", "")
        
        if not video_url:
            return {
                "type": "error",
                "message": "Video URL required",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get the video processor
        processor = get_video_processor()
        
        if processor:
            try:
                # Process the video with real functionality  
                result = await processor.process_video(video_url)
                
                # Validate the result structure
                if not isinstance(result, dict):
                    result = {"processed_data": result, "status": "processed"}
                
                return {
                    "type": "video_processing_response",
                    "result": result,
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error in video processing: {e}")
                return {
                    "type": "video_processing_response",
                    "result": {
                        "video_url": video_url,
                        "status": "error",
                        "error": str(e)
                    },
                    "status": "error",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "type": "video_processing_response",
                "result": {
                    "video_url": video_url,
                    "status": "unavailable",
                    "message": "Video processor not available"
                },
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error handling video processing message: {e}")
        return {
            "type": "error",
            "message": f"Error processing video: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# Cache management endpoints
@app.delete("/api/cache/{video_id}")
async def clear_video_cache(video_id: str):
    """Clear cache for a specific video"""
    try:
        # Reconstruct video URL for cache clearing
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        cache_manager.clear_cache(video_url)
        
        return {
            "status": "success",
            "message": f"Cache cleared for video: {video_id}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/cache")
async def clear_all_cache():
    """Clear all cached results"""
    try:
        cache_manager.clear_cache()
        
        return {
            "status": "success",
            "message": "All cache cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing all cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        cache_dir = Path("youtube_processed_videos/markdown_analysis")
        
        stats = {
            "total_cached_videos": 0,
            "categories": {},
            "total_size_mb": 0,
            "oldest_cache": None,
            "newest_cache": None
        }
        
        if cache_dir.exists():
            oldest_time = float('inf')
            newest_time = 0
            
            for category_dir in cache_dir.iterdir():
                if category_dir.is_dir():
                    category_name = category_dir.name
                    markdown_files = list(category_dir.glob("*_analysis.md"))
                    category_count = len(markdown_files)
                    category_size = sum(f.stat().st_size for f in markdown_files)
                    
                    stats["categories"][category_name] = {
                        "count": category_count,
                        "size_mb": round(category_size / 1024 / 1024, 2)
                    }
                    
                    stats["total_cached_videos"] += category_count
                    stats["total_size_mb"] += category_size
                    
                    # Track oldest and newest
                    for f in markdown_files:
                        mtime = f.stat().st_mtime
                        if mtime < oldest_time:
                            oldest_time = mtime
                        if mtime > newest_time:
                            newest_time = mtime
            
            stats["total_size_mb"] = round(stats["total_size_mb"] / 1024 / 1024, 2)
            
            if oldest_time != float('inf'):
                stats["oldest_cache"] = datetime.fromtimestamp(oldest_time).isoformat()
            if newest_time > 0:
                stats["newest_cache"] = datetime.fromtimestamp(newest_time).isoformat()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Real Video-to-Software imports
try:
    from .code_generator import get_code_generator
    from .ai_code_generator import get_ai_code_generator
    from .deployment_manager import get_deployment_manager
    REAL_PIPELINE_AVAILABLE = True
    AI_GENERATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Real pipeline components not available: {e}")
    REAL_PIPELINE_AVAILABLE = False
    AI_GENERATION_AVAILABLE = False

# REAL VIDEO-TO-SOFTWARE ENDPOINT
@app.post("/api/video-to-software")
async def video_to_software_endpoint(request: VideoToSoftwareRequest):
    """
    REAL-TIME: Convert YouTube video to deployed software
    Complete implementation using UVAI's real video processing pipeline
    """
    start_time = time.time()
    
    try:
        logger.info(f"🚀 Real Video-to-Software request: {request.video_url}")
        
        target_info = resolve_deployment_target(request.deployment_target)
        resolved_target = target_info["resolved"]
        features_list = list(request.features or ["responsive_design", "modern_ui"])

        if not REAL_PIPELINE_AVAILABLE:
            raise HTTPException(
                status_code=503, 
                detail="Real video-to-software pipeline not available. Please check system configuration."
            )
        
        # Phase 1: Real Video Processing
        logger.info("1️⃣ Processing video with real UVAI components...")
        processor = get_video_processor()
        video_analysis = await processor.process_video(request.video_url)
        
        # Handle different processor output formats
        if video_analysis.get("success") == True:
            # Enhanced processor format
            extracted_info = {
                "title": video_analysis.get("metadata", {}).get("title", "UVAI Generated Project"),
                "technologies": video_analysis.get("ai_analysis", {}).get("Related Topics", []),
                "features": features_list,
                "project_type": request.project_type,
                "complexity": "intermediate"
            }
            video_status = "success"
        elif video_analysis.get("status") == "success":
            # Real processor format
            extracted_info = video_analysis.get("extracted_info", {})
            video_status = "success"
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Video processing failed: {video_analysis.get('error', 'Unknown error')}"
            )
        
        # Phase 2: AI-Powered Full-Stack Code Generation
        logger.info("2️⃣ Generating full-stack project with AI...")

        project_config = {
            "type": request.project_type,
            "features": features_list,
            "title": extracted_info.get("title", "UVAI Generated Project"),
            "video_url": request.video_url
        }

        # Use AI code generator for full-stack apps, fallback to template for simple projects
        if AI_GENERATION_AVAILABLE and request.project_type in ["web", "api", "fullstack", "saas", "agent"]:
            try:
                ai_generator = get_ai_code_generator()
                generation_result = await ai_generator.generate_fullstack_project(
                    {"extracted_info": extracted_info, "ai_analysis": video_analysis.get("ai_analysis", {}), "video_data": {"video_url": request.video_url}},
                    project_config
                )
                logger.info("✅ AI full-stack generation completed")
            except Exception as e:
                logger.warning(f"AI generation failed, falling back to templates: {e}")
                code_generator = get_code_generator()
                generation_result = await code_generator.generate_project(video_analysis, project_config)
        else:
            code_generator = get_code_generator()
            generation_result = await code_generator.generate_project(video_analysis, project_config)
        
        # Phase 3: Real Deployment
        logger.info("3️⃣ Deploying to platforms...")
        deployment_manager = get_deployment_manager()
        
        deployment_config = {
            "target": resolved_target,
            "auto_deploy": True
        }
        
        deployment_result = await deployment_manager.deploy_project(
            generation_result["project_path"],
            project_config,
            deployment_config
        )
        
        # Phase 4: Compile Results
        processing_time = time.time() - start_time
        logger.info("4️⃣ Compiling final results...")
        
        # Get primary deployment URL
        deployment_urls = deployment_result.get("urls", {})
        primary_url = (
            deployment_urls.get(resolved_target) or 
            deployment_urls.get("vercel") or 
            deployment_urls.get("netlify") or 
            deployment_urls.get("github_pages") or
            "https://deployment-pending.uvai.platform"
        )
        
        # Get GitHub repository URL
        github_deployment = deployment_result.get("deployments", {}).get("github", {})
        github_url = github_deployment.get("url", "https://github.com/uvai-generated/project-pending")
        
        # Compile comprehensive result
        result = {
            "video_url": request.video_url,
            "project_name": generation_result.get("project_type", "uvai-project"),
            "project_type": request.project_type,
            "deployment_target": target_info["requested"],
            "live_url": primary_url,
            "github_repo": github_url,
            "build_status": "completed" if deployment_result.get("status") == "success" else "partial",
            "processing_time": f"{processing_time:.1f}s",
            "features_implemented": features_list + ["uvai_generated", "real_pipeline"],
            
            # Real processing results
            "video_analysis": {
                "status": video_status,
                "extracted_info": extracted_info,
                "processing_pipeline": video_analysis.get("processing_pipeline", [])
            },
            
            "code_generation": {
                "framework": generation_result.get("framework"),
                "files_created": generation_result.get("files_created", []),
                "entry_point": generation_result.get("entry_point"),
                "build_command": generation_result.get("build_command"),
                "start_command": generation_result.get("start_command")
            },
            
            "deployment": {
                "status": deployment_result.get("status"),
                "deployment_id": deployment_result.get("deployment_id"),
                "platforms": list(deployment_result.get("deployments", {}).keys()),
                "urls": deployment_urls,
                "errors": deployment_result.get("errors", [])
            },
            
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "real_implementation": True
        }
        
        logger.info(f"✅ Real Video-to-Software completed in {processing_time:.1f}s")
        logger.info(f"📊 Generated {len(generation_result.get('files_created', []))} files")
        logger.info(f"🌐 Deployed to {len(deployment_urls)} platforms")
        logger.info(f"🔗 Primary URL: {primary_url}")

        result["deployment"]["requested_target"] = target_info["requested"]
        result["deployment"]["resolved_target"] = resolved_target
        result["deployment"]["alias_applied"] = target_info.get("alias_applied", False)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Video-to-Software pipeline failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@app.post("/api/video-to-software/by-category")
async def video_to_software_by_category(request: VideoCategoryRequest):
    """
    Discover a fresh tutorial video for a given category and run the full
    video-to-software pipeline automatically.
    """
    if get_youtube_service is None:
        raise HTTPException(
            status_code=503,
            detail="YouTube discovery service is not configured on this instance."
        )

    query = request.query_override or _build_category_query(request.category)
    published_after = None
    if request.published_within_days and request.published_within_days > 0:
        published_after = (
            datetime.utcnow() - timedelta(days=request.published_within_days)
        ).isoformat() + "Z"

    max_results = max(1, min(request.max_results or 1, 25))

    search_results: List[Any] = []
    search_error: Optional[str] = None
    try:
        service = get_youtube_service()
        search_results = await asyncio.wait_for(
            service.search_videos(
                query=query,
                max_results=max_results,
                order=request.order or "date",
                published_after=published_after,
            ),
            timeout=CATEGORY_SEARCH_TIMEOUT,
        )
    except Exception as exc:
        search_error = str(exc)
        logger.warning(
            "Category discovery fallback for '%s' (query='%s'): %s",
            request.category,
            query,
            exc,
        )

    source_kind = "search"
    if not search_results:
        fallback_entry = _fallback_video_for_category(request.category)
        if not fallback_entry:
            detail_msg = (
                f"No videos found for category '{request.category}'."
                + (" Search error: " + search_error if search_error else "")
            )
            raise HTTPException(status_code=404, detail=detail_msg)
        source_kind = fallback_entry.get("source", "fallback")
        chosen_meta = fallback_entry
        discovered_url = fallback_entry["video_url"]
    else:
        selection_pool = search_results[: max(1, min(5, len(search_results)))]
        chosen = random.choice(selection_pool)
        chosen_meta = {
            "video_id": chosen.video_id,
            "title": getattr(chosen, "title", ""),
            "channel": getattr(chosen, "channel_title", ""),
            "published_at": getattr(chosen, "published_at", ""),
        }
        discovered_url = f"https://www.youtube.com/watch?v={chosen.video_id}"

    try:
        downstream_request = VideoToSoftwareRequest(
            video_url=discovered_url,
            project_type=request.project_type,
            deployment_target=request.deployment_target,
            features=request.features or [],
        )
        response = await video_to_software_endpoint(downstream_request)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        logger.error("Category pipeline failed for '%s': %s", request.category, exc)
        raise HTTPException(status_code=500, detail="Category pipeline failed") from exc
    response["source_video"] = {
        "category": request.category,
        "query": query,
        "video_url": discovered_url,
        "title": chosen_meta.get("title"),
        "channel": chosen_meta.get("channel"),
        "published_at": chosen_meta.get("published_at"),
        "source": source_kind,
    }
    response["search_parameters"] = {
        "order": request.order,
        "max_results": max_results,
        "published_after": published_after,
        "fallback_reason": search_error if source_kind == "fallback" else None,
    }
    return response


# Health check endpoint for the real pipeline
@app.get("/api/video-to-software/health")
async def video_to_software_health():
    """Check health of the real video-to-software pipeline"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "real_pipeline": REAL_PIPELINE_AVAILABLE,
                "video_processor": False,
                "code_generator": False,
                "deployment_manager": False
            }
        }
        
        if REAL_PIPELINE_AVAILABLE:
            try:
                processor = get_video_processor()
                health_status["components"]["video_processor"] = processor is not None
            except:
                pass
            
            try:
                code_gen = get_code_generator()
                health_status["components"]["code_generator"] = code_gen is not None
            except:
                pass
            
            try:
                deploy_mgr = get_deployment_manager()
                health_status["components"]["deployment_manager"] = deploy_mgr is not None
            except:
                pass
        
        overall_health = all(health_status["components"].values())
        health_status["overall"] = "healthy" if overall_health else "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/results/learning_log")
async def get_learning_log():
	"""Return a simple learning log compiled from enhanced analysis files."""
	try:
		base_dir = Path("youtube_processed_videos/enhanced_analysis")
		items = []
		if base_dir.exists():
			for category_dir in base_dir.iterdir():
				if not category_dir.is_dir():
					continue
				for md_file in category_dir.glob("*_enhanced.md"):
					video_id = md_file.name.split("_")[0]
					metadata_file = next(category_dir.glob(f"{video_id}_*_metadata.json"), None)
					metadata = {}
					if metadata_file and metadata_file.exists():
						with open(metadata_file, "r", encoding="utf-8") as f:
							metadata = json.load(f)
					stat = md_file.stat()
					items.append({
						"video_id": video_id,
						"category": category_dir.name,
						"actions_generated": None,
						"transcript_segments": None,
						"processing_time": None,
						"quality_assessment": None,
						"timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
						"feedback": None,
						"title": metadata.get("title") or metadata.get("snippet", {}).get("title")
					})
		return items
	except Exception as e:
		logger.error(f"Error building learning log: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/videos")
async def get_videos_summary():
	"""Return a summary list of processed videos."""
	try:
		base_dir = Path("youtube_processed_videos/enhanced_analysis")
		results = []
		if base_dir.exists():
			for category_dir in base_dir.iterdir():
				if not category_dir.is_dir():
					continue
				for md_file in category_dir.glob("*_enhanced.md"):
					video_id = md_file.name.split("_")[0]
					metadata_file = next(category_dir.glob(f"{video_id}_*_metadata.json"), None)
					metadata = {}
					if metadata_file and metadata_file.exists():
						with open(metadata_file, "r", encoding="utf-8") as f:
							metadata = json.load(f)
					stat = md_file.stat()
					results.append({
						"video_id": video_id,
						"category": category_dir.name,
						"title": metadata.get("title") or metadata.get("snippet", {}).get("title"),
						"published_at": metadata.get("published_at") or metadata.get("snippet", {}).get("publishedAt"),
						"view_count": metadata.get("view_count") or metadata.get("statistics", {}).get("viewCount"),
						"last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
						"markdown_path": str(md_file),
						"metadata_path": str(metadata_file) if metadata_file else None
					})
		return results
	except Exception as e:
		logger.error(f"Error listing videos: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/videos/{video_id}")
async def get_video_detail(video_id: str):
	"""Return detailed info for a specific video from enhanced analysis."""
	try:
		base_dir = Path("youtube_processed_videos/enhanced_analysis")
		for category_dir in base_dir.iterdir():
			if not category_dir.is_dir():
				continue
			md_file = next(category_dir.glob(f"{video_id}_*_enhanced.md"), None)
			if md_file and md_file.exists():
				metadata_file = next(category_dir.glob(f"{video_id}_*_metadata.json"), None)
				metadata = {}
				if metadata_file and metadata_file.exists():
					with open(metadata_file, "r", encoding="utf-8") as f:
						metadata = json.load(f)
				with open(md_file, "r", encoding="utf-8") as f:
					markdown = f.read()
				return {
					"video_id": video_id,
					"category": category_dir.name,
					"title": metadata.get("title") or metadata.get("snippet", {}).get("title"),
					"metadata": metadata,
					"markdown": markdown,
					"markdown_path": str(md_file),
					"metadata_path": str(metadata_file) if metadata_file else None
				}
		raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")
	except HTTPException:
		raise
	except Exception as e:
		logger.error(f"Error reading video detail: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def post_feedback(payload: Dict[str, Any]):
	"""Accept feedback and append to a jsonl file."""
	try:
		feedback_dir = Path("youtube_processed_videos/feedback")
		feedback_dir.mkdir(parents=True, exist_ok=True)
		log_file = feedback_dir / "feedback.jsonl"
		entry = {
			"timestamp": datetime.now().isoformat(),
			**payload
		}
		with open(log_file, "a", encoding="utf-8") as f:
			f.write(json.dumps(entry) + "\n")
		return {"status": "ok"}
	except Exception as e:
		logger.error(f"Error saving feedback: {e}")
		raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(MissingDependencyError)
async def missing_dependency_handler(request, exc: MissingDependencyError):
    """Return 503 JSON when a MissingDependencyError is raised."""
    return JSONResponse(status_code=503, content={"error": "missing_dependency", "detail": str(exc)})

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with enhanced error details"""
    logger.error(f"Unhandled exception: {exc}")
    
    # Enhanced error response for development
    error_detail = {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.now().isoformat(),
        "path": str(request.url) if hasattr(request, 'url') else "unknown"
    }
    
    # Add type information for debugging
    if hasattr(exc, '__class__'):
        error_detail["error_type"] = exc.__class__.__name__
    
    return JSONResponse(
        status_code=500,
        content=error_detail
    )

@app.on_event("shutdown")
async def _shutdown_cleanup():
    try:
        processor = get_video_processor()
        close_coro = getattr(processor, "close", None)
        if callable(close_coro):
            await close_coro()
            logger.info("✅ Processor session closed on shutdown")
    except Exception as e:
        logger.warning(f"Processor shutdown cleanup warning: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
