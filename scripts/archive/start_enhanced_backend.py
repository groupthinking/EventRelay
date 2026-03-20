#!/usr/bin/env python3
"""
Enhanced Backend Startup Script
===============================

Starts the enhanced FastAPI backend with proper configuration and health checks.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backend/enhanced_processing.log')
    ]
)

logger = logging.getLogger(__name__)

def check_environment() -> bool:
    """Check if environment is properly configured"""
    # Load .env so required keys are visible to env checks
    try:
        load_dotenv()
    except Exception:
        pass
    logger.info("🔍 Checking environment configuration...")

    required_env_vars = [
        'YOUTUBE_API_KEY',
        'OPENAI_API_KEY'
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.warning(f"⚠️  Missing environment variables: {missing_vars}")
        logger.info("💡 Create a .env file with the required API keys")
        return False

    logger.info("✅ Environment configuration looks good")
    return True

def check_dependencies() -> bool:
    """Check if required dependencies are installed"""
    logger.info("📦 Checking dependencies...")

    try:
        import aiohttp
        import fastapi
        import openai
        import uvicorn
        logger.info("✅ Core dependencies available")

        # Check if video processor can be imported
        # REMOVED: sys.path.insert with Path manipulation
        from agents.markdown_video_processor import MarkdownVideoProcessor
        processor = MarkdownVideoProcessor()
        logger.info("✅ MarkdownVideoProcessor available")

        return True

    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        logger.info("💡 Run: pip install -e .[youtube,ml,postgres]")
        return False

def setup_directories() -> None:
    """Ensure required directories exist"""
    logger.info("📁 Setting up directories...")

    directories = [
        'backend/youtube_processed_videos/markdown_analysis',
        'backend/logs',
        'prompts'
    ]

    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    logger.info("✅ Directories configured")

async def health_check() -> bool:
    """Perform startup health check"""
    logger.info("🏥 Performing health check...")

    try:
        # Test video processor initialization
        # REMOVED: sys.path.insert with Path manipulation
        from agents.markdown_video_processor import MarkdownVideoProcessor

        processor = MarkdownVideoProcessor()
        logger.info("✅ Video processor initialized successfully")

        # Test cache manager
        from youtube_extension.main import CacheManager
        cache_manager = CacheManager()
        logger.info("✅ Cache manager initialized successfully")

        return True

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

def main() -> bool:
    """Main startup function"""
    print(f"""
🚀 Enhanced YouTube Extension Backend
====================================

Starting enhanced FastAPI backend with:
✨ Professional markdown learning guides
⚡ Intelligent caching system
🎯 Apple Developer/LinkedIn Learning quality
🔄 MCP integration with enhanced video processing

Time: {datetime.now().isoformat()}
""")

    # Pre-flight checks
    logger.info("🛫 Starting pre-flight checks...")

    if not check_environment():
        logger.error("❌ Environment check failed")
        return False

    if not check_dependencies():
        logger.error("❌ Dependencies check failed")
        return False

    setup_directories()

    # Health check
    if __name__ == "__main__":
        try:
            health_ok = asyncio.run(health_check())
            if not health_ok:
                logger.error("❌ Health check failed")
                return False
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
        return False

    logger.info("✅ All pre-flight checks passed!")

    # Start the server
    try:
        logger.info("🚀 Starting FastAPI server...")

        # Add backend to Python path
        backend_path = Path(__file__).parent / 'backend'

        # Import and configure the app
        from main import app

        # Server configuration
        config = {
            'host': '0.0.0.0',
            'port': 8000,
            'reload': False,
            'log_level': 'info',
            'access_log': True
        }

        print(f"""
🌟 Server Configuration:
   URL: http://localhost:8000
   Host: {config['host']}
   Port: {config['port']}
   Reload: {config['reload']}

📚 API Documentation:
   Swagger UI: http://localhost:8000/docs
   ReDoc: http://localhost:8000/redoc

🔗 Key Endpoints:
   Health: GET /health
   Markdown Processing: POST /api/process-video-markdown
   Cached Analysis: GET /api/markdown/{{video_id}}
   Cache Stats: GET /api/cache/stats

🧪 Test the backend:
   python test_enhanced_backend.py
""")

        uvicorn.run(app, **config)

    except KeyboardInterrupt:
        logger.info("👋 Server shutdown requested")
        return True

    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("✅ Backend startup completed successfully")
    else:
        logger.error("❌ Backend startup failed")
        sys.exit(1)
