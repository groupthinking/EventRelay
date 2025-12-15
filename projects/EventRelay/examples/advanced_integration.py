#!/usr/bin/env python3
"""
Advanced integration examples for production use cases
"""

import sys
import os

# Ensure the package is available (development mode)
try:
    import youtube_extension
except ImportError:
    # Add parent directory for development
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

import asyncio
from typing import List, Dict, Any
from pathlib import Path
import json
import time

from fastvlm_gemini_hybrid import HybridVLMProcessor, VideoPipeline
from fastvlm_gemini_hybrid.config import HybridConfig, ProcessingMode, TaskType


class ProductDemoAgent:
    """Real-time product demo agent using FastVLM"""
    
    def __init__(self):
        config = HybridConfig()
        config.default_mode = ProcessingMode.LOCAL_ONLY  # Force local for real-time
        self.processor = HybridVLMProcessor(config)
    
    def analyze_product_screen(self, screenshot):
        """Analyze product UI screenshot"""
        prompts = [
            "Describe the UI elements visible on screen",
            "What actions can the user take from this screen?",
            "Identify any potential usability issues"
        ]
        
        results = []
        for prompt in prompts:
            result = self.processor.process(
                screenshot,
                prompt,
                metadata={"task_type": "product_demo"}
            )
            results.append(result)
        
        return self._combine_analyses(results)
    
    def generate_demo_script(self, screenshots: List):
        """Generate demo script from screenshots"""
        script_parts = []
        
        for i, screenshot in enumerate(screenshots):
            result = self.processor.process(
                screenshot,
                f"Generate a demo script for this screen (step {i+1})",
                metadata={"task_type": "product_demo"}
            )
            
            if result.get("success"):
                script_parts.append({
                    "step": i + 1,
                    "description": result["response"],
                    "latency": result.get("latency", 0)
                })
        
        return {
            "script": script_parts,
            "total_screens": len(screenshots),
            "average_latency": sum(p["latency"] for p in script_parts) / len(script_parts)
        }
    
    def _combine_analyses(self, results):
        """Combine multiple analysis results"""
        combined = {
            "ui_elements": "",
            "user_actions": "",
            "issues": "",
            "success": all(r.get("success") for r in results)
        }
        
        for i, result in enumerate(results):
            if result.get("success"):
                if i == 0:
                    combined["ui_elements"] = result["response"]
                elif i == 1:
                    combined["user_actions"] = result["response"]
                elif i == 2:
                    combined["issues"] = result["response"]
        
        return combined


class TechnicalDocumentNavigator:
    """Navigate and understand technical documents"""
    
    def __init__(self):
        config = HybridConfig()
        config.fastvlm.max_tokens = 512  # Longer responses for technical content
        self.processor = HybridVLMProcessor(config)
    
    def extract_code_from_image(self, image_path):
        """Extract code from screenshot or diagram"""
        result = self.processor.process(
            image_path,
            "Extract all code visible in this image. Format it properly with syntax.",
            metadata={"task_type": "technical_document"},
            force_mode=ProcessingMode.LOCAL_ONLY
        )
        return result
    
    def analyze_architecture_diagram(self, diagram_path):
        """Analyze software architecture diagram"""
        analyses = {}
        
        # Components analysis
        analyses["components"] = self.processor.process(
            diagram_path,
            "List all components and services shown in this architecture diagram",
            metadata={"task_type": "technical_document"}
        )
        
        # Data flow analysis
        analyses["data_flow"] = self.processor.process(
            diagram_path,
            "Describe the data flow between components",
            metadata={"task_type": "technical_document"}
        )
        
        # Technology stack
        analyses["tech_stack"] = self.processor.process(
            diagram_path,
            "Identify the technologies and frameworks used",
            metadata={"task_type": "technical_document"}
        )
        
        return analyses
    
    def generate_documentation(self, images: List, output_format="markdown"):
        """Generate documentation from images"""
        doc_parts = []
        
        for image in images:
            result = self.processor.process(
                image,
                f"Generate {output_format} documentation for this technical content",
                metadata={"task_type": "technical_document"}
            )
            
            if result.get("success"):
                doc_parts.append(result["response"])
        
        if output_format == "markdown":
            return "\n\n---\n\n".join(doc_parts)
        else:
            return doc_parts


