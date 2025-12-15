#!/usr/bin/env python3
"""
YouTube UVAI MCP Server - Enhanced Integration
Integrates with shared state coordination system and provides comprehensive video-to-action capabilities
"""

import asyncio
import json
import logging
import sys
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse, parse_qs
import re
import websockets
import sqlite3
from pathlib import Path

# Add the existing UVAI path to import the existing processor
# REMOVED: sys.path.append removed

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource
)

# Video processing imports
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsRetrievalError
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import yt_dlp
    HAS_VIDEO_DEPS = True
except ImportError:
    HAS_VIDEO_DEPS = False
    logging.warning("Video dependencies not installed. Some features will be unavailable.")

# AI/ML imports
try:
    import openai
    from transformers import pipeline
    import torch
    HAS_AI_DEPS = True
except ImportError:
    HAS_AI_DEPS = False
    logging.warning("AI dependencies not installed. Some features will be unavailable.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("youtube_uvai_mcp")

class SharedStateClient:
    """Client for connecting to the MCP State Coordinator"""
    
    def __init__(self, coordinator_url: str = "ws://localhost:8005"):
        self.coordinator_url = coordinator_url
        self.websocket = None
        self.server_id = "youtube-uvai-processor"
        self.capabilities = [
            "video_analysis",
            "transcript_extraction", 
            "tutorial_generation",
            "ai_reasoning",
            "content_structure_analysis",
            "uvai_processing"
        ]
        self.is_connected = False
    
    async def connect(self):
        """Connect to the state coordinator"""
        try:
            self.websocket = await websockets.connect(self.coordinator_url)
            self.is_connected = True
            
            # Register this server
            await self.register_server()
            logger.info(f"Connected to MCP State Coordinator at {self.coordinator_url}")
            
        except Exception as e:
            logger.warning(f"Failed to connect to state coordinator: {e}")
            self.is_connected = False
    
    async def register_server(self):
        """Register this server with the coordinator"""
        if not self.websocket:
            return
        
        message = {
            "type": "register_server",
            "server_id": self.server_id,
            "capabilities": self.capabilities,
            "metadata": {
                "description": "YouTube UVAI MCP Server with video-to-action capabilities",
                "version": "1.0.0",
                "tools_count": 12
            }
        }
        
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        
        if response_data.get("status") == "registered":
            logger.info("Successfully registered with state coordinator")
    
    async def update_status(self, status: str, current_task: str = None):
        """Update server status with coordinator"""
        if not self.websocket:
            return
        
        message = {
            "type": "update_status",
            "server_id": self.server_id,
            "status": status,
            "current_task": current_task
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def submit_action(self, action_type: str, payload: Dict[str, Any], dependencies: List[str] = None):
        """Submit an action to the shared state system"""
        if not self.websocket:
            return None
        
        message = {
            "type": "submit_action",
            "server_id": self.server_id,
            "action_type": action_type,
            "payload": payload,
            "dependencies": dependencies or []
        }
        
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        
        return response_data.get("action_id")
    
    async def get_available_servers(self):
        """Get list of available servers from coordinator"""
        if not self.websocket:
            return {}
        
        message = {"type": "get_servers"}
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        response_data = json.loads(response)
        
        return response_data.get("servers", {})

class EnhancedYouTubeProcessor:
    """Enhanced YouTube processor with shared state integration"""
    
    def __init__(self):
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.assemblyai_api_key = os.getenv('ASSEMBLYAI_API_KEY')
        
        # Initialize services
        self.youtube_service = None
        self.nlp_pipeline = None
        self.shared_state = SharedStateClient()
        
        # Video processing cache
        self.processing_cache = {}
        self.cache_db_path = "/Users/garvey/mcp-ecosystem/shared-state/video_cache.db"
        
        self._initialize_services()
        self._initialize_cache_db()
    
    def _initialize_services(self):
        """Initialize AI and API services"""
        try:
            if self.youtube_api_key and HAS_VIDEO_DEPS:
                self.youtube_service = build('youtube', 'v3', developerKey=self.youtube_api_key)
                logger.info("YouTube API service initialized")
            
            if HAS_AI_DEPS:
                # Initialize on-demand for performance
                self.nlp_pipeline = None
                logger.info("NLP pipeline will be initialized on-demand")
                
            if self.openai_api_key:
                openai.api_key = self.openai_api_key
                logger.info("OpenAI API initialized")
                
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
    
    def _initialize_cache_db(self):
        """Initialize SQLite cache for video processing results"""
        os.makedirs(os.path.dirname(self.cache_db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS video_cache (
                video_id TEXT PRIMARY KEY,
                metadata TEXT,
                transcript_data TEXT,
                content_analysis TEXT,
                tutorial_steps TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Video processing cache initialized")
    
    async def connect_to_coordinator(self):
        """Connect to the shared state coordinator"""
        await self.shared_state.connect()
    
    def extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
            r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Invalid YouTube URL or video ID: {url}")
    
    async def get_cached_result(self, video_id: str, result_type: str) -> Optional[Dict[str, Any]]:
        """Get cached processing result"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute(f'SELECT {result_type} FROM video_cache WHERE video_id = ?', (video_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            # Update last accessed timestamp
            cursor.execute('UPDATE video_cache SET last_accessed = CURRENT_TIMESTAMP WHERE video_id = ?', (video_id,))
            conn.commit()
            conn.close()
            
            return json.loads(result[0])
        
        conn.close()
        return None
    
    async def cache_result(self, video_id: str, result_type: str, data: Dict[str, Any]):
        """Cache processing result"""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        # Insert or update cache entry
        cursor.execute(f'''
            INSERT OR REPLACE INTO video_cache (video_id, {result_type}, last_accessed)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (video_id, json.dumps(data)))
        
        conn.commit()
        conn.close()
    
    async def get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """Retrieve comprehensive video metadata with caching"""
        # Check cache first
        cached_result = await self.get_cached_result(video_id, 'metadata')
        if cached_result:
            logger.info(f"Using cached metadata for video {video_id}")
            return cached_result
        
        if not self.youtube_service:
            raise RuntimeError("YouTube API not initialized")
        
        # Notify shared state system
        if self.shared_state.is_connected:
            await self.shared_state.update_status("processing", f"Getting metadata for {video_id}")
        
        try:
            request = self.youtube_service.videos().list(
                part='snippet,statistics,contentDetails,status',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                raise ValueError(f"Video with ID {video_id} not found")
            
            video_data = response['items'][0]
            snippet = video_data['snippet']
            statistics = video_data.get('statistics', {})
            content_details = video_data.get('contentDetails', {})
            
            metadata = {
                'video_id': video_id,
                'title': snippet['title'],
                'description': snippet['description'],
                'channel_title': snippet['channelTitle'],
                'published_at': snippet['publishedAt'],
                'duration': content_details.get('duration', ''),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'tags': snippet.get('tags', []),
                'category_id': snippet.get('categoryId', ''),
                'default_language': snippet.get('defaultLanguage', 'en'),
                'processed_at': datetime.now().isoformat()
            }
            
            # Cache the result
            await self.cache_result(video_id, 'metadata', metadata)
            
            return metadata
            
        except HttpError as e:
            raise Exception(f"YouTube API error: {e}")
    
    async def get_video_transcript(self, video_id: str, languages: List[str] = None) -> Dict[str, Any]:
        """Get video transcript with caching and fallback options"""
        # Check cache first
        cached_result = await self.get_cached_result(video_id, 'transcript_data')
        if cached_result:
            logger.info(f"Using cached transcript for video {video_id}")
            return cached_result
        
        if not HAS_VIDEO_DEPS:
            raise RuntimeError("Video processing dependencies not installed")
        
        languages = languages or ['en', 'auto']
        
        # Notify shared state system
        if self.shared_state.is_connected:
            await self.shared_state.update_status("processing", f"Getting transcript for {video_id}")
        
        try:
            # Try to get existing transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id, 
                languages=languages
            )
            
            # Process transcript
            full_text = ' '.join([entry['text'] for entry in transcript_list])
            
            transcript_data = {
                'transcript_available': True,
                'transcript_entries': transcript_list,
                'full_text': full_text,
                'word_count': len(full_text.split()),
                'duration_seconds': transcript_list[-1]['start'] + transcript_list[-1]['duration'] if transcript_list else 0,
                'source': 'youtube_auto_transcript',
                'processed_at': datetime.now().isoformat()
            }
            
            # Cache the result
            await self.cache_result(video_id, 'transcript_data', transcript_data)
            
            return transcript_data
            
        except TranscriptsRetrievalError:
            logger.warning(f"No transcript available for video {video_id}")
            transcript_data = {
                'transcript_available': False,
                'transcript_entries': [],
                'full_text': '',
                'word_count': 0,
                'duration_seconds': 0,
                'source': 'none',
                'error': 'No transcript available',
                'processed_at': datetime.now().isoformat()
            }
            
            # Cache the negative result too
            await self.cache_result(video_id, 'transcript_data', transcript_data)
            return transcript_data
    
    async def ai_reasoning_engine(self, video_metadata: Dict[str, Any], transcript_data: Dict[str, Any], 
                                user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Advanced AI reasoning engine for video-to-action intelligence"""
        
        # Notify shared state system of AI reasoning
        if self.shared_state.is_connected:
            action_id = await self.shared_state.submit_action(
                "ai_reasoning",
                {
                    "video_id": video_metadata.get('video_id'),
                    "title": video_metadata.get('title'),
                    "user_context": user_context
                }
            )
            await self.shared_state.update_status("processing", "Running AI reasoning engine")
        
        user_context = user_context or {}
        skill_level = user_context.get('skill_level', 'intermediate')
        available_time = user_context.get('available_time', '30 minutes')
        goals = user_context.get('goals', ['learn', 'implement'])
        
        video_title = video_metadata.get('title', '')
        transcript_text = transcript_data.get('full_text', '')
        
        # Domain classification with enhanced categories
        domain = self._classify_domain_advanced(video_title, transcript_text)
        
        # Extract actionable insights
        actionable_insights = self._extract_actionable_insights(transcript_text, domain)
        
        # Generate intelligent action recommendations
        action_recommendations = self._generate_action_recommendations(
            actionable_insights, domain, skill_level, available_time, goals
        )
        
        # Create execution roadmap
        execution_roadmap = self._create_execution_roadmap(action_recommendations, available_time)
        
        # Generate adaptive learning path
        learning_path = self._generate_learning_path(domain, skill_level, actionable_insights)
        
        reasoning_result = {
            'success': True,
            'video_analysis': {
                'domain': domain,
                'complexity_score': self._calculate_complexity_score(transcript_text, domain),
                'actionability_score': self._calculate_actionability_score(actionable_insights),
                'learning_value': self._assess_learning_value(video_metadata, transcript_data)
            },
            'user_adaptation': {
                'skill_level': skill_level,
                'time_available': available_time,
                'personalized_goals': goals,
                'difficulty_match': self._assess_difficulty_match(skill_level, domain, transcript_text)
            },
            'actionable_insights': actionable_insights,
            'action_recommendations': action_recommendations,
            'execution_roadmap': execution_roadmap,
            'learning_path': learning_path,
            'next_steps': self._generate_next_steps(action_recommendations, user_context),
            'related_skills': self._identify_related_skills(domain, actionable_insights),
            'success_metrics': self._define_success_metrics(domain, action_recommendations),
            'generated_at': datetime.now().isoformat()
        }
        
        return reasoning_result
    
    def _classify_domain_advanced(self, title: str, transcript: str) -> str:
        """Advanced domain classification with multiple categories"""
        combined_text = f"{title} {transcript}".lower()
        
        domain_keywords = {
            'programming': ['code', 'programming', 'python', 'javascript', 'react', 'api', 'database', 'function', 'variable', 'framework'],
            'cooking': ['recipe', 'ingredients', 'cook', 'bake', 'kitchen', 'food', 'meal', 'chef', 'cuisine'],
            'fitness': ['workout', 'exercise', 'training', 'muscle', 'cardio', 'strength', 'yoga', 'fitness'],
            'business': ['business', 'marketing', 'sales', 'entrepreneur', 'startup', 'revenue', 'customer', 'strategy'],
            'design': ['design', 'creative', 'photoshop', 'illustrator', 'ui', 'ux', 'graphics', 'visual'],
            'music': ['music', 'guitar', 'piano', 'song', 'chord', 'melody', 'instrument', 'audio'],
            'diy': ['diy', 'build', 'tools', 'materials', 'craft', 'handmade', 'project', 'construction'],
            'education': ['learn', 'education', 'explain', 'understand', 'concept', 'theory', 'study', 'academic'],
            'lifestyle': ['lifestyle', 'productivity', 'organization', 'habits', 'wellness', 'self-improvement'],
            'technology': ['tech', 'software', 'hardware', 'AI', 'machine learning', 'data', 'cloud', 'automation']
        }
        
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            domain_scores[domain] = score
        
        return max(domain_scores, key=domain_scores.get) if domain_scores else 'general'
    
    def _extract_actionable_insights(self, transcript: str, domain: str) -> List[Dict[str, Any]]:
        """Extract actionable insights from transcript"""
        sentences = re.split(r'[.!?]+', transcript)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
        
        action_indicators = {
            'programming': ['implement', 'create', 'build', 'write code', 'install', 'configure', 'deploy'],
            'cooking': ['add', 'mix', 'cook', 'bake', 'prepare', 'serve', 'season'],
            'fitness': ['perform', 'repeat', 'hold', 'lift', 'run', 'stretch', 'breathe'],
            'business': ['analyze', 'create strategy', 'implement', 'measure', 'optimize', 'launch'],
            'design': ['create', 'design', 'sketch', 'prototype', 'iterate', 'test'],
            'general': ['start', 'begin', 'first', 'next', 'then', 'finally', 'remember', 'important']
        }
        
        indicators = action_indicators.get(domain, action_indicators['general'])
        
        insights = []
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in indicators):
                insights.append({
                    'text': sentence,
                    'type': 'actionable_step',
                    'confidence': 0.8,
                    'position': i,
                    'estimated_time': self._estimate_step_time(sentence, domain),
                    'difficulty': self._estimate_step_difficulty(sentence, domain)
                })
        
        return insights[:15]  # Limit to top 15 insights
    
    def _generate_action_recommendations(self, insights: List[Dict], domain: str, 
                                       skill_level: str, available_time: str, goals: List[str]) -> List[Dict[str, Any]]:
        """Generate intelligent action recommendations"""
        recommendations = []
        
        # Priority 1: Quick wins (high impact, low effort)
        quick_wins = [insight for insight in insights if 
                     insight.get('difficulty') in ['easy', 'medium'] and 
                     insight.get('estimated_time', 0) <= 10]
        
        if quick_wins:
            recommendations.append({
                'priority': 1,
                'category': 'Quick Wins',
                'description': 'High-impact actions you can complete quickly',
                'actions': quick_wins[:3],
                'estimated_time': f"{sum(action.get('estimated_time', 5) for action in quick_wins[:3])} minutes",
                'success_probability': 0.9
            })
        
        # Priority 2: Core implementation
        core_actions = [insight for insight in insights if 
                       insight.get('difficulty') == 'medium' and 
                       'implement' in insight.get('text', '').lower()]
        
        if core_actions:
            recommendations.append({
                'priority': 2,
                'category': 'Core Implementation',
                'description': 'Essential implementation steps for the main functionality',
                'actions': core_actions[:4],
                'estimated_time': f"{sum(action.get('estimated_time', 15) for action in core_actions[:4])} minutes",
                'success_probability': 0.7
            })
        
        # Priority 3: Advanced features
        advanced_actions = [insight for insight in insights if 
                          insight.get('difficulty') == 'hard' or 
                          'advanced' in insight.get('text', '').lower()]
        
        if advanced_actions:
            recommendations.append({
                'priority': 3,
                'category': 'Advanced Features',
                'description': 'Advanced features and optimizations',
                'actions': advanced_actions[:3],
                'estimated_time': f"{sum(action.get('estimated_time', 25) for action in advanced_actions[:3])} minutes",
                'success_probability': 0.5
            })
        
        return recommendations
    
    def _create_execution_roadmap(self, recommendations: List[Dict], available_time: str) -> Dict[str, Any]:
        """Create a phased execution roadmap"""
        time_minutes = self._parse_time_to_minutes(available_time)
        
        phases = []
        total_time_used = 0
        
        for rec in recommendations:
            rec_time = self._parse_time_to_minutes(rec.get('estimated_time', '15 minutes'))
            
            if total_time_used + rec_time <= time_minutes:
                phases.append({
                    'phase': f"Phase {len(phases) + 1}",
                    'title': rec['category'],
                    'description': rec['description'],
                    'actions': rec['actions'],
                    'estimated_time': rec['estimated_time'],
                    'success_probability': rec['success_probability']
                })
                total_time_used += rec_time
            else:
                # Split the recommendation if it partially fits
                remaining_time = time_minutes - total_time_used
                if remaining_time > 10:  # At least 10 minutes remaining
                    partial_actions = []
                    partial_time = 0
                    
                    for action in rec['actions']:
                        action_time = action.get('estimated_time', 10)
                        if partial_time + action_time <= remaining_time:
                            partial_actions.append(action)
                            partial_time += action_time
                    
                    if partial_actions:
                        phases.append({
                            'phase': f"Phase {len(phases) + 1}",
                            'title': f"{rec['category']} (Partial)",
                            'description': f"Initial steps from {rec['description'].lower()}",
                            'actions': partial_actions,
                            'estimated_time': f"{partial_time} minutes",
                            'success_probability': rec['success_probability'] * 0.8
                        })
                break
        
        return {
            'total_phases': len(phases),
            'phases': phases,
            'total_estimated_time': f"{total_time_used} minutes",
            'time_utilization': f"{(total_time_used / time_minutes) * 100:.1f}%" if time_minutes > 0 else "N/A",
            'feasibility_score': min(1.0, total_time_used / max(time_minutes, 1))
        }
    
    def _generate_learning_path(self, domain: str, skill_level: str, insights: List[Dict]) -> Dict[str, Any]:
        """Generate adaptive learning path"""
        learning_objectives = {
            'programming': ['Understand syntax', 'Write functions', 'Handle data', 'Build projects', 'Debug code'],
            'cooking': ['Prep ingredients', 'Master techniques', 'Timing coordination', 'Flavor balancing', 'Presentation'],
            'fitness': ['Form basics', 'Build endurance', 'Increase strength', 'Prevent injury', 'Track progress'],
            'business': ['Market analysis', 'Strategy development', 'Implementation', 'Metrics tracking', 'Optimization'],
            'general': ['Understand concepts', 'Practice basics', 'Build confidence', 'Apply knowledge', 'Master skills']
        }
        
        objectives = learning_objectives.get(domain, learning_objectives['general'])
        
        # Adjust based on skill level
        if skill_level == 'beginner':
            focus_objectives = objectives[:3]
        elif skill_level == 'advanced':
            focus_objectives = objectives[2:]
        else:  # intermediate
            focus_objectives = objectives[1:4]
        
        return {
            'current_level': skill_level,
            'domain': domain,
            'learning_objectives': focus_objectives,
            'recommended_progression': [
                {'step': i+1, 'objective': obj, 'estimated_time': '1-2 weeks'} 
                for i, obj in enumerate(focus_objectives)
            ],
            'skill_prerequisites': self._identify_prerequisites(domain, skill_level),
            'next_level_skills': self._identify_next_level_skills(domain, skill_level)
        }
    
    def _generate_next_steps(self, recommendations: List[Dict], user_context: Dict) -> List[str]:
        """Generate concrete next steps"""
        next_steps = [
            "Review the video content and identify key concepts",
            "Set up your development/work environment",
            "Start with Priority 1 (Quick Wins) actions"
        ]
        
        if recommendations:
            first_rec = recommendations[0]
            if first_rec.get('actions'):
                first_action = first_rec['actions'][0]
                next_steps.append(f"Begin with: {first_action.get('text', '')[:100]}...")
        
        next_steps.extend([
            "Track your progress and take notes",
            "Test your implementation as you go",
            "Ask for help if you get stuck",
            "Share your results and get feedback"
        ])
        
        return next_steps
    
    def _calculate_complexity_score(self, transcript: str, domain: str) -> float:
        """Calculate content complexity score"""
        words = transcript.split()
        
        # Technical term density
        technical_terms = {
            'programming': ['algorithm', 'function', 'variable', 'object', 'class', 'method', 'API'],
            'cooking': ['technique', 'temperature', 'timing', 'consistency', 'seasoning'],
            'general': ['process', 'method', 'technique', 'procedure', 'system']
        }
        
        terms = technical_terms.get(domain, technical_terms['general'])
        technical_density = sum(1 for word in words if word.lower() in terms) / max(len(words), 1)
        
        # Sentence complexity
        sentences = re.split(r'[.!?]+', transcript)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        complexity = min(1.0, (technical_density * 2 + avg_sentence_length / 20) / 3)
        return complexity
    
    def _calculate_actionability_score(self, insights: List[Dict]) -> float:
        """Calculate how actionable the content is"""
        if not insights:
            return 0.0
        
        actionable_count = len([i for i in insights if i.get('type') == 'actionable_step'])
        total_insights = len(insights)
        
        return min(1.0, actionable_count / max(total_insights, 1))
    
    def _assess_learning_value(self, metadata: Dict, transcript_data: Dict) -> Dict[str, Any]:
        """Assess the learning value of the video"""
        return {
            'content_depth': min(1.0, transcript_data.get('word_count', 0) / 1000),
            'engagement_score': min(1.0, metadata.get('like_count', 0) / max(metadata.get('view_count', 1), 1)),
            'recency_score': self._calculate_recency_score(metadata.get('published_at', '')),
            'channel_authority': self._assess_channel_authority(metadata.get('channel_title', ''))
        }
    
    # Helper methods for utility calculations
    def _estimate_step_time(self, step_text: str, domain: str) -> int:
        """Estimate time required for a step"""
        base_times = {
            'programming': 15,
            'cooking': 10,
            'fitness': 5,
            'business': 20,
            'general': 10
        }
        
        base_time = base_times.get(domain, 10)
        
        # Adjust based on step complexity indicators
        if any(word in step_text.lower() for word in ['setup', 'install', 'configure']):
            return base_time + 10
        elif any(word in step_text.lower() for word in ['quick', 'simple', 'easy']):
            return max(5, base_time - 5)
        
        return base_time
    
    def _estimate_step_difficulty(self, step_text: str, domain: str) -> str:
        """Estimate difficulty level of a step"""
        step_lower = step_text.lower()
        
        if any(word in step_lower for word in ['advanced', 'complex', 'difficult', 'expert']):
            return 'hard'
        elif any(word in step_lower for word in ['basic', 'simple', 'easy', 'quick']):
            return 'easy'
        else:
            return 'medium'
    
    def _parse_time_to_minutes(self, time_str: str) -> int:
        """Parse time string to minutes"""
        time_str = time_str.lower()
        
        if 'hour' in time_str:
            hours = re.findall(r'(\d+)', time_str)
            return int(hours[0]) * 60 if hours else 60
        elif 'minute' in time_str:
            minutes = re.findall(r'(\d+)', time_str)
            return int(minutes[0]) if minutes else 30
        else:
            return 30  # Default
    
    def _assess_difficulty_match(self, skill_level: str, domain: str, transcript: str) -> str:
        """Assess if content difficulty matches user skill level"""
        complexity = self._calculate_complexity_score(transcript, domain)
        
        skill_thresholds = {
            'beginner': (0.0, 0.4),
            'intermediate': (0.3, 0.7),
            'advanced': (0.6, 1.0)
        }
        
        min_thresh, max_thresh = skill_thresholds.get(skill_level, (0.3, 0.7))
        
        if min_thresh <= complexity <= max_thresh:
            return 'perfect_match'
        elif complexity < min_thresh:
            return 'too_easy'
        else:
            return 'too_difficult'
    
    def _identify_prerequisites(self, domain: str, skill_level: str) -> List[str]:
        """Identify skill prerequisites"""
        prerequisites = {
            'programming': {
                'beginner': ['Basic computer skills', 'Text editor usage'],
                'intermediate': ['Programming fundamentals', 'Basic syntax knowledge'],
                'advanced': ['Multiple languages', 'System architecture understanding']
            },
            'general': {
                'beginner': ['Basic understanding of topic'],
                'intermediate': ['Some experience in area'],
                'advanced': ['Extensive background knowledge']
            }
        }
        
        return prerequisites.get(domain, prerequisites['general']).get(skill_level, [])
    
    def _identify_next_level_skills(self, domain: str, skill_level: str) -> List[str]:
        """Identify next level skills to develop"""
        next_skills = {
            'programming': {
                'beginner': ['Functions and methods', 'Data structures', 'Error handling'],
                'intermediate': ['Design patterns', 'Testing', 'Performance optimization'],
                'advanced': ['Architecture design', 'Team leadership', 'Technology strategy']
            },
            'general': {
                'beginner': ['Intermediate concepts', 'Practical application'],
                'intermediate': ['Advanced techniques', 'Teaching others'],
                'advanced': ['Innovation', 'Leadership', 'Mastery']
            }
        }
        
        return next_skills.get(domain, next_skills['general']).get(skill_level, [])
    
    def _identify_related_skills(self, domain: str, insights: List[Dict]) -> List[str]:
        """Identify related skills that would be beneficial"""
        related_skills = {
            'programming': ['Version control', 'Testing', 'Documentation', 'Debugging', 'Code review'],
            'cooking': ['Knife skills', 'Food safety', 'Menu planning', 'Cost management'],
            'fitness': ['Nutrition', 'Recovery techniques', 'Goal setting', 'Progress tracking'],
            'business': ['Data analysis', 'Communication', 'Project management', 'Leadership'],
            'general': ['Problem solving', 'Critical thinking', 'Communication', 'Time management']
        }
        
        return related_skills.get(domain, related_skills['general'])
    
    def _define_success_metrics(self, domain: str, recommendations: List[Dict]) -> List[Dict[str, str]]:
        """Define success metrics for the learning/implementation"""
        base_metrics = [
            {'metric': 'Completion Rate', 'target': '80% of planned actions completed'},
            {'metric': 'Understanding Level', 'target': 'Can explain key concepts clearly'},
            {'metric': 'Practical Application', 'target': 'Successfully implement main functionality'}
        ]
        
        domain_specific = {
            'programming': [
                {'metric': 'Code Quality', 'target': 'Code runs without errors'},
                {'metric': 'Best Practices', 'target': 'Follows coding conventions'}
            ],
            'cooking': [
                {'metric': 'Taste Quality', 'target': 'Dish tastes as expected'},
                {'metric': 'Presentation', 'target': 'Visually appealing result'}
            ],
            'fitness': [
                {'metric': 'Form Quality', 'target': 'Proper exercise form maintained'},
                {'metric': 'Progress Tracking', 'target': 'Baseline measurements recorded'}
            ]
        }
        
        return base_metrics + domain_specific.get(domain, [])
    
    def _calculate_recency_score(self, published_date: str) -> float:
        """Calculate recency score based on publication date"""
        try:
            pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            days_old = (datetime.now() - pub_date.replace(tzinfo=None)).days
            
            # Exponential decay: newer is better
            return max(0.1, 1.0 * (0.95 ** (days_old / 30)))
        except:
            return 0.5  # Default for parsing errors
    
    def _assess_channel_authority(self, channel_title: str) -> float:
        """Assess channel authority (simplified heuristic)"""
        authority_indicators = [
            'official', 'academy', 'university', 'institute', 'expert',
            'professional', 'certified', 'master', 'guru', 'pro'
        ]
        
        channel_lower = channel_title.lower()
        authority_count = sum(1 for indicator in authority_indicators if indicator in channel_lower)
        
        return min(1.0, authority_count * 0.3 + 0.4)  # Base score of 0.4

# Initialize the enhanced MCP server
server = Server("youtube-uvai-processor")
processor = EnhancedYouTubeProcessor()

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all enhanced UVAI MCP tools"""
    return [
        Tool(
            name="extract_video_id",
            description="Extract YouTube video ID from URL or validate existing ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "url_or_id": {"type": "string", "description": "YouTube URL or video ID"}
                },
                "required": ["url_or_id"]
            }
        ),
        Tool(
            name="get_video_metadata",
            description="Retrieve comprehensive metadata for a YouTube video with caching",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {"type": "string", "description": "YouTube video ID"}
                },
                "required": ["video_id"]
            }
        ),
        Tool(
            name="get_video_transcript",
            description="Get video transcript with caching and fallback options",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {"type": "string", "description": "YouTube video ID"},
                    "languages": {"type": "array", "items": {"type": "string"}, "description": "Preferred languages"}
                },
                "required": ["video_id"]
            }
        ),
        Tool(
            name="ai_reasoning_engine",
            description="🧠 Advanced AI reasoning engine for video-to-action intelligence with user context adaptation",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_metadata": {"type": "object", "description": "Video metadata from get_video_metadata"},
                    "transcript_data": {"type": "object", "description": "Transcript data from get_video_transcript"},
                    "user_context": {
                        "type": "object",
                        "properties": {
                            "skill_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
                            "available_time": {"type": "string", "description": "Available time (e.g., '30 minutes', '2 hours')"},
                            "goals": {"type": "array", "items": {"type": "string"}, "description": "Learning/implementation goals"}
                        }
                    }
                },
                "required": ["video_metadata", "transcript_data"]
            }
        ),
        Tool(
            name="process_video_complete_uvai",
            description="Complete UVAI processing pipeline with AI reasoning and shared state integration",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_url": {"type": "string", "description": "YouTube video URL"},
                    "user_context": {
                        "type": "object",
                        "properties": {
                            "skill_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
                            "available_time": {"type": "string"},
                            "goals": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "languages": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["video_url"]
            }
        ),
        Tool(
            name="get_shared_state_status",
            description="Get status of all connected MCP servers in the ecosystem",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="coordinate_with_servers",
            description="Coordinate video processing task with other MCP servers",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "description": "Type of coordination task"},
                    "video_id": {"type": "string", "description": "Video ID for processing"},
                    "required_capabilities": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["task_type", "video_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls with shared state integration"""
    try:
        if name == "extract_video_id":
            url_or_id = arguments["url_or_id"]
            video_id = processor.extract_video_id(url_or_id)
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({
                    "success": True, "video_id": video_id, "input": url_or_id
                }, indent=2))]
            )
        
        elif name == "get_video_metadata":
            video_id = arguments["video_id"]
            metadata = await processor.get_video_metadata(video_id)
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({
                    "success": True, "metadata": metadata
                }, indent=2))]
            )
        
        elif name == "get_video_transcript":
            video_id = arguments["video_id"]
            languages = arguments.get("languages")
            transcript_data = await processor.get_video_transcript(video_id, languages)
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({
                    "success": True, "transcript_data": transcript_data
                }, indent=2))]
            )
        
        elif name == "ai_reasoning_engine":
            video_metadata = arguments["video_metadata"]
            transcript_data = arguments["transcript_data"]
            user_context = arguments.get("user_context", {})
            
            reasoning_result = await processor.ai_reasoning_engine(
                video_metadata, transcript_data, user_context
            )
            
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({
                    "success": True, "ai_reasoning": reasoning_result
                }, indent=2))]
            )
        
        elif name == "process_video_complete_uvai":
            video_url = arguments["video_url"]
            user_context = arguments.get("user_context", {})
            languages = arguments.get("languages")
            
            # Complete UVAI processing pipeline
            try:
                # Step 1: Extract video ID
                video_id = processor.extract_video_id(video_url)
                
                # Step 2: Get metadata
                metadata = await processor.get_video_metadata(video_id)
                
                # Step 3: Get transcript
                transcript_data = await processor.get_video_transcript(video_id, languages)
                
                # Step 4: AI Reasoning Engine
                ai_reasoning = await processor.ai_reasoning_engine(metadata, transcript_data, user_context)
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "success": True,
                        "video_id": video_id,
                        "metadata": metadata,
                        "transcript_data": transcript_data,
                        "ai_reasoning": ai_reasoning,
                        "processing_timestamp": datetime.now().isoformat(),
                        "processor_version": "UVAI Enhanced v1.0"
                    }, indent=2))]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "success": False, "error": str(e), "error_type": type(e).__name__
                    }, indent=2))]
                )
        
        elif name == "get_shared_state_status":
            if processor.shared_state.is_connected:
                servers = await processor.shared_state.get_available_servers()
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "success": True,
                        "coordinator_connected": True,
                        "available_servers": servers,
                        "this_server_id": processor.shared_state.server_id
                    }, indent=2))]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "success": True,
                        "coordinator_connected": False,
                        "message": "Running in standalone mode"
                    }, indent=2))]
                )
        
        elif name == "coordinate_with_servers":
            task_type = arguments["task_type"]
            video_id = arguments["video_id"]
            required_capabilities = arguments.get("required_capabilities", [])
            
            if processor.shared_state.is_connected:
                action_id = await processor.shared_state.submit_action(
                    task_type,
                    {"video_id": video_id, "required_capabilities": required_capabilities}
                )
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "success": True,
                        "action_submitted": True,
                        "action_id": action_id,
                        "task_type": task_type
                    }, indent=2))]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "success": False,
                        "error": "Shared state coordinator not connected"
                    }, indent=2))]
                )
        
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({
                    "success": False, "error": f"Unknown tool: {name}"
                }, indent=2))]
            )
    
    except Exception as e:
        logger.error(f"Error in tool call {name}: {e}")
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps({
                "success": False, "error": str(e), "error_type": type(e).__name__
            }, indent=2))]
        )

async def main():
    """Main entry point for the enhanced UVAI MCP server"""
    logger.info("Starting Enhanced YouTube UVAI MCP Server")
    
    # Connect to shared state coordinator (optional)
    try:
        await processor.connect_to_coordinator()
    except Exception as e:
        logger.warning(f"Could not connect to state coordinator, continuing without it: {e}")
    
    # Check dependencies
    if not HAS_VIDEO_DEPS:
        logger.warning("Video processing dependencies missing. Install with: pip install youtube-transcript-api google-api-python-client yt-dlp")
    
    if not HAS_AI_DEPS:
        logger.warning("AI dependencies missing. Install with: pip install openai transformers torch")
    
    # Check environment variables
    required_env_vars = ['YOUTUBE_API_KEY']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
    
    # Start the server
    async with stdio_server() as streams:
        await server.run(
            streams[0], streams[1], InitializationOptions(
                server_name="youtube-uvai-processor",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)