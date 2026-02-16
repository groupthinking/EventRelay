#!/usr/bin/env python3
"""
Transcription MCP Server
========================

MCP server that provides transcription and text processing tools.
Handles video transcription, text analysis, and natural language processing.
"""

import json
import os
import sys
from typing import Any, Dict
import requests

BASE = os.getenv("YOUTUBE_EXTENSION_BASE", "http://localhost:8000")

def list_tools() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": "transcribe_video",
                "description": "Transcribe audio from YouTube video to text with timestamps",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "video_url": {"type": "string", "description": "YouTube video URL"},
                        "include_timestamps": {"type": "boolean", "default": True},
                        "language": {"type": "string", "default": "en"}
                    },
                    "required": ["video_url"]
                },
            },
            {
                "name": "analyze_transcript_sentiment",
                "description": "Analyze sentiment and emotional tone of transcript text",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": "Transcript text to analyze"},
                        "granularity": {"type": "string", "enum": ["overall", "sentence", "paragraph"], "default": "overall"}
                    },
                    "required": ["transcript"]
                },
            },
            {
                "name": "extract_key_phrases",
                "description": "Extract important keywords and phrases from transcript",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": "Transcript text"},
                        "max_phrases": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50}
                    },
                    "required": ["transcript"]
                },
            },
            {
                "name": "detect_transcript_language",
                "description": "Detect the primary language of transcript text",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": "Transcript text"}
                    },
                    "required": ["transcript"]
                },
            },
            {
                "name": "summarize_transcript_sections",
                "description": "Break transcript into logical sections and provide summaries",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": "Full transcript text"},
                        "max_sections": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20}
                    },
                    "required": ["transcript"]
                },
            },
            {
                "name": "search_transcript",
                "description": "Search for specific terms or phrases within transcript with context",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "transcript": {"type": "string", "description": "Transcript text"},
                        "query": {"type": "string", "description": "Search term or phrase"},
                        "context_words": {"type": "integer", "default": 50, "minimum": 10, "maximum": 200}
                    },
                    "required": ["transcript", "query"]
                },
            }
        ]
    }

