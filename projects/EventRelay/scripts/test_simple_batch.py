#!/usr/bin/env python3
"""
Simple batch test for YouTube video processing
Tests processing of multiple technical business videos
"""

import json
import time
from datetime import datetime
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi

# Create API instance
api = YouTubeTranscriptApi()

# Technical Business YouTube Video IDs (Updated for accessible videos)
TEST_VIDEO_IDS = [
    "mJeNghZXtMo",  # Transformers Explained
    "gKNmRcXhx-M",  # Machine Learning Fundamentals
    "ZoJPKjLWugg",  # Python for Data Science
    "Gv9_4yMHFhI",  # How to Think Like a Programmer
    "RBSGKlAvoiM",  # Data Structures Easy to Advanced
]

def process_video(video_id):
    """Process a single video"""
    print(f"\n🎯 Processing video: {video_id}")
    start_time = time.time()
    
    try:
        # Get transcript using the new API instance method
        transcript = api.fetch(video_id, languages=['en', 'en-US'])
        
        # Extract key information
        total_text = " ".join([seg['text'] for seg in transcript])
        total_segments = len(transcript)
        duration = transcript[-1]['start'] + transcript[-1]['duration'] if transcript else 0
        
        # Categorize based on content
        text_lower = total_text.lower()
        if any(kw in text_lower for kw in ['tutorial', 'learn', 'course']):
            category = "Educational_Content"
        elif any(kw in text_lower for kw in ['business', 'startup', 'marketing']):
            category = "Business_Professional"
        else:
            category = "Technical_Content"
        
        result = {
            'video_id': video_id,
            'status': 'success',
            'category': category,
            'total_segments': total_segments,
            'duration_seconds': duration,
            'summary': total_text[:200] + '...',
            'processing_time': time.time() - start_time,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save result
        output_dir = Path(f'gdrive_results/{category}')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f'{video_id}_result.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✅ Success: {total_segments} segments, {duration:.0f}s duration")
        print(f"📁 Saved to: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            'video_id': video_id,
            'status': 'failed',
            'error': str(e),
            'processing_time': time.time() - start_time,
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Process test videos"""
    print("🚀 Starting Simple Batch Test")
    print(f"📹 Processing {len(TEST_VIDEO_IDS)} test videos")
    
    results = []
    success_count = 0
    
    for i, video_id in enumerate(TEST_VIDEO_IDS, 1):
        print(f"\n--- Video {i}/{len(TEST_VIDEO_IDS)} ---")
        result = process_video(video_id)
        results.append(result)
        
        if result['status'] == 'success':
            success_count += 1
        
        # Small delay to avoid rate limiting
        time.sleep(2)
    
    # Generate report
    print(f"\n\n📊 FINAL REPORT")
    print(f"Total videos: {len(TEST_VIDEO_IDS)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(TEST_VIDEO_IDS) - success_count}")
    print(f"Success rate: {(success_count/len(TEST_VIDEO_IDS))*100:.1f}%")
    
    # Save report
    report = {
        'test_date': datetime.now().isoformat(),
        'total_videos': len(TEST_VIDEO_IDS),
        'successful': success_count,
        'failed': len(TEST_VIDEO_IDS) - success_count,
        'results': results
    }
    
    with open('simple_batch_test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n📄 Report saved to: simple_batch_test_report.json")

if __name__ == "__main__":
    main()