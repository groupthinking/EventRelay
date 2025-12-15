#!/usr/bin/env python3
"""
Autonomous Video Processor
Processes YouTube videos autonomously with cloud integration
"""

import json
import logging
import os
import sys
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import random

# REMOVED: sys.path.insert for autonomous_processor

# Import processors
try:
    from .simple_real_processor import process_video, extract_video_id
except ImportError:
    # Fallback for direct execution
    from simple_real_processor import process_video, extract_video_id

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [AUTONOMOUS] %(message)s',
    handlers=[
        logging.FileHandler('autonomous_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Video categories with sample searches
VIDEO_CATEGORIES = {
    "Educational_Content": [
        "machine learning tutorial",
        "python programming guide", 
        "data science course",
        "web development tutorial",
        "cloud computing basics"
    ],
    "Business_Professional": [
        "tech startup advice",
        "product management tutorial",
        "agile methodology guide",
        "business analytics tutorial",
        "digital marketing strategy"
    ],
    "Creative_DIY": [
        "coding project ideas",
        "tech DIY projects",
        "raspberry pi tutorial",
        "arduino projects",
        "3D printing guide"
    ],
    "Health_Fitness_Cooking": [
        "productivity tips developers",
        "ergonomics for programmers",
        "healthy habits tech workers",
        "meal prep programmers",
        "desk exercises developers"
    ]
}

# Predefined video IDs for each category (for demo purposes)
CATEGORY_VIDEO_IDS = {
    "Educational_Content": [
        "aircAruvnKk", "fOqJJphkZA", "gV0_raKR2UQ", "J4Wdy0Wc_xQ", "mJeNghZXtMo",
        "HgWvYvvXIM", "TjkFGrjkXfc", "7eh4d6r5fNQ", "X2vAabgKEyw", "LHBE6Q9XlzI",
        "xC-c7E5PK0Y", "ua-CiDNNj30", "zg9ASOp5j8", "GtQjRJnvV8", "KaTE5lPRbn0",
        "nfr5j_1BgD8", "5q87K1WaoFI", "Gv9_4yMHFhI", "rGx1QNdYzvs", "jflA3vXw5Qo",
        "h00gbp36KWg", "HZOv0qUzo8A", "ub3P8TnFS8M", "44E8o-IqWTY", "nFQaZmvCayw"
    ],
    "Business_Professional": [
        "ZoqgAy3h4OM", "nKIu9yen5nc", "BXgQDlW6jxE", "VECV6r-fQPg", "V7h3kGtqV8",
        "CTBt9NCnqB8", "xPJoq_QVsY4", "jOhm-E2fVGk", "FZLXPC_ug2E", "4K6MhLXhx0M",
        "BdSiBlLafNM", "Unzc7oWbYg", "FRRh5hqzRg", "UvCri1tqIxQ", "502ILHjX9EE",
        "F8_ME4VwTiw", "JK_3nIFGOdE", "BkREIFyCuKY", "n_F1a7UpKqw", "QmOF0crdyRU",
        "dH0yz-Osy54", "OXE2a8dqIAA", "bEpU_7wFKM", "lpk7MkQ5xQI", "7kJysT7gXI"
    ],
    "Creative_DIY": [
        "YB5ELgW7JGQ", "SWYqp7iY_Tc", "WxpCXCIfyAY", "PkZNo7MFNFg", "OqBFXhR5E6Y",
        "2vMH8lxTvVE", "yIVXjl4SwVo", "JdeyVryaal0", "s7wmiS2mSXY", "GZvSYJDk-us",
        "mb-QHAqBL1g", "ByGJQzlzxQg", "FLnxgSZ0DG4", "cuPVDvPc9SY", "pxfEV6XKdY",
        "7YcW25PHnAA", "iFMLyMgCUTs", "6_xGKdYA0MM", "SSo_EIwHSd4", "hYip_Vuv8J0",
        "qOVAbKKSH10", "41Ilug_dDcM", "2yJqjTiwpxM", "s4g1XFU8Gto", "QAQatPPtUkU"
    ],
    "Health_Fitness_Cooking": [
        "n7IHhwmDCNE", "nU-IIXBWlS4", "5GBT4WJNnG0", "NLXys9vVXm8", "pVfGKMU1d9c",
        "9KhKPKxPeQI", "sZz5MPMdao", "0VGQbKQZ7k8", "vCh-HUACjUA", "JcTkbe0TT-U",
        "inWWhr5tnEA", "wXCD8Kb3K7Q", "z5nc9MDbvkw", "IQV0LnDoBkQ", "hXPmnoGVQW0",
        "infQ1knyPqI", "rdFYLTR9I4", "uPrYPUopgm8", "UsVfElI9nsM", "0GfNGKvtXhM",
        "KXdOoIDcmbM", "SyVMrxYSzUM", "37JxCFVAAHY", "t5zQpSjSu9I", "JdeyVryaal0"
    ]
}

class AutonomousProcessor:
    """Manages autonomous video processing"""
    
    def __init__(self, duration_hours: int = 4):
        self.duration_hours = duration_hours
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=duration_hours)
        self.processed_count = 0
        self.category_counts = {cat: 0 for cat in VIDEO_CATEGORIES}
        self.results = []
    
    def should_continue(self) -> bool:
        """Check if processing should continue"""
        return datetime.now() < self.end_time and self.processed_count < 100
    
    def get_next_video(self) -> tuple[str, str]:
        """Get next video to process"""
        # Select category with fewest processed videos
        category = min(self.category_counts, key=self.category_counts.get)
        
        # Get random video from category
        videos = CATEGORY_VIDEO_IDS[category]
        video_id = random.choice(videos)
        
        return video_id, category
    
    async def process_video_safe(self, video_id: str, category: str) -> Optional[Dict[str, Any]]:
        """Safely process a video with error handling"""
        try:
            logger.info(f"Processing video {video_id} from category: {category}")
            
            result = process_video(video_id)
            
            if result and result.get("status") == "success":
                # Save to category folder
                output_dir = Path(f"gdrive_results/{category}")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Save result
                output_file = output_dir / f"{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                logger.info(f"✅ Saved result to {output_file}")
                
                # Update counts
                self.processed_count += 1
                self.category_counts[category] += 1
                
                return result
            else:
                logger.warning(f"Failed to process video {video_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing video {video_id}: {e}")
            return None
    
    async def run(self):
        """Run autonomous processing"""
        logger.info(f"🚀 Starting autonomous processing for {self.duration_hours} hours")
        logger.info(f"Target: 100 videos across {len(VIDEO_CATEGORIES)} categories")
        
        while self.should_continue():
            # Get next video
            video_id, category = self.get_next_video()
            
            # Process video
            result = await self.process_video_safe(video_id, category)
            
            if result:
                self.results.append({
                    "video_id": video_id,
                    "category": category,
                    "timestamp": datetime.now().isoformat(),
                    "summary": result.get("summary", "")[:100]
                })
            
            # Progress update
            if self.processed_count % 10 == 0:
                self.log_progress()
            
            # Rate limiting
            await asyncio.sleep(5)  # 5 seconds between videos
        
        # Final report
        self.generate_report()
    
    def log_progress(self):
        """Log current progress"""
        elapsed = datetime.now() - self.start_time
        rate = self.processed_count / (elapsed.total_seconds() / 3600) if elapsed.total_seconds() > 0 else 0
        
        logger.info(f"\n📊 PROGRESS UPDATE:")
        logger.info(f"   Processed: {self.processed_count}/100 videos")
        logger.info(f"   Rate: {rate:.1f} videos/hour")
        logger.info(f"   Time elapsed: {elapsed}")
        logger.info(f"   Categories: {self.category_counts}\n")
    
    def generate_report(self):
        """Generate final processing report"""
        report = {
            "summary": {
                "total_processed": self.processed_count,
                "duration_hours": self.duration_hours,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "categories": self.category_counts
            },
            "videos": self.results,
            "performance": {
                "average_rate": self.processed_count / self.duration_hours,
                "success_rate": (self.processed_count / 100) * 100
            }
        }
        
        # Save report
        report_file = f"autonomous_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n🎯 AUTONOMOUS PROCESSING COMPLETE")
        logger.info(f"   Total videos processed: {self.processed_count}")
        logger.info(f"   Report saved to: {report_file}")
        
        # Display category breakdown
        logger.info("\n📊 Category Breakdown:")
        for category, count in self.category_counts.items():
            logger.info(f"   {category}: {count} videos")

async def main():
    """Main function for autonomous processing"""
    # Get configuration from environment or defaults
    duration_hours = int(os.environ.get("DURATION_HOURS", "4"))
    
    # Initialize processor
    processor = AutonomousProcessor(duration_hours)
    
    # Run processing
    await processor.run()

if __name__ == "__main__":
    asyncio.run(main())