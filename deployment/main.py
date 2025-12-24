#!/usr/bin/env python3
"""
Root-level main.py to handle Fly.io's default uvicorn command
This file simply imports the FastAPI app from the backend module
"""

from src.youtube_extension.main import app

# This allows Fly.io to run "uvicorn main:app" and find our application
__all__ = ["app"]
