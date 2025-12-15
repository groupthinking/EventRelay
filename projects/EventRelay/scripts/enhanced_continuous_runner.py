#!/usr/bin/env python3
"""
ENHANCED CONTINUOUS RUNNER WITH LLAMA BACKGROUND AGENT
Advanced video processing pipeline using Llama 3.1 8B for intelligent analysis

This runner provides:
- Llama-powered content analysis and categorization
- Intelligent quality assessment
- Learning from processed videos
- MCP tool integration
- Performance monitoring and optimization
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

import sys
# REMOVED: sys.path.insert with Path manipulation

# Import Llama agent
try:
    from ..agents.llama_background_agent import LlamaBackgroundAgent, create_llama_background_agent
    HAS_LLAMA = True
except ImportError:
    try:
        from agents.llama_background_agent import LlamaBackgroundAgent, create_llama_background_agent
        HAS_LLAMA = True
    except ImportError:
        HAS_LLAMA = False
        print("⚠️  Llama agent not available, falling back to basic processing")

# Import existing components
try:
    from ..agents.process_video_with_mcp import RealVideoProcessor
    from ..agents.action_implementer import ActionImplementer
    from ..agents.specialized.quality_agent import QualityAgent
except ImportError:
    try:
        from agents.process_video_with_mcp import RealVideoProcessor
        from agents.action_implementer import ActionImplementer
        from agents.specialized.quality_agent import QualityAgent
    except ImportError:
        RealVideoProcessor = None
        ActionImplementer = None
        QualityAgent = None

# YouTube API
try:
    from googleapiclient.discovery import build
    HAS_YT_API = True
except ImportError:
    HAS_YT_API = False

class EnhancedContinuousRunner:
    """Enhanced continuous runner with Llama Background Agent"""
    
    def __init__(self):
        self.llama_agent = None
        self.quality_agent = QualityAgent() if QualityAgent else None
        self.action_implementer = ActionImplementer() if ActionImplementer else None
        
        # Performance tracking
        self.start_time = time.time()
        self.total_videos_processed = 0
        self.successful_videos = 0
        self.failed_videos = 0
        self.average_quality_score = 0.0
        
        # Learning insights
        self.learning_insights = []
        
        # Configuration
        self.batch_size = int(os.getenv('BATCH_SIZE', '10'))
        self.sleep_interval = int(os.getenv('SLEEP_INTERVAL', '60'))
        self.use_llama = HAS_LLAMA and os.getenv('USE_LLAMA', 'true').lower() == 'true'
        
        print(f"🚀 Enhanced Continuous Runner initialized")
        print(f"   - Llama Agent: {'✅ Available' if HAS_LLAMA else '❌ Not available'}")
        print(f"   - Use Llama: {'✅ Enabled' if self.use_llama else '❌ Disabled'}")
        print(f"   - Batch Size: {self.batch_size}")
        print(f"   - Sleep Interval: {self.sleep_interval}s")
    
    async def initialize(self) -> bool:
        """Initialize the runner and Llama agent"""
        try:
            if self.use_llama and HAS_LLAMA:
                print("🔮 Initializing Llama 3.1 8B Background Agent...")
                self.llama_agent = await create_llama_background_agent()
                print("✅ Llama agent initialized successfully!")
            
            # Create necessary directories
            self._ensure_directories()
            
            # Initialize YouTube API if available
            self.yt_api = None
            yt_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("REACT_APP_YOUTUBE_API_KEY")
            if HAS_YT_API and yt_key:
                try:
                    self.yt_api = build("youtube", "v3", developerKey=yt_key)
                    print("✅ YouTube API initialized")
                except Exception as e:
                    print(f"⚠️  YouTube API initialization failed: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def _ensure_directories(self):
        """Ensure all necessary directories exist"""
        directories = [
            "workflow_results",
            "workflow_results/videos",
            "workflow_results/failures",
            "workflow_results/learning_logs",
            "workflow_results/implementation_plans",
            "models/llama-3.1-8b-instruct"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def process_video_with_llama(self, video_id: str, url: str) -> Dict[str, Any]:
        """Process video using Llama agent for enhanced analysis"""
        try:
            print(f"🔮 Processing video {video_id} with Llama agent...")
            
            # Get basic video info
            processor = RealVideoProcessor(real_mode_only=False)
            basic_result = await processor.process_video_real(url)
            
            if not basic_result.get('success'):
                return basic_result
            
            transcript = basic_result.get('transcript_data', {}).get('transcript', '')
            if not transcript:
                return {**basic_result, 'llama_enhanced': False, 'error': 'No transcript available'}
            
            # Enhanced analysis with Llama
            metadata = {
                'video_id': video_id,
                'title': basic_result.get('video_metadata', {}).get('title', 'Unknown'),
                'duration': basic_result.get('video_metadata', {}).get('duration', 'Unknown'),
                'upload_date': basic_result.get('video_metadata', {}).get('upload_date', 'Unknown')
            }
            
            # Llama content analysis
            llama_analysis = await self.llama_agent.analyze_video_content(transcript, metadata)
            
            # Quality assessment
            quality_score = await self.llama_agent.assess_video_quality(llama_analysis, transcript)
            
            # Generate implementation plan
            implementation_plan = await self.llama_agent.generate_implementation_plan(
                llama_analysis.action_items, video_id
            )
            
            # Extract learning insights
            insights = await self.llama_agent.learn_from_video(llama_analysis, transcript)
            self.learning_insights.extend(insights)
            
            # Enhanced result
            enhanced_result = {
                **basic_result,
                'llama_enhanced': True,
                'llama_analysis': {
                    'content_category': llama_analysis.content_category,
                    'confidence_score': llama_analysis.confidence_score,
                    'key_topics': llama_analysis.key_topics,
                    'action_items': llama_analysis.action_items,
                    'quality_score': quality_score,
                    'processing_time': llama_analysis.processing_time
                },
                'implementation_plan': implementation_plan,
                'learning_insights': [insight.__dict__ for insight in insights]
            }
            
            print(f"✅ Video {video_id} enhanced with Llama analysis")
            return enhanced_result
            
        except Exception as e:
            print(f"❌ Llama processing failed for {video_id}: {e}")
            # Fallback to basic processing
            if RealVideoProcessor:
                processor = RealVideoProcessor(real_mode_only=False)
                return await processor.process_video_real(url)
            else:
                return {'success': False, 'error': str(e), 'video_id': video_id}
    
    async def process_video_basic(self, video_id: str, url: str) -> Dict[str, Any]:
        """Process video using basic processor (fallback)"""
        try:
            print(f"📹 Processing video {video_id} with basic processor...")
            
            if RealVideoProcessor:
                processor = RealVideoProcessor(real_mode_only=False)
                result = await processor.process_video_real(url)
                
                # Basic quality assessment if available
                if self.quality_agent and hasattr(self.quality_agent, 'assess_actionability'):
                    actions = result.get('action_items', [])
                    transcript_segments = [{"text": result.get('transcript_data', {}).get('transcript', '')}]
                    quality_result = self.quality_agent.assess_actionability(actions, transcript_segments, {'video_id': video_id})
                    result['quality_score'] = quality_result.get('overall_score', 0)
                
                return result
            else:
                return {'success': False, 'error': 'No processor available', 'video_id': video_id}
                
        except Exception as e:
            print(f"❌ Basic processing failed for {video_id}: {e}")
            return {'success': False, 'error': str(e), 'video_id': video_id}
    
    async def save_video_result(self, result: Dict[str, Any], video_id: str):
        """Save enhanced video result"""
        try:
            # Save to videos directory
            video_file = Path(f"workflow_results/videos/{video_id}.json")
            video_file.write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
            
            # Save implementation plan if available
            if result.get('implementation_plan'):
                plan_file = Path(f"workflow_results/implementation_plans/{video_id}_plan.json")
                plan_file.write_text(json.dumps(result['implementation_plan'], indent=2, default=str), encoding='utf-8')
            
            # Update learning log
            await self._update_learning_log(result)
            
            print(f"💾 Saved results for video {video_id}")
            
        except Exception as e:
            print(f"❌ Failed to save results for {video_id}: {e}")
    
    async def _update_learning_log(self, result: Dict[str, Any]):
        """Update the learning log with new insights"""
        try:
            log_file = Path("workflow_results/learning_log.json")
            
            if log_file.exists():
                with log_file.open('r', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                log_data = []
            
            # Add new entry
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'video_id': result.get('video_id', 'unknown'),
                'success': result.get('success', False),
                'processing_time': result.get('processing_time', 0),
                'llama_enhanced': result.get('llama_enhanced', False)
            }
            
            # Add Llama-specific data if available
            if result.get('llama_enhanced'):
                llama_data = result.get('llama_analysis', {})
                log_entry.update({
                    'content_category': llama_data.get('content_category'),
                    'quality_score': llama_data.get('quality_score'),
                    'confidence_score': llama_data.get('confidence_score'),
                    'key_topics': llama_data.get('key_topics', []),
                    'action_items_count': len(llama_data.get('action_items', [])),
                    'learning_insights': result.get('learning_insights', [])
                })
            
            # Add quality score if available
            if result.get('quality_score'):
                log_entry['quality_score'] = result['quality_score']
            
            log_data.append(log_entry)
            
            # Save updated log
            with log_file.open('w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"❌ Failed to update learning log: {e}")
    
    async def precheck_video_availability(self, video_ids: List[str]) -> List[str]:
        """Pre-check video availability using YouTube API"""
        if not self.yt_api or not video_ids:
            return video_ids
        
        try:
            kept = []
            skip = []
            
            # Process in chunks of 50 (YouTube API limit)
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i:i+50]
                try:
                    response = self.yt_api.videos().list(
                        part="status,contentDetails",
                        id=",".join(chunk)
                    ).execute()
                    
                    status_map = {item['id']: item.get('status', {}) for item in response.get('items', [])}
                    
                    for vid in chunk:
                        status = status_map.get(vid, {})
                        if (status.get('privacyStatus') == 'public' and 
                            status.get('uploadStatus') not in ['rejected', 'failed']):
                            kept.append(vid)
                        else:
                            skip.append(vid)
                            await self._log_failure(vid, 'precheck_unavailable')
                            
                except Exception as e:
                    print(f"⚠️  YouTube API chunk check failed: {e}")
                    # Keep videos if API check fails
                    kept.extend(chunk)
            
            if skip:
                print(f"⏭️  Skipped {len(skip)} unavailable videos: {skip}")
            
            return kept
            
        except Exception as e:
            print(f"❌ Video availability pre-check failed: {e}")
            return video_ids
    
    async def _log_failure(self, video_id: str, error: str):
        """Log video processing failure"""
        try:
            failure_file = Path(f"workflow_results/failures/{video_id}.json")
            failure_data = {
                'video_id': video_id,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
            failure_file.write_text(json.dumps(failure_data, indent=2), encoding='utf-8')
        except Exception as e:
            print(f"❌ Failed to log failure for {video_id}: {e}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'uptime_formatted': f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
            'total_videos_processed': self.total_videos_processed,
            'successful_videos': self.successful_videos,
            'failed_videos': self.failed_videos,
            'success_rate': (self.successful_videos / max(self.total_videos_processed, 1)) * 100,
            'average_quality_score': self.average_quality_score,
            'learning_insights_count': len(self.learning_insights),
            'llama_agent_available': self.llama_agent is not None,
            'last_updated': datetime.now().isoformat()
        }
    
    async def run(self):
        """Main continuous processing loop"""
        print("🚀 Starting Enhanced Continuous Runner...")
        
        if not await self.initialize():
            print("❌ Failed to initialize runner")
            return
        
        queue_path = Path("workflow_results/video_queue.json")
        
        while True:
            try:
                # Load video queue
                if not queue_path.exists():
                    queue_path.write_text(json.dumps({
                        "pending": [],
                        "processed": [],
                        "failed": []
                    }, indent=2))
                
                with queue_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not data.get('pending'):
                    stats = await self.get_performance_stats()
                    print(f"💤 No pending videos. Sleeping {self.sleep_interval}s...")
                    print(f"📊 Current stats: {stats['total_videos_processed']} processed, {stats['success_rate']:.1f}% success rate")
                    await asyncio.sleep(self.sleep_interval)
                    continue
                
                # Process batch
                batch = data['pending'][:self.batch_size]
                del data['pending'][:self.batch_size]
                
                # Save updated queue
                with queue_path.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                print(f"📦 Processing batch of {len(batch)} videos...")
                
                # Pre-check availability
                available_videos = await self.precheck_video_availability(batch)
                
                if not available_videos:
                    print("⚠️  No videos available in current batch")
                    continue
                
                # Process videos
                for video_id in available_videos:
                    try:
                        url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        # Choose processing method
                        if self.use_llama and self.llama_agent:
                            result = await self.process_video_with_llama(video_id, url)
                        else:
                            result = await self.process_video_basic(video_id, url)
                        
                        # Update counters
                        self.total_videos_processed += 1
                        if result.get('success'):
                            self.successful_videos += 1
                            
                            # Update quality score average
                            quality_score = result.get('quality_score', 0)
                            if quality_score > 0:
                                self.average_quality_score = (
                                    (self.average_quality_score * (self.successful_videos - 1) + quality_score) / 
                                    self.successful_videos
                                )
                        else:
                            self.failed_videos += 1
                            await self._log_failure(video_id, result.get('error', 'unknown_error'))
                        
                        # Save result
                        await self.save_video_result(result, video_id)
                        
                        # Update queue
                        data['processed'].append(video_id)
                        
                    except Exception as e:
                        print(f"❌ Error processing video {video_id}: {e}")
                        self.failed_videos += 1
                        await self._log_failure(video_id, str(e))
                
                # Save updated queue
                with queue_path.open('w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                # Print batch summary
                stats = await self.get_performance_stats()
                print(f"✅ Batch complete. Stats: {stats['total_videos_processed']} total, {stats['success_rate']:.1f}% success")
                
            except KeyboardInterrupt:
                print("\n🛑 Enhanced Continuous Runner stopped by user")
                break
            except Exception as e:
                print(f"❌ Runner error: {e}")
                await asyncio.sleep(10)  # Brief pause before retry
        
        # Cleanup
        if self.llama_agent:
            await self.llama_agent.shutdown()
        
        # Final stats
        final_stats = await self.get_performance_stats()
        print(f"📊 Final stats: {final_stats}")

async def main():
    """Main entry point"""
    runner = EnhancedContinuousRunner()
    await runner.run()

if __name__ == "__main__":
    asyncio.run(main())
