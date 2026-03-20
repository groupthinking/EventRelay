#!/usr/bin/env python3
"""
Generate OpenAPI spec from EventRelay's FastAPI backend.

FastAPI auto-generates OpenAPI schemas. This script extracts it
and saves it for Stainless SDK generation.

Usage:
    python scripts/generate_openapi.py > openapi.json

Then feed openapi.json to Stainless:
    npx stainless init --input openapi.json
"""

import json
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def main():
    """Extract OpenAPI spec from the FastAPI app."""
    try:
        # Import the FastAPI app
        from youtube_extension.backend.api import app
        
        # FastAPI provides .openapi() method
        openapi_schema = app.openapi()
        
        # Add Stainless-compatible extensions
        openapi_schema["info"]["x-stainless-config"] = {
            "package-name": {
                "python": "uvai",
                "typescript": "@uvai/sdk"
            },
            "api-url": "https://api.uvai.io",
            "topics": {
                "videos": "Video processing and analysis",
                "projects": "Code generation and deployment",
                "agents": "AI agent orchestration"
            }
        }
        
        print(json.dumps(openapi_schema, indent=2))
        
    except ImportError as e:
        print(f"Error: Could not import FastAPI app: {e}", file=sys.stderr)
        print("Make sure you're running from the EventRelay root with dependencies installed.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
