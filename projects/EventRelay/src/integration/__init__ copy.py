"""
EventRelay API Integrations
---------------------------
Unified service layer for external API integrations.

Services:
- GeminiVideoService: Gemini 3 Pro Preview for video analysis
- YouTubeAPIService: YouTube Data API for metadata/transcripts
- VercelDeployService: Vercel CLI for deployments
- StripePaymentService: Stripe for monetization
- SupabaseDBService: Supabase for database/auth
- OpenAIVoiceService: OpenAI for voice agents (fallback)
"""

from .gemini_video import GeminiVideoService, VideoAnalysisResult
from .youtube_api import YouTubeAPIService
from .vercel_deploy import VercelDeployService
from .stripe_payments import StripePaymentService
from .supabase_db import SupabaseDBService
from .openai_voice import OpenAIVoiceService, OpenAIVideoFallback

__all__ = [
    "GeminiVideoService",
    "VideoAnalysisResult",
    "YouTubeAPIService", 
    "VercelDeployService",
    "StripePaymentService",
    "SupabaseDBService",
    "OpenAIVoiceService",
    "OpenAIVideoFallback",
]
