"""
Interactive Metadata Extractor
Extracts time-coded chapters, transcript, keyframes, and resources from YouTube videos
"""

import os
import re
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import aiohttp
import cv2
import numpy as np
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
import whisper
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class InteractiveMetadataExtractor:
    """Extract comprehensive time-coded metadata for interactive learning"""
    
    def __init__(self):
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.whisper_model = None  # Lazy load
        
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
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
    
    async def extract_chapters(self, video_id: str, description: str) -> List[Dict[str, Any]]:
        """Extract chapters from video description or generate them"""
        chapters = []
        
        # Try to extract from description timestamps
        timestamp_pattern = r'(\d{1,2}:?\d{1,2}:\d{2}|\d{1,2}:\d{2})\s*[-–—]\s*(.+?)(?=\n|$)'
        matches = re.findall(timestamp_pattern, description, re.MULTILINE)
        
        if matches:
            for i, (time_str, title) in enumerate(matches):
                chapters.append({
                    'id': f'ch_{i}',
                    'title': title.strip(),
                    'time': time_str,
                    'timeSeconds': self._time_to_seconds(time_str)
                })
        else:
            # Generate chapters using AI if none found
            chapters = await self._generate_chapters_ai(video_id)
        
        # Calculate durations
        for i in range(len(chapters) - 1):
            duration = chapters[i + 1]['timeSeconds'] - chapters[i]['timeSeconds']
            chapters[i]['duration'] = self._seconds_to_time(duration)
        
        return chapters
    
    async def extract_transcript(self, video_id: str) -> List[Dict[str, Any]]:
        """Extract transcript with timing information"""
        transcript_lines = []
        
        try:
            # Try YouTube's auto-generated captions
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            
            for i, entry in enumerate(transcript):
                transcript_lines.append({
                    'id': f'tr_{i}',
                    'text': entry['text'],
                    'start': entry['start'],
                    'end': entry['start'] + entry['duration'],
                    'speaker': 'narrator'  # Default, could be enhanced
                })
        except Exception as e:
            logger.warning(f"Failed to get YouTube transcript: {e}")
            # Fall back to Whisper or other methods
            transcript_lines = await self._generate_transcript_whisper(video_id)
        
        return transcript_lines
    
    async def extract_keyframes(self, video_id: str, transcript: List[Dict]) -> List[Dict[str, Any]]:
        """Extract visual keyframes from video"""
        keyframes = []
        
        # For now, generate keyframes at chapter boundaries and important moments
        # In production, this would use computer vision to detect scene changes
        
        # Mock implementation - would use actual video processing
        important_times = [0, 60, 120, 180, 240]  # Every minute for demo
        
        for i, time in enumerate(important_times):
            keyframes.append({
                'time': time,
                'image': f'/api/keyframe/{video_id}/{time}',  # Would be actual image URL
                'description': f'Key concept at {self._seconds_to_time(time)}'
            })
        
        return keyframes
    
    async def extract_resources(self, video_id: str, metadata: Dict) -> List[Dict[str, Any]]:
        """Extract or generate relevant resources"""
        resources = []
        
        # Extract links from description
        description = metadata.get('description', '')
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, description)
        
        for i, url in enumerate(urls[:10]):  # Limit to 10 resources
            resource_type = self._classify_resource_url(url)
            resources.append({
                'id': f'res_{i}',
                'type': resource_type,
                'title': f'Resource {i + 1}',  # Would extract actual title
                'url': url,
                'chapters': []  # Would map to relevant chapters
            })
        
        # Add generated resources based on content
        if metadata.get('category') == 'Educational':
            resources.extend([
                {
                    'id': 'res_exercise',
                    'type': 'exercise',
                    'title': 'Practice Exercises',
                    'url': f'/api/exercises/{video_id}',
                    'chapters': []
                },
                {
                    'id': 'res_quiz',
                    'type': 'exercise',
                    'title': 'Interactive Quiz',
                    'url': f'/api/quiz/{video_id}',
                    'chapters': []
                }
            ])
        
        return resources
    
    async def extract_all_metadata(self, video_url: str) -> Dict[str, Any]:
        """Extract all interactive metadata from video"""
        video_id = self.extract_video_id(video_url)
        
        # Get basic metadata
        metadata = await self._get_video_metadata(video_id)
        
        # Extract all components
        chapters = await self.extract_chapters(video_id, metadata.get('description', ''))
        transcript = await self.extract_transcript(video_id)
        keyframes = await self.extract_keyframes(video_id, transcript)
        resources = await self.extract_resources(video_id, metadata)
        
        # Compile complete metadata
        return {
            'video_id': video_id,
            'video_url': video_url,
            'metadata': metadata,
            'chapters': chapters,
            'transcript': transcript,
            'keyframes': keyframes,
            'resources': resources,
            'extracted_at': datetime.now().isoformat()
        }
    
    async def _get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """Get basic video metadata from YouTube API"""
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,contentDetails,statistics',
            'id': video_id,
            'key': self.youtube_api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if not data.get('items'):
                    raise ValueError(f"Video not found: {video_id}")
                
                video = data['items'][0]
                
                return {
                    'title': video['snippet']['title'],
                    'channel': video['snippet']['channelTitle'],
                    'description': video['snippet']['description'],
                    'duration': self._parse_duration(video['contentDetails']['duration']),
                    'category': self._get_category_name(video['snippet']['categoryId'])
                }
    
    async def _generate_chapters_ai(self, video_id: str) -> List[Dict[str, Any]]:
        """Generate chapters using AI analysis"""
        # This would use GPT-4 or similar to analyze transcript and generate chapters
        # Mock implementation for now
        return [
            {
                'id': 'ch_0',
                'title': 'Introduction',
                'time': '0:00',
                'timeSeconds': 0
            },
            {
                'id': 'ch_1',
                'title': 'Main Content',
                'time': '2:00',
                'timeSeconds': 120
            },
            {
                'id': 'ch_2',
                'title': 'Conclusion',
                'time': '8:00',
                'timeSeconds': 480
            }
        ]
    
    async def _generate_transcript_whisper(self, video_id: str) -> List[Dict[str, Any]]:
        """Generate transcript using Whisper"""
        # This would download audio and transcribe with Whisper
        # Mock implementation for now
        return [
            {
                'id': 'tr_0',
                'text': 'Welcome to this tutorial.',
                'start': 0,
                'end': 3,
                'speaker': 'narrator'
            }
        ]
    
    def _time_to_seconds(self, time_str: str) -> int:
        """Convert time string to seconds"""
        parts = time_str.split(':')
        parts = [int(p) for p in parts]
        
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        else:
            return parts[0]
    
    def _seconds_to_time(self, seconds: int) -> str:
        """Convert seconds to time string"""
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        else:
            return f"{m}:{s:02d}"
    
    def _parse_duration(self, duration: str) -> str:
        """Parse ISO 8601 duration to readable format"""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if match:
            hours, minutes, seconds = match.groups()
            parts = []
            if hours:
                parts.append(f"{hours}h")
            if minutes:
                parts.append(f"{minutes}m")
            if seconds:
                parts.append(f"{seconds}s")
            return " ".join(parts) if parts else "0s"
        return duration
    
    def _get_category_name(self, category_id: str) -> str:
        """Map YouTube category ID to name"""
        categories = {
            '27': 'Educational',
            '28': 'Science & Technology',
            '26': 'How-to & Style',
            '22': 'People & Blogs',
            '10': 'Music',
            '24': 'Entertainment',
            '20': 'Gaming',
            '19': 'Travel & Events',
            '17': 'Sports',
            '25': 'News & Politics',
            '23': 'Comedy',
            '15': 'Pets & Animals',
            '1': 'Film & Animation',
            '2': 'Autos & Vehicles'
        }
        return categories.get(category_id, 'General')
    
    def _classify_resource_url(self, url: str) -> str:
        """Classify resource type based on URL"""
        if 'github.com' in url or 'gitlab.com' in url:
            return 'code'
        elif 'docs.' in url or 'documentation' in url or '.pdf' in url:
            return 'document'
        elif 'exercise' in url or 'practice' in url or 'quiz' in url:
            return 'exercise'
        else:
            return 'link'
    
    async def save_metadata(self, metadata: Dict[str, Any]) -> str:
        """Save extracted metadata to file"""
        video_id = metadata['video_id']
        save_dir = Path('youtube_processed_videos/interactive_metadata')
        save_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = save_dir / f"{video_id}_metadata.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved interactive metadata to: {filepath}")
        return str(filepath)


# Example usage
async def test_metadata_extraction():
    extractor = InteractiveMetadataExtractor()
    
    # Test with a sample video
    video_url = "https://www.youtube.com/watch?v=aircAruvnKk"
    
    metadata = await extractor.extract_all_metadata(video_url)
    filepath = await extractor.save_metadata(metadata)
    
    print(f"✅ Extracted metadata for: {metadata['metadata']['title']}")
    print(f"📁 Saved to: {filepath}")
    print(f"📚 Chapters: {len(metadata['chapters'])}")
    print(f"📝 Transcript lines: {len(metadata['transcript'])}")
    print(f"🖼️ Keyframes: {len(metadata['keyframes'])}")
    print(f"📎 Resources: {len(metadata['resources'])}")


if __name__ == "__main__":
    asyncio.run(test_metadata_extraction())