class YouTubeVideoAnalyzer:
    """Analyze YouTube videos using Gemini"""
    
    def __init__(self):
        config = HybridConfig()
        config.default_mode = ProcessingMode.CLOUD_ONLY  # Use Gemini for YouTube
        self.processor = HybridVLMProcessor(config)
        self.pipeline = VideoPipeline(self.processor)
    
    def analyze_youtube_video(self, video_url: str):
        """Analyze YouTube video content"""
        # Note: This requires downloading the video first
        # In production, you might use YouTube API directly
        
        analyses = {
            "summary": self._get_video_summary(video_url),
            "key_moments": self._extract_key_moments(video_url),
            "transcript_analysis": self._analyze_transcript(video_url),
            "visual_analysis": self._analyze_visuals(video_url)
        }
        
        return analyses
    
    def _get_video_summary(self, video_url):
        """Get video summary"""
        return self.processor.process(
            video_url,
            "Provide a comprehensive summary of this video",
            metadata={"source": "youtube", "task_type": "youtube_analysis"}
        )
    
    def _extract_key_moments(self, video_url):
        """Extract key moments from video"""
        return self.processor.process(
            video_url,
            "Identify and timestamp the key moments in this video",
            metadata={"source": "youtube", "task_type": "youtube_analysis"}
        )
    
    def _analyze_transcript(self, video_url):
        """Analyze video transcript"""
        return self.processor.process(
            video_url,
            "Analyze the speech and dialogue in this video",
            metadata={"source": "youtube", "task_type": "youtube_analysis"}
        )
    
    def _analyze_visuals(self, video_url):
        """Analyze visual content"""
        return self.processor.process(
            video_url,
            "Describe the visual elements, scenes, and cinematography",
            metadata={"source": "youtube", "task_type": "youtube_analysis"}
        )


class HybridWorkflowOrchestrator:
    """Orchestrate complex hybrid workflows"""
    
    def __init__(self):
        self.processor = HybridVLMProcessor()
        self.pipeline = VideoPipeline(self.processor)
    
    async def process_content_pipeline(self, content_path: str):
        """Process content through intelligent pipeline"""
        
        # Determine content type
        path = Path(content_path)
        is_video = path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']
        
        workflow = {
            "content_path": str(content_path),
            "content_type": "video" if is_video else "image",
            "timestamp": time.time(),
            "stages": []
        }
        
        if is_video:
            # Video workflow
            workflow["stages"] = await self._video_workflow(content_path)
        else:
            # Image workflow
            workflow["stages"] = await self._image_workflow(content_path)
        
        workflow["total_duration"] = time.time() - workflow["timestamp"]
        return workflow
    
    async def _video_workflow(self, video_path):
        """Video processing workflow"""
        stages = []
        
        # Stage 1: Quick preview with FastVLM
        stage1 = {
            "name": "quick_preview",
            "processor": "fastvlm",
            "start_time": time.time()
        }
        
        # Extract first frame for quick preview
        frames = self.pipeline.extract_frames(video_path, frame_rate=0.1, max_frames=1)
        if frames:
            from PIL import Image
            preview_result = self.processor.process(
                Image.fromarray(frames[0]),
                "Provide a quick preview of this video content",
                force_mode=ProcessingMode.LOCAL_ONLY
            )
            stage1["result"] = preview_result
        
        stage1["duration"] = time.time() - stage1["start_time"]
        stages.append(stage1)
        
        # Stage 2: Detailed analysis with Gemini
        stage2 = {
            "name": "detailed_analysis",
            "processor": "gemini",
            "start_time": time.time()
        }
        
        detailed_result = self.processor.process(
            video_path,
            "Provide detailed analysis of this video including content, quality, and insights",
            force_mode=ProcessingMode.CLOUD_ONLY
        )
        stage2["result"] = detailed_result
        stage2["duration"] = time.time() - stage2["start_time"]
        stages.append(stage2)
        
        # Stage 3: Generate actionable insights
        stage3 = {
            "name": "insights_generation",
            "processor": "hybrid",
            "start_time": time.time()
        }
        
        if stage2["result"].get("success"):
            insights_prompt = f"Based on this analysis: {stage2['result']['response'][:500]}, generate actionable insights"
            insights_result = self.processor.process(
                frames[0] if frames else video_path,
                insights_prompt,
                force_mode=ProcessingMode.HYBRID_AUTO
            )
            stage3["result"] = insights_result
        
        stage3["duration"] = time.time() - stage3["start_time"]
        stages.append(stage3)
        
        return stages
    
    async def _image_workflow(self, image_path):
        """Image processing workflow"""
        stages = []
        
        # Stage 1: Quick classification
        stage1 = {
            "name": "classification",
            "processor": "fastvlm",
            "start_time": time.time()
        }
        
        classification_result = self.processor.process(
            image_path,
            "Classify this image: Is it technical, artistic, document, or general?",
            force_mode=ProcessingMode.LOCAL_ONLY
        )
        stage1["result"] = classification_result
        stage1["duration"] = time.time() - stage1["start_time"]
        stages.append(stage1)
        
        # Stage 2: Specialized processing based on classification
        stage2 = {
            "name": "specialized_processing",
            "start_time": time.time()
        }
        
        if stage1["result"].get("success"):
            response = stage1["result"]["response"].lower()
            
            if "technical" in response or "document" in response:
                # Use FastVLM for technical content
                stage2["processor"] = "fastvlm"
                specialized_result = self.processor.process(
                    image_path,
                    "Extract all technical information, code, and diagrams",
                    force_mode=ProcessingMode.LOCAL_ONLY
                )
            else:
                # Use Gemini for complex analysis
                stage2["processor"] = "gemini"
                specialized_result = self.processor.process(
                    image_path,
                    "Provide artistic analysis and creative interpretation",
                    force_mode=ProcessingMode.CLOUD_ONLY
                )
            
            stage2["result"] = specialized_result
        
        stage2["duration"] = time.time() - stage2["start_time"]
        stages.append(stage2)
        
        return stages


