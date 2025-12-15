#!/usr/bin/env python3
"""
VIDEO TO ACTION WORKFLOW
Complete end-to-end system for processing YouTube videos and generating actionable content
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Import our processing modules
try:
    from enhanced_video_processor import EnhancedVideoProcessor
    from action_implementer import ActionImplementer
except ImportError:
    print("❌ ERROR: Required modules not found. Make sure enhanced_video_processor.py and action_implementer.py are in the same directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [WORKFLOW] %(message)s',
    handlers=[
        logging.FileHandler('video_to_action_workflow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("video_to_action_workflow")

class VideoToActionWorkflow:
    """Complete workflow for processing videos and generating actionable content"""
    
    def __init__(self):
        self.video_processor = EnhancedVideoProcessor()
        self.action_implementer = ActionImplementer()
        self.workflow_dir = Path('workflow_results')
        self.workflow_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("🎯 VIDEO TO ACTION WORKFLOW INITIALIZED")
    
    async def process_video_to_actions(self, video_url: str) -> Dict[str, Any]:
        """Complete workflow: process video and generate actionable content"""
        
        start_time = time.time()
        video_id = self.video_processor.extract_video_id(video_url)
        
        logger.info(f"🚀 STARTING COMPLETE WORKFLOW FOR: {video_id}")
        print(f"\n🎯 PROCESSING VIDEO: {video_url}")
        print("=" * 60)
        
        try:
            # Stage 1: Process video and extract metadata
            print("📊 Stage 1: Extracting video metadata...")
            video_data = await self.video_processor.process_video_enhanced(video_url)
            
            if not video_data['success']:
                raise Exception(f"Video processing failed: {video_data.get('error', 'Unknown error')}")
            
            print(f"✅ Video processed successfully!")
            print(f"   Category: {video_data['actionable_content']['category']}")
            print(f"   Actions Generated: {len(video_data['actionable_content']['actions'])}")
            
            # Stage 2: Create implementation plans
            print("\n📋 Stage 2: Creating implementation plans...")
            # Convert video_data to the format expected by action_implementer
            processed_video_data = {
                'video_id': video_data['video_id'],
                'category': video_data['actionable_content']['category'],
                'actions': video_data['actionable_content']['actions'],
                'metadata': video_data['metadata']
            }
            implementation_plan = self.action_implementer.create_implementation_plan(processed_video_data)
            
            # Stage 3: Save comprehensive results
            print("\n💾 Stage 3: Saving comprehensive results...")
            workflow_result = await self._save_workflow_results(video_data, implementation_plan, processed_video_data)
            
            # Stage 4: Generate summary report
            print("\n📊 Stage 4: Generating summary report...")
            summary_report = self._generate_summary_report(processed_video_data, implementation_plan)
            
            processing_time = time.time() - start_time
            
            final_result = {
                'video_id': video_id,
                'video_url': video_url,
                'video_data': video_data,
                'processed_video_data': processed_video_data,
                'implementation_plan': implementation_plan,
                'workflow_result': workflow_result,
                'summary_report': summary_report,
                'processing_time': processing_time,
                'timestamp': datetime.now().isoformat(),
                'success': True
            }
            
            logger.info(f"✅ COMPLETE WORKFLOW SUCCESS: {video_id} in {processing_time:.3f}s")
            
            return final_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ WORKFLOW FAILED: {video_id} - {e}")
            
            return {
                'video_id': video_id,
                'error': str(e),
                'processing_time': processing_time,
                'success': False
            }
    
    async def _save_workflow_results(self, video_data: Dict[str, Any], implementation_plan: Dict[str, Any], processed_video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save comprehensive workflow results"""
        
        video_id = video_data['video_id']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create workflow result file
        workflow_file = self.workflow_dir / f"{video_id}_workflow_{timestamp}.json"
        
        workflow_data = {
            'workflow_info': {
                'video_id': video_id,
                'timestamp': datetime.now().isoformat(),
                'processing_method': 'enhanced_metadata_analysis',
                'workflow_version': '1.0'
            },
            'video_processing': video_data,
            'action_implementation': implementation_plan,
            'summary': {
                'total_actions': len(processed_video_data['actions']),
                'category': processed_video_data['category'],
                'estimated_total_time': implementation_plan['estimated_total_time'],
                'priority_breakdown': self._analyze_priority_breakdown(processed_video_data['actions'])
            }
        }
        
        with open(workflow_file, 'w') as f:
            json.dump(workflow_data, f, indent=2)
        
        logger.info(f"✅ Workflow results saved to: {workflow_file}")
        
        return {
            'success': True,
            'workflow_file': str(workflow_file),
            'timestamp': workflow_data['workflow_info']['timestamp']
        }
    
    def _analyze_priority_breakdown(self, actions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze priority breakdown of actions"""
        priorities = {}
        for action in actions:
            priority = action.get('priority', 'unknown')
            priorities[priority] = priorities.get(priority, 0) + 1
        return priorities
    
    def _generate_summary_report(self, video_data: Dict[str, Any], implementation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive summary report"""
        
        video_id = video_data['video_id']
        category = video_data['category']
        actions = video_data['actions']
        
        # Calculate time estimates
        total_time = implementation_plan['estimated_total_time']
        high_priority_time = sum(
            self.action_implementer._parse_time_estimate(action['estimated_time'])
            for action in actions if action.get('priority') == 'high'
        )
        
        summary = {
            'video_info': {
                'id': video_id,
                'title': video_data['metadata'].get('title', 'Unknown'),
                'category': category,
                'extraction_method': video_data['metadata'].get('extraction_method', 'unknown')
            },
            'action_summary': {
                'total_actions': len(actions),
                'high_priority_actions': len([a for a in actions if a.get('priority') == 'high']),
                'medium_priority_actions': len([a for a in actions if a.get('priority') == 'medium']),
                'low_priority_actions': len([a for a in actions if a.get('priority') == 'low'])
            },
            'time_estimates': {
                'total_time_minutes': total_time,
                'high_priority_time_minutes': high_priority_time,
                'estimated_completion_days': max(1, total_time // 60)  # Assume 1 hour per day
            },
            'recommendations': self._generate_recommendations(video_data, implementation_plan),
            'next_steps': [
                'Review the generated implementation plan',
                'Prioritize high-priority actions',
                'Schedule time for action implementation',
                'Track progress and adjust as needed'
            ]
        }
        
        return summary
    
    def _generate_recommendations(self, video_data: Dict[str, Any], implementation_plan: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations based on content and actions"""
        
        category = video_data['actionable_content']['category']
        actions = video_data['actionable_content']['actions']
        total_time = implementation_plan['estimated_total_time']
        
        recommendations = []
        
        # Category-specific recommendations
        if category == 'Educational_Content':
            recommendations.extend([
                "Start with the learning pathway creation for maximum impact",
                "Consider creating a study group or finding a learning partner",
                "Set up regular review sessions to reinforce concepts"
            ])
        elif category == 'Business_Professional':
            recommendations.extend([
                "Focus on workflow automation for immediate productivity gains",
                "Document processes as you implement them",
                "Measure performance improvements to validate changes"
            ])
        elif category == 'Creative_DIY':
            recommendations.extend([
                "Gather all materials before starting any project",
                "Take photos of your progress for documentation",
                "Start with smaller projects to build confidence"
            ])
        elif category == 'Health_Fitness_Cooking':
            recommendations.extend([
                "Plan your meals and workouts in advance",
                "Start with simple recipes and gradually increase complexity",
                "Track your progress to stay motivated"
            ])
        elif category == 'Technology_Programming':
            recommendations.extend([
                "Set up your development environment first",
                "Practice coding regularly, even for short sessions",
                "Build a portfolio of projects to showcase your skills"
            ])
        
        # Time-based recommendations
        if total_time > 120:  # More than 2 hours
            recommendations.append("Break down the implementation into smaller, manageable sessions")
        elif total_time < 60:  # Less than 1 hour
            recommendations.append("You can complete this in one focused session")
        
        # Priority-based recommendations
        high_priority_count = len([a for a in actions if a.get('priority') == 'high'])
        if high_priority_count > 0:
            recommendations.append(f"Focus on the {high_priority_count} high-priority action(s) first")
        
        return recommendations
    
    def display_workflow_summary(self, result: Dict[str, Any]):
        """Display comprehensive workflow summary"""
        
        if not result['success']:
            print(f"\n❌ WORKFLOW FAILED: {result['error']}")
            return
        
        video_data = result['video_data']
        processed_video_data = result['processed_video_data']
        implementation_plan = result['implementation_plan']
        summary = result['summary_report']
        
        print(f"\n🎉 VIDEO TO ACTION WORKFLOW COMPLETE!")
        print("=" * 60)
        
        # Video Information
        print(f"\n📹 VIDEO INFORMATION:")
        print(f"   ID: {processed_video_data['video_id']}")
        print(f"   Title: {processed_video_data['metadata'].get('title', 'Unknown')}")
        print(f"   Category: {processed_video_data['category']}")
        print(f"   Processing Method: {processed_video_data['metadata'].get('extraction_method', 'unknown')}")
        
        # Action Summary
        print(f"\n📋 ACTION SUMMARY:")
        print(f"   Total Actions: {summary['action_summary']['total_actions']}")
        print(f"   High Priority: {summary['action_summary']['high_priority_actions']}")
        print(f"   Medium Priority: {summary['action_summary']['medium_priority_actions']}")
        print(f"   Low Priority: {summary['action_summary']['low_priority_actions']}")
        
        # Time Estimates
        print(f"\n⏱️ TIME ESTIMATES:")
        print(f"   Total Time: {summary['time_estimates']['total_time_minutes']} minutes")
        print(f"   High Priority Time: {summary['time_estimates']['high_priority_time_minutes']} minutes")
        print(f"   Estimated Completion: {summary['time_estimates']['estimated_completion_days']} day(s)")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(summary['recommendations'], 1):
            print(f"   {i}. {rec}")
        
        # Next Steps
        print(f"\n🚀 NEXT STEPS:")
        for i, step in enumerate(summary['next_steps'], 1):
            print(f"   {i}. {step}")
        
        # File Locations
        print(f"\n📁 FILES CREATED:")
        print(f"   Video Processing: {video_data['save_result']['file_path']}")
        print(f"   Implementation Plan: {implementation_plan.get('file_path', 'Generated in memory')}")
        print(f"   Workflow Results: {result['workflow_result']['workflow_file']}")
        
        print(f"\n✅ Processing completed in {result['processing_time']:.3f} seconds")

async def main():
    """Main execution function"""
    
    if len(sys.argv) < 2:
        print("Usage: python video_to_action_workflow.py <video_url>")
        print("Example: python video_to_action_workflow.py https://www.youtube.com/watch?v=aircAruvnKk")
        sys.exit(1)
    
    video_url = sys.argv[1]
    workflow = VideoToActionWorkflow()
    
    try:
        # Run complete workflow
        result = await workflow.process_video_to_actions(video_url)
        
        # Display comprehensive summary
        workflow.display_workflow_summary(result)
        
        return result
        
    except Exception as e:
        print(f"❌ WORKFLOW FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 