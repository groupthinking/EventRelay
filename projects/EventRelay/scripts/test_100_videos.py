#!/usr/bin/env python3
"""
Test Script: Process 100 Technical Business YouTube Videos
Tests the working version by consuming 100 technical business videos
with robust error handling and checkpoint state management.
"""

import json
import logging
import os
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import traceback

# Add project root to path

# Import our processors
try:
    from youtube_extension.processors.simple_real_processor import process_video, extract_video_id
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False
    print("⚠️ Warning: simple_real_processor not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_100_videos.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Technical Business YouTube Video IDs (100 videos)
TECHNICAL_BUSINESS_VIDEOS = [
    # AI and Machine Learning for Business
    "t5zQpSjSu9I", "aircAruvnKk", "fOqJJphkZA", "gV0_raKR2UQ", "J4Wdy0Wc_xQ",
    "mJeNghZXtMo", "HgWvYvvXIM", "TjkFGrjkXfc", "7eh4d6r5fNQ", "X2vAabgKEyw",
    
    # Cloud Computing and DevOps
    "dH0yz-Osy54", "OXE2a8dqIAA", "bEpU_7wFKM", "lpk7MkQ5xQI", "7kJysT7gXI",
    "PkZNo7MFNFg", "OqBFXhR5E6Y", "2vMH8lxTvVE", "yIVXjl4SwVo", "JdeyVryaal0",
    
    # Blockchain and Cryptocurrency for Business
    "SSo_EIwHSd4", "hYip_Vuv8J0", "qOVAbKKSH10", "41Ilug_dDcM", "2yJqjTiwpxM",
    "s4g1XFU8Gto", "QAQatPPtUkU", "KXdOoIDcmbM", "SyVMrxYSzUM", "37JxCFVAAHY",
    
    # Data Science and Analytics
    "LHBE6Q9XlzI", "xC-c7E5PK0Y", "ua-CiDNNj30", "7eh4d6r5fNQ", "zg9ASOp5j8",
    "GtQjRJnvV8", "KaTE5lPRbn0", "nfr5j_1BgD8", "5q87K1WaoFI", "Gv9_4yMHFhI",
    
    # Software Development Best Practices
    "rGx1QNdYzvs", "jflA3vXw5Qo", "h00gbp36KWg", "HZOv0qUzo8A", "ub3P8TnFS8M",
    "44E8o-IqWTY", "nFQaZmvCayw", "YB5ELgW7JGQ", "SWYqp7iY_Tc", "WxpCXCIfyAY",
    
    # Tech Entrepreneurship and Startups
    "ZoqgAy3h4OM", "nKIu9yen5nc", "BXgQDlW6jxE", "VECV6r-fQPg", "V7h3kGtqV8",
    "CTBt9NCnqB8", "xPJoq_QVsY4", "jOhm-E2fVGk", "FZLXPC_ug2E", "4K6MhLXhx0M",
    
    # Digital Marketing and Growth Hacking
    "n7IHhwmDCNE", "nU-IIXBWlS4", "5GBT4WJNnG0", "NLXys9vVXm8", "pVfGKMU1d9c",
    "9KhKPKxPeQI", "sZz5MPMdao", "0VGQbKQZ7k8", "vCh-HUACjUA", "JcTkbe0TT-U",
    
    # Cybersecurity and Business
    "inWWhr5tnEA", "wXCD8Kb3K7Q", "z5nc9MDbvkw", "IQV0LnDoBkQ", "hXPmnoGVQW0",
    "infQ1knyPqI", "rdFYLTR9I4", "uPrYPUopgm8", "UsVfElI9nsM", "0GfNGKvtXhM",
    
    # API Development and Integration
    "s7wmiS2mSXY", "GZvSYJDk-us", "mb-QHAqBL1g", "ByGJQzlzxQg", "FLnxgSZ0DG4",
    "cuPVDvPc9SY", "pxfEV6XKdY", "7YcW25PHnAA", "iFMLyMgCUTs", "6_xGKdYA0MM",
    
    # Tech Product Management
    "BdSiBlLafNM", "Unzc7oWbYg", "FRRh5hqzRg", "UvCri1tqIxQ", "502ILHjX9EE",
    "F8_ME4VwTiw", "JK_3nIFGOdE", "BkREIFyCuKY", "n_F1a7UpKqw", "QmOF0crdyRU"
]

class VideoProcessingCheckpoint:
    """Manages checkpoint state for video processing"""
    
    def __init__(self, checkpoint_file: str = "video_processing_checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.state = self.load_checkpoint()
    
    def load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint from file"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        
        return {
            "processed_videos": [],
            "failed_videos": [],
            "last_processed_index": -1,
            "start_time": datetime.now().isoformat(),
            "total_processing_time": 0,
            "results": []
        }
    
    def save_checkpoint(self):
        """Save checkpoint to file"""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def mark_processed(self, video_id: str, result: Dict[str, Any]):
        """Mark a video as processed"""
        self.state["processed_videos"].append(video_id)
        self.state["results"].append({
            "video_id": video_id,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
        self.save_checkpoint()
    
    def mark_failed(self, video_id: str, error: str):
        """Mark a video as failed"""
        self.state["failed_videos"].append({
            "video_id": video_id,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        self.save_checkpoint()
    
    def update_progress(self, index: int):
        """Update processing progress"""
        self.state["last_processed_index"] = index
        self.save_checkpoint()

async def process_video_with_retry(video_id: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
    """Process a video with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Processing video {video_id} (attempt {attempt + 1}/{max_retries})")
            
            # Use the simple real processor
            result = process_video(video_id)
            
            if result and result.get("status") == "success":
                return result
            else:
                logger.warning(f"Video {video_id} processing returned non-success status")
                
        except Exception as e:
            logger.error(f"Error processing video {video_id}: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Exponential backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Failed to process video {video_id} after {max_retries} attempts")
                return None
    
    return None

async def search_youtube_solution(error: str) -> Optional[str]:
    """Search YouTube for solution to the error"""
    try:
        # Simulate searching for solution (would integrate with YouTube API)
        logger.info(f"🔍 Searching YouTube for solution to: {error}")
        
        # For now, return a mock solution
        # In production, this would actually search YouTube
        search_terms = f"fix {error} tutorial"
        logger.info(f"Would search for: {search_terms}")
        
        return f"Suggested fix: Check API quotas and rate limits"
        
    except Exception as e:
        logger.error(f"Failed to search for solution: {e}")
        return None

async def process_batch(videos: List[str], checkpoint: VideoProcessingCheckpoint, start_index: int = 0):
    """Process a batch of videos with checkpoint management"""
    
    success_count = 0
    failure_count = 0
    
    for i, video_id in enumerate(videos[start_index:], start=start_index):
        # Check if already processed
        if video_id in checkpoint.state["processed_videos"]:
            logger.info(f"Skipping already processed video: {video_id}")
            continue
        
        # Update progress
        checkpoint.update_progress(i)
        
        # Process video
        start_time = time.time()
        
        try:
            result = await process_video_with_retry(video_id)
            
            if result:
                processing_time = time.time() - start_time
                checkpoint.mark_processed(video_id, result)
                success_count += 1
                
                logger.info(f"✅ Successfully processed video {i+1}/{len(videos)}: {video_id}")
                logger.info(f"   Processing time: {processing_time:.2f}s")
                
                # Log some key insights
                if "summary" in result:
                    logger.info(f"   Summary: {result['summary'][:100]}...")
                
            else:
                failure_count += 1
                error_msg = "Processing returned None"
                checkpoint.mark_failed(video_id, error_msg)
                
                # Try to find solution
                solution = await search_youtube_solution(error_msg)
                if solution:
                    logger.info(f"   Suggested solution: {solution}")
                
        except Exception as e:
            failure_count += 1
            error_msg = str(e)
            checkpoint.mark_failed(video_id, error_msg)
            logger.error(f"❌ Failed to process video {i+1}/{len(videos)}: {video_id}")
            logger.error(f"   Error: {error_msg}")
            
            # Try to find solution
            solution = await search_youtube_solution(error_msg)
            if solution:
                logger.info(f"   Suggested solution: {solution}")
        
        # Progress report every 10 videos
        if (i + 1) % 10 == 0:
            logger.info(f"\n📊 PROGRESS REPORT: {i+1}/{len(videos)} videos processed")
            logger.info(f"   Success: {success_count}, Failed: {failure_count}")
            logger.info(f"   Success rate: {(success_count/(i+1))*100:.1f}%\n")
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(2)
    
    return success_count, failure_count

def generate_final_report(checkpoint: VideoProcessingCheckpoint):
    """Generate final processing report"""
    
    total_videos = len(TECHNICAL_BUSINESS_VIDEOS)
    processed = len(checkpoint.state["processed_videos"])
    failed = len(checkpoint.state["failed_videos"])
    success_rate = (processed / total_videos) * 100 if total_videos > 0 else 0
    
    report = f"""
    =====================================
    VIDEO PROCESSING FINAL REPORT
    =====================================
    
    Total Videos: {total_videos}
    Successfully Processed: {processed}
    Failed: {failed}
    Success Rate: {success_rate:.1f}%
    
    Start Time: {checkpoint.state['start_time']}
    End Time: {datetime.now().isoformat()}
    
    Failed Videos:
    """
    
    for failure in checkpoint.state["failed_videos"]:
        report += f"\n    - {failure['video_id']}: {failure['error']}"
    
    # Save report
    report_file = f"video_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    # Also save detailed JSON report
    json_report = {
        "summary": {
            "total_videos": total_videos,
            "processed": processed,
            "failed": failed,
            "success_rate": success_rate
        },
        "videos": checkpoint.state["results"],
        "failures": checkpoint.state["failed_videos"],
        "metadata": {
            "start_time": checkpoint.state["start_time"],
            "end_time": datetime.now().isoformat()
        }
    }
    
    json_report_file = f"video_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_report_file, 'w') as f:
        json.dump(json_report, f, indent=2)
    
    logger.info(report)
    logger.info(f"\n📄 Reports saved to:")
    logger.info(f"   - {report_file}")
    logger.info(f"   - {json_report_file}")

async def main():
    """Main function to process 100 technical business videos"""
    
    logger.info("🚀 Starting Technical Business Video Processing Test")
    logger.info(f"📹 Total videos to process: {len(TECHNICAL_BUSINESS_VIDEOS)}")
    
    # Check dependencies
    if not PROCESSOR_AVAILABLE:
        logger.error("❌ Video processor not available. Please check imports.")
        return
    
    # Initialize checkpoint
    checkpoint = VideoProcessingCheckpoint()
    
    # Get starting point
    start_index = checkpoint.state["last_processed_index"] + 1
    if start_index > 0:
        logger.info(f"📌 Resuming from video #{start_index}")
    
    # Process videos
    try:
        success, failed = await process_batch(
            TECHNICAL_BUSINESS_VIDEOS,
            checkpoint,
            start_index
        )
        
        logger.info(f"\n✅ Processing complete!")
        logger.info(f"   Success: {success}")
        logger.info(f"   Failed: {failed}")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Processing interrupted by user")
        logger.info("Checkpoint saved - can resume later")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
    finally:
        # Generate final report
        generate_final_report(checkpoint)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())