def example_product_demo():
    """Example: Product Demo Agent"""
    print("\n=== Product Demo Agent Example ===")
    
    agent = ProductDemoAgent()
    
    # Create sample screenshots (in production, use real screenshots)
    from PIL import Image
    screenshots = [
        Image.new('RGB', (1920, 1080), color='white'),
        Image.new('RGB', (1920, 1080), color='lightgray'),
        Image.new('RGB', (1920, 1080), color='lightblue')
    ]
    
    # Analyze first screen
    print("\nAnalyzing product screen...")
    analysis = agent.analyze_product_screen(screenshots[0])
    print(f"Analysis complete: {analysis['success']}")
    
    # Generate demo script
    print("\nGenerating demo script...")
    script = agent.generate_demo_script(screenshots)
    print(f"Generated script for {script['total_screens']} screens")
    print(f"Average latency: {script['average_latency']:.2f}s")


def example_technical_navigation():
    """Example: Technical Document Navigation"""
    print("\n=== Technical Document Navigator Example ===")
    
    navigator = TechnicalDocumentNavigator()
    
    # Create sample technical image
    from PIL import Image
    tech_image = Image.new('RGB', (800, 600), color='white')
    
    print("\nExtracting code from image...")
    code_result = navigator.extract_code_from_image(tech_image)
    print(f"Code extraction: {code_result.get('success')}")
    
    print("\nAnalyzing architecture diagram...")
    architecture = navigator.analyze_architecture_diagram(tech_image)
    print(f"Components analysis: {architecture['components'].get('success')}")
    print(f"Data flow analysis: {architecture['data_flow'].get('success')}")
    print(f"Tech stack analysis: {architecture['tech_stack'].get('success')}")


async def example_workflow_orchestration():
    """Example: Hybrid Workflow Orchestration"""
    print("\n=== Hybrid Workflow Orchestration Example ===")
    
    orchestrator = HybridWorkflowOrchestrator()
    
    # Create sample content
    from PIL import Image
    sample_image = Image.new('RGB', (1024, 768), color='green')
    sample_image.save('/tmp/sample_content.jpg')
    
    print("\nProcessing content through hybrid pipeline...")
    workflow = await orchestrator.process_content_pipeline('/tmp/sample_content.jpg')
    
    print(f"\nWorkflow completed:")
    print(f"Content type: {workflow['content_type']}")
    print(f"Total duration: {workflow['total_duration']:.2f}s")
    print(f"Stages completed: {len(workflow['stages'])}")
    
    for stage in workflow['stages']:
        print(f"\n  Stage: {stage['name']}")
        print(f"    Processor: {stage.get('processor', 'unknown')}")
        print(f"    Duration: {stage['duration']:.2f}s")
        print(f"    Success: {stage.get('result', {}).get('success', False)}")
    
    # Clean up
    os.unlink('/tmp/sample_content.jpg')


if __name__ == "__main__":
    print("Advanced Integration Examples")
    print("=" * 50)
    
    # Run synchronous examples
    example_product_demo()
    example_technical_navigation()
    
    # Run async example
    asyncio.run(example_workflow_orchestration())
    
    print("\n" + "=" * 50)
    print("Advanced examples completed!")