def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if name == "transcribe_video":
            return _transcribe_video(arguments)
        elif name == "analyze_transcript_sentiment":
            return _analyze_transcript_sentiment(arguments)
        elif name == "extract_key_phrases":
            return _extract_key_phrases(arguments)
        elif name == "detect_transcript_language":
            return _detect_transcript_language(arguments)
        elif name == "summarize_transcript_sections":
            return _summarize_transcript_sections(arguments)
        elif name == "search_transcript":
            return _search_transcript(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        return {
            "error": str(e),
            "tool": name,
            "status": "failed"
        }

def _transcribe_video(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Transcribe video audio to text"""
    video_url = arguments.get("video_url")
    include_timestamps = arguments.get("include_timestamps", True)
    language = arguments.get("language", "en")

    # Mock transcription result
    transcript_data = {
        "video_url": video_url,
        "language": language,
        "duration": "10:30",
        "confidence": 0.92,
        "transcript": "Welcome to this educational video about technology and development. Today we'll explore key concepts and best practices that will help you build better applications."
    }

    if include_timestamps:
        transcript_data["segments"] = [
            {"start": 0.0, "end": 3.5, "text": "Welcome to this educational video"},
            {"start": 3.5, "end": 7.2, "text": "about technology and development."},
            {"start": 7.2, "end": 10.3, "text": "Today we'll explore key concepts and best practices"}
        ]

    return transcript_data

def _analyze_transcript_sentiment(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze sentiment of transcript"""
    transcript = arguments.get("transcript")
    granularity = arguments.get("granularity", "overall")

    sentiment_analysis = {
        "transcript_length": len(transcript) if transcript else 0,
        "overall_sentiment": {
            "polarity": 0.75,
            "subjectivity": 0.60,
            "label": "positive"
        }
    }

    if granularity == "sentence":
        sentiment_analysis["sentence_analysis"] = [
            {"text": "Welcome to this educational video", "sentiment": "positive", "confidence": 0.85},
            {"text": "about technology and development", "sentiment": "neutral", "confidence": 0.70}
        ]

    return sentiment_analysis

def _extract_key_phrases(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key phrases from transcript"""
    transcript = arguments.get("transcript")
    max_phrases = arguments.get("max_phrases", 10)

    key_phrases = [
        {"phrase": "educational video", "relevance": 0.95, "frequency": 2},
        {"phrase": "technology development", "relevance": 0.88, "frequency": 1},
        {"phrase": "key concepts", "relevance": 0.85, "frequency": 1},
        {"phrase": "best practices", "relevance": 0.82, "frequency": 1},
        {"phrase": "build applications", "relevance": 0.80, "frequency": 1}
    ]

    return {
        "transcript_length": len(transcript) if transcript else 0,
        "key_phrases": key_phrases[:max_phrases],
        "total_phrases_found": len(key_phrases)
    }

def _detect_transcript_language(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Detect language of transcript"""
    transcript = arguments.get("transcript")

    # Mock language detection
    return {
        "detected_language": "en",
        "language_name": "English",
        "confidence": 0.98,
        "alternative_languages": [
            {"language": "en-US", "confidence": 0.95},
            {"language": "en-GB", "confidence": 0.85}
        ]
    }

def _summarize_transcript_sections(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize transcript sections"""
    transcript = arguments.get("transcript")
    max_sections = arguments.get("max_sections", 5)

    sections = [
        {
            "section_id": 1,
            "start_time": "00:00",
            "end_time": "02:30",
            "title": "Introduction",
            "summary": "Welcome and overview of the video content and learning objectives."
        },
        {
            "section_id": 2,
            "start_time": "02:30",
            "end_time": "06:15",
            "title": "Main Concepts",
            "summary": "Explanation of core technology concepts with examples and diagrams."
        },
        {
            "section_id": 3,
            "start_time": "06:15",
            "end_time": "08:45",
            "title": "Implementation",
            "summary": "Step-by-step implementation guide with code examples and best practices."
        },
        {
            "section_id": 4,
            "start_time": "08:45",
            "end_time": "10:30",
            "title": "Conclusion",
            "summary": "Summary of key takeaways and next steps for learners."
        }
    ]

    return {
        "total_sections": len(sections),
        "sections": sections[:max_sections],
        "transcript_coverage": "100%"
    }

def _search_transcript(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search transcript for specific terms"""
    transcript = arguments.get("transcript")
    query = arguments.get("query")
    context_words = arguments.get("context_words", 50)

    # Mock search results
    search_results = [
        {
            "match_text": "technology and development",
            "start_position": 45,
            "end_position": 70,
            "context": "...Welcome to this educational video about technology and development. Today we'll explore key concepts...",
            "relevance_score": 0.95
        },
        {
            "match_text": "key concepts",
            "start_position": 85,
            "end_position": 97,
            "context": "...technology and development. Today we'll explore key concepts and best practices that will help...",
            "relevance_score": 0.88
        }
    ]

    return {
        "query": query,
        "total_matches": len(search_results),
        "results": search_results,
        "transcript_length": len(transcript) if transcript else 0
    }

def main():
    """Main MCP server loop"""
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            if req.get("method") == "tools/list":
                result = list_tools()
                sys.stdout.write(json.dumps({"result": result}) + "\n")
                sys.stdout.flush()
            elif req.get("method") == "tools/call":
                params = req.get("params", {})
                name = params.get("name")
                args = params.get("arguments", {})
                result = call_tool(name, args)
                sys.stdout.write(json.dumps({"result": result}) + "\n")
                sys.stdout.flush()
            else:
                sys.stdout.write(json.dumps({"error": {"message": "unknown method"}}) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"error": {"message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
