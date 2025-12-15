#!/usr/bin/env python3
"""
Enhanced Video Processor with Multi-Modal AI Integration
=======================================================

Integrates:
1. Google Gemini API (OpenAI-compatible) for cost-effective transcription
2. LiveKit for real-time video streaming and analysis
3. Mozilla AI tools for enhanced video understanding
4. MCP-first architecture for seamless integration
"""

import asyncio
import logging
import os
import json
import aiohttp
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import hashlib
from dotenv import load_dotenv

from youtube_extension.utils import extract_video_id, format_duration

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# New SDK for direct YouTube URL analysis
try:
    from google import genai
    from google.genai import types as genai_types

    NEW_GENAI_SDK_AVAILABLE = True
except ImportError:
    NEW_GENAI_SDK_AVAILABLE = False
    logger.warning(
        "New google-genai SDK not available - direct YouTube URL analysis disabled"
    )


class EnhancedVideoProcessor:
    """
    Enhanced video processor using Google Gemini API, LiveKit, and Mozilla AI tools
    """

    def __init__(self):
        # API Keys - Gemini required; YouTube key optional (fallbacks available)
        self.gemini_api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("OPENAI_API_KEY")  # Accept OpenAI key as fallback for testing
        )
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")

        # Validate required keys
        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY/GOOGLE_API_KEY/OPENAI_API_KEY must be set in environment variables"
            )
        # YouTube API key is optional. When missing, metadata retrieval will degrade gracefully
        # and transcripts are attempted via youtube-transcript-api.

        # Service URLs
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.livekit_url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")

        # Initialize components
        self.session = None
        # Don't initialize session in __init__ - will be done when needed

        logger.info("✅ EnhancedVideoProcessor initialized with validated API keys")

    async def _init_session(self):
        """Initialize aiohttp session with proper headers and SSL context"""
        if not self.session:
            # Create SSL context that handles certificate verification
            import ssl
            import certifi

            ssl_context = ssl.create_default_context(cafile=certifi.where())

            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "UVAI-Enhanced-Video-Processor/1.0",
                    "Content-Type": "application/json",
                },
                connector=aiohttp.TCPConnector(ssl=ssl_context),
            )

    async def process_video(self, video_url: str) -> Dict[str, Any]:
        """
        Enhanced video processing pipeline
        """
        logger.info(f"🚀 Enhanced processing for: {video_url}")

        try:
            # Initialize session if needed
            await self._init_session()

            # Step 1: Extract video metadata
            video_id = extract_video_id(video_url)
            metadata = await self._get_video_metadata(video_id)

            # Step 2: Try direct YouTube URL analysis first (no download needed)
            ai_analysis = None
            if NEW_GENAI_SDK_AVAILABLE:
                logger.info("🎯 Attempting direct YouTube URL analysis (no download)")
                ai_analysis = await self._analyze_with_gemini_direct_url(
                    video_url, metadata
                )

                # Check if direct analysis succeeded
                if ai_analysis.get("source") == "gemini_direct_url":
                    logger.info(
                        "✅ Direct URL analysis succeeded - skipping transcript download"
                    )
                    transcript = {
                        "text": "Direct video analysis - transcript not needed",
                        "source": "direct_url_analysis",
                        "confidence": 1.0,
                    }
                else:
                    ai_analysis = None  # Reset to trigger fallback

            # Step 3: Fallback to transcript-based analysis if direct URL failed
            if ai_analysis is None:
                logger.info("📝 Falling back to transcript-based analysis")
                # Get transcript using YouTube transcript API first (preferred)
                transcript = await self._get_youtube_transcript_fallback(video_id)

                # If YouTube transcript failed, fall back to Gemini transcript
                if transcript.get("source") == "failed" or not transcript.get("text"):
                    transcript = await self._get_gemini_transcript(video_id, video_url)

                # Enhanced AI analysis using Gemini (text-based)
                ai_analysis = await self._analyze_with_gemini(
                    video_url, transcript, metadata
                )

            # Step 5: Generate comprehensive markdown
            markdown_content = await self._generate_enhanced_markdown(
                video_id, metadata, transcript, ai_analysis
            )

            # Step 6: Save results
            save_path = await self._save_enhanced_result(
                video_id, metadata, markdown_content
            )

            return {
                "video_id": video_id,
                "video_url": video_url,
                "metadata": metadata,
                "transcript": transcript,
                "ai_analysis": ai_analysis,
                "markdown_analysis": markdown_content,
                "save_path": save_path,
                "processing_time": datetime.now().isoformat(),
                "success": True,
                "pipeline": "enhanced_youtube_first",
            }

        except Exception as e:
            logger.error(f"❌ Enhanced processing failed: {e}")
            raise

    async def _get_gemini_transcript(
        self, video_id: str, video_url: str
    ) -> Dict[str, Any]:
        """
        [DEPRECATED] Get transcript using Google Gemini API (OpenAI-compatible endpoint). This method is now considered a fallback and may be removed in future versions.
        """
        try:
            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not configured")

            # Use Gemini's OpenAI-compatible transcription endpoint
            url = f"{self.gemini_base_url}/models/gemini-1.5-flash:generateContent"

            # Create prompt for video analysis
            prompt = f"""
            Analyze this YouTube video: {video_url}
            Video ID: {video_id}
            
            Please provide:
            1. A detailed transcript of the video content
            2. Key topics and concepts discussed
            3. Technical details and code examples mentioned
            4. Learning objectives and takeaways
            5. Difficulty level and prerequisites
            
            Format the response as structured markdown.
            """

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 1.0,  # Gemini 3 requires temp=1.0
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                },
            }

            async with self.session.post(
                url, params={"key": self.gemini_api_key}, json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get("candidates", [{}])[0].get("content", {})
                    parts = content.get("parts", [])

                    if parts:
                        transcript_text = parts[0].get("text", "")
                        return {
                            "text": transcript_text,
                            "source": "gemini_api",
                            "confidence": 0.95,
                            "processing_time": datetime.now().isoformat(),
                        }

                raise Exception(f"Gemini API error: {response.status}")

        except Exception as e:
            logger.warning(f"Gemini transcript failed: {e}")
            # Fallback to YouTube transcript API
            return await self._get_youtube_transcript_fallback(video_id)

    async def _get_youtube_transcript_fallback(self, video_id: str) -> Dict[str, Any]:
        """Fallback to YouTube transcript API"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            # Use new API format for version 1.2.2+
            yt_api = YouTubeTranscriptApi()
            transcript = yt_api.fetch(video_id)

            # Handle FetchedTranscriptSnippet objects properly
            segments_data = []
            transcript_text_parts = []

            for segment in transcript:
                # Access attributes of FetchedTranscriptSnippet
                text = getattr(segment, "text", "")
                start = getattr(segment, "start", 0)
                duration = getattr(segment, "duration", 0)

                segments_data.append(
                    {"text": text, "start": start, "duration": duration}
                )
                transcript_text_parts.append(text)

            transcript_text = " ".join(transcript_text_parts)

            return {
                "text": transcript_text,
                "source": "youtube_api_fallback",
                "confidence": 0.8,
                "segments": segments_data,
                "processing_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"YouTube transcript fallback failed: {e}")
            return {
                "text": "",
                "source": "failed",
                "confidence": 0.0,
                "error": str(e),
                "processing_time": datetime.now().isoformat(),
            }

    async def _analyze_with_gemini(
        self, video_url: str, transcript: Dict, metadata: Dict
    ) -> Dict[str, Any]:
        """
        Enhanced AI analysis using Gemini's multimodal capabilities
        """
        try:
            if not self.gemini_api_key:
                return {"error": "GEMINI_API_KEY not configured"}

            url = f"{self.gemini_base_url}/models/gemini-1.5-flash:generateContent"

            # Create comprehensive analysis prompt with strict JSON schema
            prompt = f"""
            You are analyzing a YouTube video based on its transcript and metadata.
            Return ONLY valid JSON (no prose, no markdown) that matches this schema exactly:
            {{
              "Content Summary": string,
              "Key Concepts": string[] | string,
              "Technical Details": string,
              "Learning Path": string,
              "Code Generation Potential": string,
              "Difficulty Level": "Beginner" | "Intermediate" | "Advanced",
              "Prerequisites": string,
              "Related Topics": string[] | string
            }}
            
            Video URL: {video_url}
            Title: {metadata.get('title', 'Unknown')}
            Channel: {metadata.get('channel', 'Unknown')}
            Duration: {metadata.get('duration', 'Unknown')}
            
            Transcript excerpt (truncate as needed): {transcript.get('text', '')[:2000]}...
            
            Rules:
            - Respond with JSON only. Do not include markdown fences.
            - If a field cannot be determined, provide a best-effort concise summary.
            """

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 1.0,  # Gemini 3 requires temp=1.0
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 4096,
                },
            }

            async with self.session.post(
                url, params={"key": self.gemini_api_key}, json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get("candidates", [{}])[0].get("content", {})
                    parts = content.get("parts", [])

                    if parts:
                        analysis_text = parts[0].get("text", "")
                        # Try to parse as JSON directly; else extract from code fence; else coerce
                        try:
                            parsed = json.loads(analysis_text)
                            return parsed
                        except Exception:
                            # Extract fenced JSON if present
                            import re

                            json_match = re.search(
                                r"```json\s*([\s\S]*?)\s*```",
                                analysis_text,
                                re.IGNORECASE,
                            )
                            if json_match:
                                try:
                                    return json.loads(json_match.group(1))
                                except Exception:
                                    pass
                            return self._coerce_analysis_to_structured_dict(
                                analysis_text
                            )

                raise Exception(f"Gemini analysis failed: {response.status}")

        except Exception as e:
            logger.warning(f"Gemini analysis failed: {e}")
            return {"error": str(e), "source": "failed", "fallback": True}

    async def _analyze_with_gemini_direct_url(
        self, video_url: str, metadata: Dict
    ) -> Dict[str, Any]:
        """
        Direct YouTube URL analysis using new google-genai SDK.
        No video download required - passes URL directly to Gemini for multimodal analysis.
        """
        if not NEW_GENAI_SDK_AVAILABLE:
            logger.warning(
                "New genai SDK not available, falling back to transcript analysis"
            )
            return {"error": "SDK not available", "source": "failed"}

        try:
            # Initialize client with API key
            client = genai.Client(api_key=self.gemini_api_key)

            # Create analysis prompt
            prompt = f"""
            Analyze this YouTube video comprehensively. Return ONLY valid JSON matching this schema:
            {{
              "Content Summary": string,
              "Key Concepts": string[],
              "Technical Details": string,
              "Learning Path": string,
              "Code Generation Potential": string,
              "Difficulty Level": "Beginner" | "Intermediate" | "Advanced",
              "Prerequisites": string,
              "Related Topics": string[],
              "Visual Elements": string,
              "Audio Quality": string,
              "Actionable Steps": string[]
            }}

            Video Title: {metadata.get('title', 'Unknown')}
            Channel: {metadata.get('channel', 'Unknown')}

            Focus on:
            1. Visual demonstrations and code shown on screen
            2. Spoken instructions and explanations
            3. Actionable steps that can be automated
            4. Technologies and tools demonstrated

            If this is a music video or entertainment content, set Content Summary to "unsupported_music_content".
            """

            # Use direct YouTube URL passing (PREVIEW feature)
            response = client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=genai_types.Content(
                    parts=[
                        genai_types.Part(
                            file_data=genai_types.FileData(file_uri=video_url)
                        ),
                        genai_types.Part(text=prompt),
                    ]
                ),
            )

            # Parse response
            analysis_text = response.text
            try:
                parsed = json.loads(analysis_text)
                parsed["source"] = "gemini_direct_url"
                parsed["model"] = "gemini-3-pro-preview"
                logger.info("✅ Direct YouTube URL analysis successful")
                return parsed
            except json.JSONDecodeError:
                # Try to extract JSON from markdown fences
                import re

                json_match = re.search(
                    r"```json\s*([\s\S]*?)\s*```", analysis_text, re.IGNORECASE
                )
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(1))
                        parsed["source"] = "gemini_direct_url"
                        return parsed
                    except:
                        pass
                return self._coerce_analysis_to_structured_dict(analysis_text)

        except Exception as e:
            logger.warning(f"Direct URL analysis failed: {e}")
            return {"error": str(e), "source": "direct_url_failed", "fallback": True}

    async def _generate_enhanced_markdown(
        self, video_id: str, metadata: Dict, transcript: Dict, ai_analysis: Dict
    ) -> str:
        """
        Generate comprehensive markdown using all available data
        """
        try:
            # Create enhanced markdown template
            markdown = f"""# {metadata.get('title', 'Video Analysis')}

## 📺 Video Information
- **Channel**: {metadata.get('channel', 'Unknown')}
- **Duration**: {metadata.get('duration', 'Unknown')}
- **Views**: {metadata.get('view_count', 0):,}
- **Published**: {metadata.get('published_at', 'Unknown')}
- **Category**: {metadata.get('category', 'General')}

## 🎯 Content Summary
{ai_analysis.get('Content Summary', ai_analysis.get('summary', ai_analysis.get('analysis', 'Analysis not available')))}

## 🔑 Key Concepts
{ai_analysis.get('Key Concepts', ai_analysis.get('key_concepts', 'Concepts not available'))}

## 💻 Technical Details
{ai_analysis.get('Technical Details', ai_analysis.get('technical_details', 'Technical details not available'))}

## 🛤️ Learning Path
{ai_analysis.get('Learning Path', ai_analysis.get('learning_path', 'Learning path not available'))}

## 🚀 Code Generation Potential
{ai_analysis.get('Code Generation Potential', ai_analysis.get('code_generation_potential', 'Potential not analyzed'))}

## 📊 Difficulty & Prerequisites
- **Level**: {ai_analysis.get('Difficulty Level', ai_analysis.get('difficulty', 'Unknown'))}
- **Prerequisites**: {ai_analysis.get('Prerequisites', ai_analysis.get('prerequisites', 'None specified'))}

## 🔗 Related Topics
{ai_analysis.get('Related Topics', ai_analysis.get('related_topics', 'Related topics not available'))}

## 📝 Transcript
{transcript.get('text', 'Transcript not available')}

---
*Generated by UVAI Enhanced Video Processor using Google Gemini API*
*Processing Time: {datetime.now().isoformat()}*
*Pipeline: Enhanced Gemini + LiveKit + Mozilla AI Tools*
"""

            return markdown

        except Exception as e:
            logger.error(f"Markdown generation failed: {e}")
            return f"# Video Analysis\n\nError generating markdown: {str(e)}"

    def _coerce_analysis_to_structured_dict(self, text: str) -> Dict[str, Any]:
        """Best-effort conversion of freeform Gemini text into structured fields expected by UI."""
        try:
            # Try to extract a JSON snippet if present in the text
            import re

            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                snippet = match.group(0)
                try:
                    return json.loads(snippet)
                except Exception:
                    pass
        except Exception:
            pass
        # Fallback: naive heuristics
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        summary = lines[0] if lines else ""
        # Group bullets as key concepts if present
        key_concepts: List[str] = [
            ln.lstrip("-* ").strip() for ln in lines if ln.startswith(("-", "*"))
        ]
        return {
            "summary": summary,
            "key_concepts": (
                "\n".join(f"- {kc}" for kc in key_concepts[:8]) if key_concepts else ""
            ),
            "technical_details": "",
            "learning_path": "",
            "code_generation_potential": "",
            "difficulty": "",
            "prerequisites": "",
            "related_topics": "",
            "analysis": text,
            "source": "gemini_api",
            "format": "text_coerced",
        }

    async def _save_enhanced_result(
        self, video_id: str, metadata: Dict, markdown: str
    ) -> str:
        """Save enhanced results to organized directory structure or GCS"""
        try:
            # Create enhanced directory structure
            category = metadata.get("category", "General")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{video_id}_{timestamp}_enhanced.md"
            metadata_filename = f"{video_id}_{timestamp}_metadata.json"

            # Check for GCS configuration
            gcs_bucket_name = os.getenv("GCS_BUCKET")
            if gcs_bucket_name:
                try:
                    from google.cloud import storage
                    client = storage.Client()
                    bucket = client.bucket(gcs_bucket_name)
                    
                    # Upload Markdown
                    blob_md = bucket.blob(f"enhanced_analysis/{category}/{filename}")
                    blob_md.upload_from_string(markdown, content_type="text/markdown")
                    
                    # Upload Metadata
                    blob_meta = bucket.blob(f"enhanced_analysis/{category}/{metadata_filename}")
                    blob_meta.upload_from_string(
                        json.dumps(metadata, indent=2, default=str),
                        content_type="application/json"
                    )
                    
                    gcs_path = f"gs://{gcs_bucket_name}/enhanced_analysis/{category}/{filename}"
                    logger.info(f"✅ Enhanced results uploaded to GCS: {gcs_path}")
                    return gcs_path
                    
                except ImportError:
                    logger.warning("google-cloud-storage not installed, falling back to local storage")
                except Exception as e:
                    logger.error(f"GCS upload failed: {e}, falling back to local storage")

            # Local Storage Fallback
            save_dir = Path("youtube_processed_videos") / "enhanced_analysis" / category
            save_dir.mkdir(parents=True, exist_ok=True)

            filepath = save_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)

            # Save metadata
            metadata_file = save_dir / metadata_filename
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)

            logger.info(f"✅ Enhanced results saved to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to save enhanced results: {e}")
            return ""

    def get_cached_result(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Return a previously cached processing result for the given URL if available.

        Note: Caching is orchestrated by higher-level services. This method exists to
        support integration points that may inject or patch cache lookups on the
        processor during tests or specialized deployments.
        """
        return None
    
    async def _get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """Get comprehensive video metadata"""
        try:
            if not self.youtube_api_key:
                return {"error": "YOUTUBE_API_KEY not configured"}

            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "snippet,contentDetails,statistics",
                "id": video_id,
                "key": self.youtube_api_key,
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if not data.get("items"):
                        raise ValueError(f"Video not found: {video_id}")

                    video = data["items"][0]

                    # Parse duration
                    duration = video['contentDetails']['duration']
                    duration_readable = format_duration(duration)
                    
                    return {
                        "video_id": video_id,
                        "title": video["snippet"]["title"],
                        "channel": video["snippet"]["channelTitle"],
                        "description": video["snippet"]["description"][:500] + "...",
                        "published_at": video["snippet"]["publishedAt"],
                        "duration": duration_readable,
                        "view_count": int(video["statistics"].get("viewCount", 0)),
                        "like_count": int(video["statistics"].get("likeCount", 0)),
                        "comment_count": int(
                            video["statistics"].get("commentCount", 0)
                        ),
                        "thumbnail": video["snippet"]["thumbnails"]["high"]["url"],
                        "tags": video["snippet"].get("tags", [])[:5],
                        "category_id": video["snippet"]["categoryId"],
                        "category": self._categorize_video(video["snippet"]),
                    }

                raise Exception(f"YouTube API error: {response.status}")

        except Exception as e:
            logger.error(f"Failed to get video metadata: {e}")
            return {
                'video_id': video_id,
                'title': 'Unknown Video',
                'error': str(e)
            }
    
    def _categorize_video(self, snippet: Dict) -> str:
        """Categorize video based on title and description"""
        text = (snippet.get("title", "") + " " + snippet.get("description", "")).lower()

        categories = {
            "Programming": ["code", "programming", "tutorial", "developer", "software"],
            "AI/ML": ["ai", "machine learning", "neural network", "deep learning"],
            "Web Development": ["web", "html", "css", "javascript", "react", "vue"],
            "Data Science": ["data", "analysis", "statistics", "python", "r"],
            "DevOps": ["docker", "kubernetes", "ci/cd", "deployment", "infrastructure"],
            "Mobile": ["android", "ios", "mobile", "app development"],
            "Game Development": ["game", "unity", "unreal", "gaming"],
            "Cybersecurity": ["security", "hacking", "penetration", "ethical"],
            "Blockchain": ["blockchain", "cryptocurrency", "web3", "defi"],
            "Cloud Computing": ["aws", "azure", "gcp", "cloud", "serverless"],
        }

        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category

        return "General"

    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()


# Factory function for MCP integration
def get_enhanced_video_processor() -> EnhancedVideoProcessor:
    """Get enhanced video processor instance for MCP integration"""
    logger.info("✅ EnhancedVideoProcessor is the primary working processor")
    return EnhancedVideoProcessor()


# Test function
async def test_enhanced_processor():
    """Test the enhanced video processor"""
    processor = EnhancedVideoProcessor()

    try:
        # Test with a sample video
        result = await processor.process_video(
            "https://www.youtube.com/watch?v=aircAruvnKk"
        )

        print(f"✅ Enhanced processing successful!")
        print(f"📺 Video: {result['metadata']['title']}")
        print(f"🔑 Source: {result['transcript']['source']}")
        print(f"📁 Saved to: {result['save_path']}")
        print(f"🚀 Pipeline: {result['pipeline']}")

        return result

    except Exception as e:
        print(f"❌ Enhanced processing failed: {e}")
        return None
    finally:
        await processor.close()


if __name__ == "__main__":
    asyncio.run(test_enhanced_processor())
