#!/usr/bin/env python3
"""
Shim for Enhanced Video Processor
Redirects to canonical implementation in `backend/enhanced_video_processor.py`
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import requests
from urllib.parse import urlparse, parse_qs

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.warning("python-dotenv not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [ENHANCED] %(message)s',
    handlers=[
        logging.FileHandler('enhanced_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("enhanced_video_processor")

try:
    from backend.enhanced_video_processor import EnhancedVideoProcessor, get_enhanced_video_processor
except ImportError as e:
    logger.error("Could not import backend.enhanced_video_processor: %s", e)
    def _not_implemented(*args, **kwargs):
        raise ImportError("EnhancedVideoProcessor and get_enhanced_video_processor are unavailable because backend.enhanced_video_processor could not be imported.")
    EnhancedVideoProcessor = _not_implemented
    get_enhanced_video_processor = _not_implemented

__all__ = ["EnhancedVideoProcessor", "get_enhanced_video_processor"] 