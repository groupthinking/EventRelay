#!/usr/bin/env python3
"""
COMPREHENSIVE TEST: 100 Technical Business YouTube Videos
Tests the working version by consuming 100 Technical Business YouTube videos
with error handling, checkpointing, and progress tracking.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import random

# Import the main video processor
from process_video_with_mcp import RealVideoProcessor
from real_technical_videos_list import REAL_TECHNICAL_VIDEOS, VIDEO_CATEGORIES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [BATCH_TEST] %(message)s',
    handlers=[
        logging.FileHandler('batch_test_100_videos.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("batch_test_processor")

class BatchVideoProcessor:
    """Process 100 Technical Business YouTube videos with comprehensive tracking"""
    
    def __init__(self):
        self.processor = RealVideoProcessor(real_mode_only=True)
        self.checkpoint_file = Path('batch_test_checkpoint.json')
        self.results_dir = Path('batch_test_results')
        self.results_dir.mkdir(exist_ok=True)
        
        # Technical Business YouTube video URLs (100 videos)
        self.technical_videos = REAL_TECHNICAL_VIDEOS
        
        # Load checkpoint if exists
        self.checkpoint = self._load_checkpoint()
        
    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint data"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                logger.info(f"✅ Loaded checkpoint: {checkpoint['processed_count']} videos processed")
                return checkpoint
            except Exception as e:
                logger.warning(f"⚠️ Failed to load checkpoint: {e}")
        
        return {
            'processed_count': 0,
            'failed_count': 0,
            'current_index': 0,
            'start_time': datetime.now().isoformat(),
            'results': [],
            'errors': []
        }
    
    def _save_checkpoint(self):
        """Save checkpoint data"""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
            logger.info(f"💾 Checkpoint saved: {self.checkpoint['processed_count']} videos processed")
        except Exception as e:
            logger.error(f"❌ Failed to save checkpoint: {e}")
    
    async def process_single_video(self, video_url: str, index: int) -> Dict[str, Any]:
        """Process a single video with error handling"""
        start_time = time.time()
        
        try:
            logger.info(f"🎯 Processing video {index + 1}/100: {video_url}")
            
            # Process video
            result = await self.processor.process_video_real(video_url)
            
            processing_time = time.time() - start_time
            
            # Create result entry
            result_entry = {
                'index': index,
                'video_url': video_url,
                'video_id': result.get('video_id', 'unknown'),
                'category': result.get('actionable_content', {}).get('category', 'unknown'),
                'actions_count': len(result.get('actionable_content', {}).get('actions', [])),
                'processing_time': processing_time,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Video {index + 1} processed successfully in {processing_time:.2f}s")
            return result_entry
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_entry = {
                'index': index,
                'video_url': video_url,
                'error': str(e),
                'processing_time': processing_time,
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.error(f"❌ Video {index + 1} failed: {e}")
            return error_entry
    
    async def run_batch_test(self):
        """Run the complete batch test of 100 videos"""
        logger.info("🚀 STARTING BATCH TEST: 100 Technical Business YouTube Videos")
        logger.info(f"📊 Checkpoint loaded: {self.checkpoint['processed_count']} videos already processed")
        
        total_videos = len(self.technical_videos)
        start_time = time.time()
        
        # Process videos from checkpoint position
        for i in range(self.checkpoint['current_index'], total_videos):
            video_url = self.technical_videos[i]
            
            # Process video
            result = await self.process_single_video(video_url, i)
            
            # Update checkpoint
            if result['success']:
                self.checkpoint['processed_count'] += 1
                self.checkpoint['results'].append(result)
            else:
                self.checkpoint['failed_count'] += 1
                self.checkpoint['errors'].append(result)
            
            self.checkpoint['current_index'] = i + 1
            
            # Save checkpoint every 10 videos
            if (i + 1) % 10 == 0:
                self._save_checkpoint()
                logger.info(f"📈 Progress: {i + 1}/{total_videos} videos processed")
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(random.uniform(1, 3))
        
        # Final checkpoint save
        self._save_checkpoint()
        
        # Generate final report
        total_time = time.time() - start_time
        await self._generate_final_report(total_time)
        
        logger.info("🎉 BATCH TEST COMPLETED!")
        return self.checkpoint
    
    async def _generate_final_report(self, total_time: float):
        """Generate comprehensive final report"""
        report = {
            'test_summary': {
                'total_videos': len(self.technical_videos),
                'processed_count': self.checkpoint['processed_count'],
                'failed_count': self.checkpoint['failed_count'],
                'success_rate': (self.checkpoint['processed_count'] / len(self.technical_videos)) * 100,
                'total_time': total_time,
                'average_time_per_video': total_time / len(self.technical_videos)
            },
            'category_breakdown': {},
            'performance_metrics': {
                'fastest_processing': float('inf'),
                'slowest_processing': 0,
                'average_processing_time': 0
            },
            'errors_summary': [],
            'recommendations': []
        }
        
        # Analyze results
        processing_times = []
        for result in self.checkpoint['results']:
            if result['success']:
                processing_times.append(result['processing_time'])
                
                # Category breakdown
                category = result['category']
                if category not in report['category_breakdown']:
                    report['category_breakdown'][category] = 0
                report['category_breakdown'][category] += 1
        
        # Calculate performance metrics
        if processing_times:
            report['performance_metrics']['fastest_processing'] = min(processing_times)
            report['performance_metrics']['slowest_processing'] = max(processing_times)
            report['performance_metrics']['average_processing_time'] = sum(processing_times) / len(processing_times)
        
        # Error analysis
        for error in self.checkpoint['errors']:
            report['errors_summary'].append({
                'video_url': error['video_url'],
                'error': error['error'],
                'processing_time': error['processing_time']
            })
        
        # Generate recommendations
        if report['test_summary']['success_rate'] < 90:
            report['recommendations'].append("Consider implementing retry logic for failed videos")
        
        if report['performance_metrics']['average_processing_time'] > 30:
            report['recommendations'].append("Optimize processing speed - consider parallel processing")
        
        # Save report
        report_file = self.results_dir / f"batch_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Final report saved to: {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("🎯 BATCH TEST RESULTS SUMMARY")
        print("="*60)
        print(f"📊 Total Videos: {report['test_summary']['total_videos']}")
        print(f"✅ Successfully Processed: {report['test_summary']['processed_count']}")
        print(f"❌ Failed: {report['test_summary']['failed_count']}")
        print(f"📈 Success Rate: {report['test_summary']['success_rate']:.1f}%")
        print(f"⏱️ Total Time: {report['test_summary']['total_time']:.2f}s")
        print(f"⚡ Avg Time per Video: {report['test_summary']['average_time_per_video']:.2f}s")
        print(f"🚀 Fastest Processing: {report['performance_metrics']['fastest_processing']:.2f}s")
        print(f"🐌 Slowest Processing: {report['performance_metrics']['slowest_processing']:.2f}s")
        print("="*60)

async def main():
    """Main execution function"""
    print("🚀 Starting comprehensive test of 100 Technical Business YouTube videos...")
    print("📋 This will test the working version with real video processing")
    print("💾 Checkpoint system enabled - can resume if interrupted")
    print("📊 Progress tracking and error handling included")
    print()
    
    processor = BatchVideoProcessor()
    
    try:
        results = await processor.run_batch_test()
        print(f"\n🎉 Test completed successfully!")
        print(f"📊 Final results: {results['processed_count']} processed, {results['failed_count']} failed")
        
    except KeyboardInterrupt:
        print("\n⏸️ Test interrupted by user. Checkpoint saved for resume.")
        processor._save_checkpoint()
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        processor._save_checkpoint()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())