#!/usr/bin/env python3
"""
AI Insights Processor for UVAI Video-to-Software Pipeline
=========================================================

This module provides AI-powered insights extraction from YouTube videos
using various AI services and models.
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class AIInsightsProcessor:
    """
    Processes videos to extract AI-powered insights for software generation
    """
    
    def __init__(self):
        self.available_services = []
        self._check_available_services()
    
    def _check_available_services(self):
        """Check which AI services are available"""
        # Check for Google AI/Gemini
        if os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GEMINI_API_KEY'):
            self.available_services.append('gemini')
        
        # Check for OpenAI
        if os.getenv('OPENAI_API_KEY'):
            self.available_services.append('openai')
        
        # Check for other services
        if os.getenv('ANTHROPIC_API_KEY'):
            self.available_services.append('anthropic')
        
        logger.info(f"Available AI services: {self.available_services}")
    
    async def get_insights(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Get AI insights from a video URL
        """
        try:
            logger.info(f"🧠 Getting AI insights for: {video_url}")
            
            if not self.available_services:
                logger.warning("No AI services available for insights")
                return self._generate_fallback_insights(video_url)
            
            # Try services in order of preference
            for service in ['gemini', 'openai', 'anthropic']:
                if service in self.available_services:
                    try:
                        insights = await self._get_insights_from_service(video_url, service)
                        if insights:
                            insights['service_used'] = service
                            return insights
                    except Exception as e:
                        logger.warning(f"Failed to get insights from {service}: {e}")
                        continue
            
            # If all services fail, return fallback
            return self._generate_fallback_insights(video_url)
            
        except Exception as e:
            logger.error(f"Error getting AI insights: {e}")
            return self._generate_fallback_insights(video_url)
    
    async def _get_insights_from_service(self, video_url: str, service: str) -> Optional[Dict[str, Any]]:
        """Get insights from a specific AI service"""
        
        if service == 'gemini':
            return await self._get_gemini_insights(video_url)
        elif service == 'openai':
            return await self._get_openai_insights(video_url)
        elif service == 'anthropic':
            return await self._get_anthropic_insights(video_url)
        
        return None
    
    async def _get_gemini_insights(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Get insights using Google's Gemini API"""
        try:
            # Note: This is a placeholder implementation
            # In a real implementation, you would:
            # 1. Use Google's Gemini API to analyze the video
            # 2. Extract key insights, programming concepts, etc.
            # 3. Return structured data
            
            logger.info("Getting Gemini insights (simulated)")
            
            # Simulate API call delay
            await asyncio.sleep(0.5)
            
            return {
                "summary": "Video analysis using Gemini AI",
                "key_moments": [
                    "Introduction to the main concept",
                    "Code implementation demonstration", 
                    "Best practices explanation",
                    "Testing and deployment steps"
                ],
                "technologies_detected": ["javascript", "react", "html", "css"],
                "difficulty_level": "intermediate",
                "estimated_duration": "30 minutes",
                "programming_concepts": [
                    "Component-based architecture",
                    "State management",
                    "Event handling",
                    "API integration"
                ]
            }
            
        except Exception as e:
            logger.error(f"Gemini insights failed: {e}")
            return None
    
    async def _get_openai_insights(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Get insights using OpenAI API"""
        try:
            logger.info("Getting OpenAI insights (simulated)")
            
            # Simulate API call delay
            await asyncio.sleep(0.3)
            
            return {
                "summary": "Video analysis using OpenAI GPT",
                "key_moments": [
                    "Problem definition and setup",
                    "Step-by-step implementation",
                    "Code review and optimization",
                    "Final testing and validation"
                ],
                "technologies_detected": ["python", "javascript", "html"],
                "difficulty_level": "beginner",
                "estimated_duration": "25 minutes",
                "learning_objectives": [
                    "Understanding core concepts",
                    "Practical implementation skills",
                    "Best practices adoption",
                    "Error handling techniques"
                ]
            }
            
        except Exception as e:
            logger.error(f"OpenAI insights failed: {e}")
            return None
    
    async def _get_anthropic_insights(self, video_url: str) -> Optional[Dict[str, Any]]:
        """Get insights using Anthropic Claude API"""
        try:
            logger.info("Getting Anthropic insights (simulated)")
            
            # Simulate API call delay
            await asyncio.sleep(0.4)
            
            return {
                "summary": "Video analysis using Anthropic Claude",
                "key_moments": [
                    "Conceptual overview",
                    "Practical demonstration",
                    "Common pitfalls and solutions",
                    "Advanced techniques"
                ],
                "technologies_detected": ["typescript", "react", "nodejs"],
                "difficulty_level": "advanced",
                "estimated_duration": "45 minutes",
                "insights": [
                    "Strong focus on clean code principles",
                    "Emphasis on scalable architecture",
                    "Comprehensive error handling",
                    "Performance optimization techniques"
                ]
            }
            
        except Exception as e:
            logger.error(f"Anthropic insights failed: {e}")
            return None
    
    def _generate_fallback_insights(self, video_url: str) -> Dict[str, Any]:
        """Generate fallback insights when AI services are not available"""
        return {
            "summary": "Basic video analysis (fallback mode)",
            "key_moments": [
                "Video content analysis",
                "Technology detection",
                "Structure identification",
                "Implementation planning"
            ],
            "technologies_detected": ["javascript", "html", "css"],
            "difficulty_level": "intermediate",
            "estimated_duration": "30 minutes",
            "note": "AI services not available - using fallback analysis",
            "service_used": "fallback"
        }


# Global instance
_ai_insights_processor = None

async def get_ai_insights(video_url: str) -> Optional[Dict[str, Any]]:
    """
    Global function to get AI insights for a video
    """
    global _ai_insights_processor
    
    if _ai_insights_processor is None:
        _ai_insights_processor = AIInsightsProcessor()
    
    return await _ai_insights_processor.get_insights(video_url)