#!/usr/bin/env python3
"""
Real API Testing Script - YouTube Extension Project
Tests multiple YouTube videos with actual API keys to measure costs and performance.
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional

class YouTubeAPITester:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.results = []
        
    def test_video(self, video_id: str) -> Dict:
        """Test a single YouTube video and collect metrics."""
        start_time = time.time()
        
        try:
            # Get video metadata
            url = f"{self.base_url}/videos"
            params = {
                'part': 'snippet,statistics,contentDetails',
                'id': video_id,
                'key': self.api_key
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            processing_time = time.time() - start_time
            
            if not data.get('items'):
                return {
                    'video_id': video_id,
                    'status': 'error',
                    'error': 'Video not found',
                    'processing_time': processing_time
                }
            
            video_data = data['items'][0]
            
            # Extract duration and convert to minutes
            duration_str = video_data['contentDetails']['duration']
            duration_minutes = self._parse_duration(duration_str)
            
            # Calculate estimated costs
            estimated_costs = self._calculate_costs(duration_minutes)
            
            result = {
                'video_id': video_id,
                'status': 'success',
                'processing_time': processing_time,
                'metadata': {
                    'title': video_data['snippet']['title'],
                    'channel': video_data['snippet']['channelTitle'],
                    'duration': duration_str,
                    'duration_minutes': duration_minutes,
                    'view_count': int(video_data['statistics'].get('viewCount', 0)),
                    'like_count': int(video_data['statistics'].get('likeCount', 0)),
                    'published_at': video_data['snippet']['publishedAt'],
                    'description_length': len(video_data['snippet']['description']),
                    'tags_count': len(video_data['snippet'].get('tags', []))
                },
                'costs': estimated_costs,
                'business_metrics': self._calculate_business_value(duration_minutes, video_data)
            }
            
            return result
            
        except Exception as e:
            return {
                'video_id': video_id,
                'status': 'error',
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _parse_duration(self, duration_str: str) -> float:
        """Parse YouTube duration format (PT1H20M4S) to minutes."""
        import re
        
        # Remove PT prefix
        duration_str = duration_str[2:]
        
        # Extract hours, minutes, seconds
        hours = 0
        minutes = 0
        seconds = 0
        
        if 'H' in duration_str:
            hours = int(re.search(r'(\d+)H', duration_str).group(1))
        if 'M' in duration_str:
            minutes = int(re.search(r'(\d+)M', duration_str).group(1))
        if 'S' in duration_str:
            seconds = int(re.search(r'(\d+)S', duration_str).group(1))
        
        return hours * 60 + minutes + seconds / 60
    
    def _calculate_costs(self, duration_minutes: float) -> Dict:
        """Calculate estimated processing costs."""
        # YouTube API: Free (within quotas)
        youtube_cost = 0.0
        
        # Whisper transcription: $0.006 per minute
        whisper_cost = duration_minutes * 0.006
        
        # GPT-4 analysis: Estimated based on content length
        # Assume ~500 tokens per minute of content
        estimated_tokens = int(duration_minutes * 500)
        gpt4_cost = estimated_tokens * 0.00003  # $0.03 per 1K tokens
        
        total_cost = youtube_cost + whisper_cost + gpt4_cost
        
        return {
            'youtube_api': youtube_cost,
            'whisper_transcription': round(whisper_cost, 4),
            'gpt4_analysis': round(gpt4_cost, 4),
            'total_estimated': round(total_cost, 4)
        }
    
    def _calculate_business_value(self, duration_minutes: float, video_data: Dict) -> Dict:
        """Calculate business value metrics."""
        # Estimate manual analysis time (3-5x video duration)
        manual_analysis_hours = duration_minutes / 60 * 4
        
        # Estimate AI processing time (5-10 minutes regardless of video length)
        ai_processing_minutes = 7
        
        # Time savings
        time_saved_hours = manual_analysis_hours - (ai_processing_minutes / 60)
        
        # Value calculations
        view_count = video_data['statistics'].get('viewCount', 0)
        like_count = video_data['statistics'].get('likeCount', 0)
        
        # Engagement rate
        engagement_rate = (int(like_count) / int(view_count)) * 100 if view_count else 0
        
        return {
            'manual_analysis_hours': round(manual_analysis_hours, 2),
            'ai_processing_minutes': ai_processing_minutes,
            'time_saved_hours': round(time_saved_hours, 2),
            'efficiency_gain_percent': round((time_saved_hours / manual_analysis_hours) * 100, 1),
            'engagement_rate': round(engagement_rate, 4),
            'content_quality_score': self._calculate_quality_score(video_data)
        }
    
    def _calculate_quality_score(self, video_data: Dict) -> float:
        """Calculate content quality score based on engagement and metadata."""
        view_count = int(video_data['statistics'].get('viewCount', 0))
        like_count = int(video_data['statistics'].get('likeCount', 0))
        
        # Normalize metrics
        view_score = min(view_count / 1000000, 10)  # Max 10 for 1M+ views
        like_score = min(like_count / 10000, 10)   # Max 10 for 10K+ likes
        
        # Description quality
        desc_length = len(video_data['snippet']['description'])
        desc_score = min(desc_length / 1000, 5)    # Max 5 for 1K+ char description
        
        # Tags quality
        tags_count = len(video_data['snippet'].get('tags', []))
        tags_score = min(tags_count / 10, 5)       # Max 5 for 10+ tags
        
        total_score = (view_score + like_score + desc_score + tags_score) / 4
        return round(total_score, 2)

def main():
    """Main testing function."""
    # Test videos of different lengths and topics
    test_videos = [
        {
            'id': 'SqcY0GlETPk',
            'name': 'React Tutorial for Beginners',
            'expected_length': '80 minutes',
            'topic': 'Technical Tutorial'
        },
        {
            'id': 'aircAruvnKk',
            'name': 'What is a Neural Network?',
            'expected_length': '19 minutes',
            'topic': 'AI/ML Education'
        },
        {
            'id': 'fgTGADljAeg',
            'name': 'Full Stack Web Development',
            'expected_length': '45 minutes',
            'topic': 'Programming Course'
        },
        {
            'id': 'BPK_qzeH_yk',
            'name': 'Growth Hacking Strategies',
            'expected_length': '15 minutes',
            'topic': 'Business/Marketing'
        },
        {
            'id': 'c9Wg6Cb_YlU',
            'name': 'UI/UX Design Principles',
            'expected_length': '25 minutes',
            'topic': 'Design Tutorial'
        }
    ]
    
    # Get API key from environment
    api_key = os.getenv('REACT_APP_YOUTUBE_API_KEY')
    if not api_key:
        print("❌ Error: REACT_APP_YOUTUBE_API_KEY environment variable not set")
        return
    
    print("🚀 Starting Real API Testing...")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 API Key: {api_key[:20]}...")
    print()
    
    tester = YouTubeAPITester(api_key)
    results = []
    
    for i, video in enumerate(test_videos, 1):
        print(f"🎬 Testing Video {i}/5: {video['name']}")
        print(f"   Expected: {video['expected_length']} - {video['topic']}")
        
        result = tester.test_video(video['id'])
        result['test_info'] = video
        results.append(result)
        
        if result['status'] == 'success':
            print(f"   ✅ Success: {result['metadata']['duration_minutes']:.1f} min")
            print(f"   💰 Estimated Cost: ${result['costs']['total_estimated']:.4f}")
            print(f"   ⏱️  Processing Time: {result['processing_time']:.2f}s")
            print(f"   📊 Quality Score: {result['business_metrics']['content_quality_score']}/10")
        else:
            print(f"   ❌ Error: {result['error']}")
        print()
    
    # Generate summary report
    print("📋 TESTING SUMMARY")
    print("=" * 50)
    
    successful_tests = [r for r in results if r['status'] == 'success']
    failed_tests = [r for r in results if r['status'] == 'error']
    
    print(f"✅ Successful Tests: {len(successful_tests)}/{len(results)}")
    print(f"❌ Failed Tests: {len(failed_tests)}")
    
    if successful_tests:
        total_duration = sum(r['metadata']['duration_minutes'] for r in successful_tests)
        total_cost = sum(r['costs']['total_estimated'] for r in successful_tests)
        avg_processing_time = sum(r['processing_time'] for r in successful_tests) / len(successful_tests)
        
        print(f"\n💰 COST ANALYSIS:")
        print(f"   Total Video Duration: {total_duration:.1f} minutes")
        print(f"   Total Estimated Cost: ${total_cost:.4f}")
        print(f"   Average Cost per Minute: ${total_cost/total_duration:.4f}")
        print(f"   Average Processing Time: {avg_processing_time:.2f}s")
        
        print(f"\n📊 BUSINESS VALUE:")
        total_time_saved = sum(r['business_metrics']['time_saved_hours'] for r in successful_tests)
        avg_efficiency = sum(r['business_metrics']['efficiency_gain_percent'] for r in successful_tests) / len(successful_tests)
        
        print(f"   Total Time Saved: {total_time_saved:.1f} hours")
        print(f"   Average Efficiency Gain: {avg_efficiency:.1f}%")
        print(f"   ROI at $25/hour: ${(total_time_saved * 25) - total_cost:.2f}")
        print(f"   ROI at $50/hour: ${(total_time_saved * 50) - total_cost:.2f}")
    
    # Save detailed results
    output_file = f"real_api_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: {output_file}")
    print("\n🎯 NEXT STEPS:")
    print("1. Add OpenAI API key to test complete pipeline")
    print("2. Process actual video content with AI analysis")
    print("3. Measure real user value with implementation guides")
    print("4. Deploy to production with usage analytics")

if __name__ == "__main__":
    main() 