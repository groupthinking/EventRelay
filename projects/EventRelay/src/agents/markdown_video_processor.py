"""
Markdown-First Video Processor
Generates human-readable markdown analysis instead of JSON
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import aiohttp
import ssl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class MarkdownVideoProcessor:
    """Process YouTube videos and generate markdown-formatted analysis"""
    
    def __init__(self):
        # Load API keys
        self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Load prompt template
        prompt_path = Path(__file__).parent.parent / 'prompts' / 'video_analysis_markdown.txt'
        with open(prompt_path, 'r') as f:
            self.prompt_template = f.read()
    
    async def get_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """Fetch comprehensive video metadata via MCP proxy with fallback"""
        # Try MCP proxy first for enhanced data
        try:
            from mcp_servers.youtube_api_proxy import create_youtube_proxy
            proxy = create_youtube_proxy(self.youtube_api_key)
            
            # Get enriched metadata via proxy
            video_info = await proxy.get_video_info(video_id)
            video = video_info
            
            # Get transcript if available
            transcript_data = []
            try:
                transcript_data = await proxy.get_transcript(video_id)
            except Exception as e:
                logger.warning(f"Transcript not available: {e}")
            
        except Exception as e:
            logger.warning(f"MCP proxy failed, using direct API: {e}")
            # Fallback to direct API
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
                    transcript_data = []
        
        # Parse duration from ISO 8601
        duration = video['contentDetails']['duration']
        duration_readable = self._parse_duration(duration)
        
        # Extract transcript summary if available
        transcript_summary = ""
        if transcript_data:
            # Take first few transcript segments for context
            first_segments = transcript_data[:5]
            transcript_summary = " ".join([seg.get('text', '') for seg in first_segments])
            transcript_summary = transcript_summary[:300] + "..." if len(transcript_summary) > 300 else transcript_summary
        
        return {
            'video_id': video_id,
            'title': video['snippet']['title'],
            'channel': video['snippet']['channelTitle'],
            'description': video['snippet']['description'][:500] + '...',
            'published_at': video['snippet']['publishedAt'],
            'duration': duration_readable,
            'view_count': int(video['statistics'].get('viewCount', 0)),
            'like_count': int(video['statistics'].get('likeCount', 0)),
            'comment_count': int(video['statistics'].get('commentCount', 0)),
            'thumbnail': video['snippet']['thumbnails']['high']['url'],
            'tags': video['snippet'].get('tags', [])[:5],
            'category_id': video['snippet']['categoryId'],
            'transcript_preview': transcript_summary,
            'has_transcript': len(transcript_data) > 0,
            'transcript_segments': len(transcript_data)
        }
    
    def _parse_duration(self, duration: str) -> str:
        """Convert ISO 8601 duration to readable format"""
        # Simple parser for PT12M34S format
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
    
    async def get_video_comments(self, video_id: str, max_results: int = 20) -> list:
        """Fetch top comments from video"""
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {
            'part': 'snippet',
            'videoId': video_id,
            'key': self.youtube_api_key,
            'maxResults': max_results,
            'order': 'relevance'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    comments = []
                    for item in data.get('items', []):
                        comment = item['snippet']['topLevelComment']['snippet']
                        comments.append({
                            'text': comment['textDisplay'][:200],
                            'likes': comment['likeCount'],
                            'author': comment['authorDisplayName']
                        })
                    return comments
        except Exception as e:
            logger.warning(f"Failed to fetch comments: {e}")
            return []
    
    async def generate_markdown_analysis(self, metadata: Dict[str, Any]) -> str:
        """Generate markdown analysis using AI"""
        # Prepare the prompt
        prompt = self.prompt_template.replace('{{VIDEO_URL}}', f"https://www.youtube.com/watch?v={metadata['video_id']}")
        prompt = prompt.replace('{{VIDEO_METADATA}}', json.dumps(metadata, indent=2))
        
        # Use OpenAI for generation
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'gpt-4o',
                'messages': [
                    {'role': 'system', 'content': 'You are an expert at creating educational content from videos.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 2000
            }
            
            async with session.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload
            ) as response:
                result = await response.json()
                
                if 'choices' in result:
                    return result['choices'][0]['message']['content']
                else:
                    raise Exception(f"API error: {result}")
    
    def categorize_video(self, metadata: Dict[str, Any]) -> str:
        """Categorize video based on metadata"""
        # YouTube category mapping (simplified)
        category_map = {
            '27': 'Educational',
            '28': 'Technology',
            '26': 'Tutorial',
            '22': 'Vlog',
            '10': 'Music',
            '19': 'Travel',
            '17': 'Sports',
            '23': 'Comedy',
            '24': 'Entertainment',
            '25': 'News',
            '20': 'Gaming'
        }
        
        category_id = str(metadata.get('category_id', ''))
        base_category = category_map.get(category_id, 'General')
        
        # Enhance with keyword detection
        title = metadata.get('title', '').lower()
        tags = ' '.join(metadata.get('tags', [])).lower()
        combined = f"{title} {tags}"
        
        if any(word in combined for word in ['learn', 'tutorial', 'course', 'how to', 'explained']):
            return 'Educational'
        elif any(word in combined for word in ['code', 'programming', 'software', 'dev']):
            return 'Technology'
        elif any(word in combined for word in ['cook', 'recipe', 'food']):
            return 'Cooking'
        elif any(word in combined for word in ['workout', 'exercise', 'fitness']):
            return 'Fitness'
        
        return base_category
    
    async def process_video(self, video_url: str) -> Dict[str, Any]:
        """Main processing pipeline"""
        # Extract video ID
        video_id = self._extract_video_id(video_url)
        
        # Get enriched metadata
        metadata = await self.get_video_metadata(video_id)
        
        # Get top comments
        comments = await self.get_video_comments(video_id)
        if comments:
            metadata['top_comments'] = [f"{c['text']} — {c['likes']} likes" for c in comments[:3]]
        
        # Categorize
        metadata['category'] = self.categorize_video(metadata)
        
        # Generate markdown analysis
        markdown_content = await self.generate_markdown_analysis(metadata)
        
        # Save results
        save_path = await self._save_markdown_result(video_id, metadata, markdown_content)
        
        return {
            'video_id': video_id,
            'video_url': video_url,
            'metadata': metadata,
            'markdown_analysis': markdown_content,
            'save_path': save_path,
            'processing_time': datetime.now().isoformat(),
            'success': True
        }
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no pattern matches, assume the input is already a video ID
        if len(url) == 11:
            return url
        
        raise ValueError(f"Could not extract video ID from: {url}")
    
    async def _save_markdown_result(self, video_id: str, metadata: Dict[str, Any], markdown: str) -> str:
        """Save the markdown analysis to file"""
        # Create directory structure
        category = metadata.get('category', 'General')
        save_dir = Path('youtube_processed_videos') / 'markdown_analysis' / category
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Save markdown file
        filename = f"{video_id}_analysis.md"
        filepath = save_dir / filename
        
        # Add metadata header to markdown
        full_content = f"""---
video_id: {video_id}
title: {metadata.get('title', 'Unknown')}
channel: {metadata.get('channel', 'Unknown')}
category: {category}
duration: {metadata.get('duration', 'Unknown')}
views: {metadata.get('view_count', 0):,}
processed_at: {datetime.now().isoformat()}
---

# {metadata.get('title', 'Video Analysis')}

{markdown}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # Also save the raw metadata
        json_filepath = save_dir / f"{video_id}_metadata.json"
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved markdown analysis to: {filepath}")
        return str(filepath)


# Example usage
async def test_markdown_processor():
    processor = MarkdownVideoProcessor()
    
    # Test with the neural network video
    result = await processor.process_video("https://www.youtube.com/watch?v=aircAruvnKk")
    
    print(f"✅ Processed video: {result['metadata']['title']}")
    print(f"📁 Saved to: {result['save_path']}")
    print(f"\n📝 Markdown Preview:\n")
    print(result['markdown_analysis'][:500] + "...")


if __name__ == "__main__":
    asyncio.run(test_markdown_processor())
