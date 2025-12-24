#!/usr/bin/env python3
"""
Enhanced MCP Server with Integrated Video Processing Pipeline
Combines YouTube transcript extraction, NotebookLM processing, and VideoPrism analysis
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import asdict
import traceback

# Import our enhanced processors
from video_extractor_enhanced import EnhancedVideoExtractor, VideoContent
from notebooklm_processor import NotebookLMProcessor, VideoNotebook
from videoprism_analyzer import VideoPrismAnalyzer, VideoPrismAnalysis

# MCP imports
try:
    from mcp import McpServer
    from mcp.types import (
        Tool, TextContent, CallToolResult, 
        GetPromptResult, Prompt, PromptMessage, PromptArgument
    )
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logging.warning("MCP not available - running in standalone mode")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [EnhancedMCP] %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedMCPServer:
    """
    Enhanced MCP Server with integrated video processing capabilities
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize processors
        self.video_extractor = EnhancedVideoExtractor(config)
        self.notebook_processor = NotebookLMProcessor(config)
        self.videoprism_analyzer = VideoPrismAnalyzer(config)
        
        # Initialize MCP server if available
        if HAS_MCP:
            self.server = McpServer("enhanced-video-processor")
            self._register_tools()
            self._register_prompts()
        else:
            self.server = None
            logger.warning("MCP server not available - tools will run in standalone mode")
        
        # Processing cache
        self.processing_cache = {}
        
        logger.info("Enhanced MCP Server initialized")
    
    def _register_tools(self):
        """Register all available tools with the MCP server"""
        if not self.server:
            return
        
        # Video extraction tools
        @self.server.call_tool()
        async def extract_video_content(arguments: dict) -> CallToolResult:
            """Extract comprehensive content from video URL including transcript, metadata, and analysis"""
            try:
                video_url = arguments.get("video_url")
                languages = arguments.get("languages", ["en"])
                
                if not video_url:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: video_url is required")]
                    )
                
                logger.info(f"Extracting video content from: {video_url}")
                video_content = await self.video_extractor.process_video(video_url, languages)
                
                # Cache the result
                cache_key = f"video_content_{hash(video_url)}"
                self.processing_cache[cache_key] = video_content
                
                # Create response
                response = {
                    "video_id": video_content.metadata.video_id,
                    "title": video_content.metadata.title,
                    "duration": video_content.metadata.duration,
                    "transcript_segments": len(video_content.transcript) if video_content.transcript else 0,
                    "summary": video_content.summary,
                    "key_points": video_content.key_points,
                    "topics": video_content.topics,
                    "cache_key": cache_key
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response, indent=2))]
                )
            
            except Exception as e:
                logger.error(f"Video extraction failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        @self.server.call_tool()
        async def get_youtube_transcript(arguments: dict) -> CallToolResult:
            """Extract transcript from YouTube video with detailed timing information"""
            try:
                video_url = arguments.get("video_url")
                languages = arguments.get("languages", ["en"])
                
                if not video_url:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: video_url is required")]
                    )
                
                logger.info(f"Extracting transcript from: {video_url}")
                transcript = await self.video_extractor.extract_transcript(video_url, languages)
                
                if not transcript:
                    return CallToolResult(
                        content=[TextContent(type="text", text="No transcript available for this video")]
                    )
                
                # Format transcript with timing
                formatted_transcript = []
                for segment in transcript:
                    formatted_transcript.append({
                        "start": segment.start,
                        "end": segment.end,
                        "duration": segment.duration,
                        "text": segment.text
                    })
                
                response = {
                    "transcript_segments": len(formatted_transcript),
                    "total_duration": transcript[-1].end if transcript else 0,
                    "transcript": formatted_transcript
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response, indent=2))]
                )
            
            except Exception as e:
                logger.error(f"Transcript extraction failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        # NotebookLM-style processing tools
        @self.server.call_tool()
        async def create_video_notebook(arguments: dict) -> CallToolResult:
            """Create a NotebookLM-style notebook with AI-generated insights from video content"""
            try:
                video_url = arguments.get("video_url")
                languages = arguments.get("languages", ["en"])
                export_format = arguments.get("format", "markdown")
                
                if not video_url:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: video_url is required")]
                    )
                
                logger.info(f"Creating notebook for video: {video_url}")
                notebook = await self.notebook_processor.process_video_to_notebook(video_url, languages)
                
                # Export notebook
                output_file = self.notebook_processor.export_notebook(notebook, export_format)
                
                # Create summary response
                response = {
                    "video_title": notebook.video_metadata.title,
                    "executive_summary": notebook.executive_summary,
                    "key_insights_count": len(notebook.key_insights),
                    "questions_count": len(notebook.questions_raised),
                    "action_items_count": len(notebook.action_items),
                    "notebook_entries_count": len(notebook.notebook_entries),
                    "exported_file": output_file,
                    "processing_time": notebook.processing_metadata.get('processing_duration', 0)
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response, indent=2))]
                )
            
            except Exception as e:
                logger.error(f"Notebook creation failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        @self.server.call_tool()
        async def get_video_insights(arguments: dict) -> CallToolResult:
            """Extract key insights and actionable items from video content"""
            try:
                video_url = arguments.get("video_url")
                languages = arguments.get("languages", ["en"])
                
                if not video_url:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: video_url is required")]
                    )
                
                logger.info(f"Extracting insights from: {video_url}")
                notebook = await self.notebook_processor.process_video_to_notebook(video_url, languages)
                
                response = {
                    "video_title": notebook.video_metadata.title,
                    "executive_summary": notebook.executive_summary,
                    "key_insights": notebook.key_insights,
                    "main_topics": notebook.main_topics,
                    "questions_raised": notebook.questions_raised,
                    "action_items": notebook.action_items,
                    "concept_map": notebook.concept_map
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response, indent=2))]
                )
            
            except Exception as e:
                logger.error(f"Insights extraction failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        # VideoPrism-style analysis tools
        @self.server.call_tool()
        async def analyze_video_content(arguments: dict) -> CallToolResult:
            """Perform comprehensive VideoPrism-style analysis including visual content, categorization, and audience analysis"""
            try:
                video_url = arguments.get("video_url")
                languages = arguments.get("languages", ["en"])
                export_format = arguments.get("format", "json")
                
                if not video_url:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: video_url is required")]
                    )
                
                logger.info(f"Analyzing video content: {video_url}")
                analysis = await self.videoprism_analyzer.analyze_video(video_url, languages)
                
                # Export analysis
                output_file = self.videoprism_analyzer.export_analysis(analysis, export_format)
                
                # Create summary response
                response = {
                    "video_title": analysis.video_metadata.title,
                    "primary_category": analysis.content_category.primary_category,
                    "target_audience": analysis.audience_analysis.target_age_group,
                    "complexity_scores": {
                        "visual": analysis.video_complexity.visual_complexity,
                        "audio": analysis.video_complexity.audio_complexity,
                        "content": analysis.video_complexity.content_complexity,
                        "production_quality": analysis.video_complexity.production_quality
                    },
                    "frames_analyzed": len(analysis.visual_analysis),
                    "key_moments_count": len(analysis.key_moments),
                    "content_themes": analysis.content_themes,
                    "exported_file": output_file,
                    "analysis_duration": analysis.analysis_metadata.get('analysis_duration', 0)
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response, indent=2))]
                )
            
            except Exception as e:
                logger.error(f"Video analysis failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        @self.server.call_tool()
        async def categorize_video(arguments: dict) -> CallToolResult:
            """Categorize video content and identify target audience"""
            try:
                video_url = arguments.get("video_url")
                languages = arguments.get("languages", ["en"])
                
                if not video_url:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: video_url is required")]
                    )
                
                logger.info(f"Categorizing video: {video_url}")
                analysis = await self.videoprism_analyzer.analyze_video(video_url, languages)
                
                response = {
                    "video_title": analysis.video_metadata.title,
                    "content_category": {
                        "primary": analysis.content_category.primary_category,
                        "subcategories": analysis.content_category.subcategories,
                        "confidence_scores": analysis.content_category.confidence_scores,
                        "reasoning": analysis.content_category.reasoning,
                        "tags": analysis.content_category.content_tags
                    },
                    "audience_analysis": {
                        "target_age_group": analysis.audience_analysis.target_age_group,
                        "education_level": analysis.audience_analysis.education_level,
                        "expertise_level": analysis.audience_analysis.expertise_level,
                        "engagement_factors": analysis.audience_analysis.engagement_factors,
                        "accessibility_score": analysis.audience_analysis.accessibility_score,
                        "content_appropriateness": analysis.audience_analysis.content_appropriateness
                    }
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response, indent=2))]
                )
            
            except Exception as e:
                logger.error(f"Video categorization failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        # Combined processing tools
        @self.server.call_tool()
        async def process_video_complete(arguments: dict) -> CallToolResult:
            """Complete video processing pipeline: extraction, notebook creation, and analysis"""
            try:
                video_url = arguments.get("video_url")
                languages = arguments.get("languages", ["en"])
                include_notebook = arguments.get("include_notebook", True)
                include_analysis = arguments.get("include_analysis", True)
                
                if not video_url:
                    return CallToolResult(
                        content=[TextContent(type="text", text="Error: video_url is required")]
                    )
                
                logger.info(f"Starting complete processing for: {video_url}")
                start_time = datetime.now()
                
                results = {
                    "video_url": video_url,
                    "processing_started": start_time.isoformat()
                }
                
                # Step 1: Extract video content
                logger.info("Step 1: Extracting video content...")
                video_content = await self.video_extractor.process_video(video_url, languages)
                results["video_extraction"] = {
                    "title": video_content.metadata.title,
                    "duration": video_content.metadata.duration,
                    "transcript_segments": len(video_content.transcript) if video_content.transcript else 0,
                    "topics": video_content.topics
                }
                
                # Step 2: Create notebook if requested
                if include_notebook:
                    logger.info("Step 2: Creating NotebookLM-style notebook...")
                    notebook = await self.notebook_processor.process_video_to_notebook(video_url, languages)
                    notebook_file = self.notebook_processor.export_notebook(notebook, "markdown")
                    results["notebook"] = {
                        "insights_count": len(notebook.key_insights),
                        "questions_count": len(notebook.questions_raised),
                        "action_items_count": len(notebook.action_items),
                        "exported_file": notebook_file
                    }
                
                # Step 3: Perform VideoPrism analysis if requested
                if include_analysis:
                    logger.info("Step 3: Performing VideoPrism analysis...")
                    analysis = await self.videoprism_analyzer.analyze_video(video_url, languages)
                    analysis_file = self.videoprism_analyzer.export_analysis(analysis, "json")
                    results["analysis"] = {
                        "primary_category": analysis.content_category.primary_category,
                        "target_audience": analysis.audience_analysis.target_age_group,
                        "complexity_visual": analysis.video_complexity.visual_complexity,
                        "complexity_content": analysis.video_complexity.content_complexity,
                        "frames_analyzed": len(analysis.visual_analysis),
                        "exported_file": analysis_file
                    }
                
                # Final results
                processing_time = (datetime.now() - start_time).total_seconds()
                results["processing_completed"] = datetime.now().isoformat()
                results["total_processing_time"] = processing_time
                
                logger.info(f"Complete processing finished in {processing_time:.2f}s")
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(results, indent=2))]
                )
            
            except Exception as e:
                logger.error(f"Complete processing failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        # Utility tools
        @self.server.call_tool()
        async def get_processing_status(arguments: dict) -> CallToolResult:
            """Get status of processing operations and cached results"""
            try:
                cache_info = {
                    "cached_items": len(self.processing_cache),
                    "cache_keys": list(self.processing_cache.keys()),
                    "server_status": "running",
                    "available_processors": {
                        "video_extractor": True,
                        "notebook_processor": self.notebook_processor.ai_available if hasattr(self.notebook_processor, 'ai_available') else False,
                        "videoprism_analyzer": self.videoprism_analyzer.cv_available if hasattr(self.videoprism_analyzer, 'cv_available') else False
                    }
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(cache_info, indent=2))]
                )
            
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        @self.server.call_tool()
        async def clear_processing_cache(arguments: dict) -> CallToolResult:
            """Clear processing cache and temporary files"""
            try:
                cache_count = len(self.processing_cache)
                self.processing_cache.clear()
                
                # Clean up temporary files
                temp_dirs = ["/tmp/videoprism_analysis", "/tmp/video_processing"]
                cleaned_files = 0
                
                for temp_dir in temp_dirs:
                    temp_path = Path(temp_dir)
                    if temp_path.exists():
                        for file_path in temp_path.glob("*"):
                            try:
                                file_path.unlink()
                                cleaned_files += 1
                            except Exception as e:
                                logger.warning(f"Failed to delete {file_path}: {e}")
                
                result = {
                    "cache_items_cleared": cache_count,
                    "temp_files_cleaned": cleaned_files,
                    "status": "success"
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )
            
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        logger.info("All tools registered successfully")
    
    def _register_prompts(self):
        """Register prompts for the MCP server"""
        if not self.server:
            return
        
        @self.server.get_prompt()
        async def video_analysis_prompt(arguments: dict) -> GetPromptResult:
            """Generate analysis prompt for video content"""
            video_url = arguments.get("video_url", "")
            analysis_type = arguments.get("analysis_type", "comprehensive")
            
            if analysis_type == "notebook":
                prompt_text = f"""
                Please create a comprehensive NotebookLM-style analysis of the video at: {video_url}
                
                Include:
                1. Executive summary of the main content
                2. Key insights and takeaways
                3. Discussion questions for deeper exploration
                4. Action items and practical applications
                5. Concept map showing relationships between topics
                
                Use the create_video_notebook tool to generate the analysis.
                """
            
            elif analysis_type == "categorization":
                prompt_text = f"""
                Please analyze and categorize the video at: {video_url}
                
                Provide:
                1. Content category and subcategories
                2. Target audience analysis (age, education, expertise level)
                3. Content complexity assessment
                4. Engagement factors and accessibility score
                5. Content appropriateness evaluation
                
                Use the categorize_video tool to perform this analysis.
                """
            
            else:  # comprehensive
                prompt_text = f"""
                Please perform a complete analysis of the video at: {video_url}
                
                This should include:
                1. Video content extraction with transcript
                2. NotebookLM-style note generation with insights
                3. VideoPrism-style content analysis and categorization
                4. Visual content analysis (if applicable)
                5. Target audience and complexity assessment
                
                Use the process_video_complete tool to run the full pipeline.
                """
            
            return GetPromptResult(
                description=f"Video analysis prompt for {analysis_type} analysis",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=prompt_text)
                    )
                ]
            )
        
        @self.server.get_prompt()
        async def video_extraction_prompt(arguments: dict) -> GetPromptResult:
            """Generate prompt for video content extraction"""
            video_url = arguments.get("video_url", "")
            
            prompt_text = f"""
            Please extract comprehensive content from the video at: {video_url}
            
            Extract:
            1. Video metadata (title, duration, description)
            2. Full transcript with timing information
            3. Key topics and themes
            4. Summary and key points
            5. Any available captions or subtitles
            
            Use the extract_video_content tool to perform this extraction.
            """
            
            return GetPromptResult(
                description="Video content extraction prompt",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=prompt_text)
                    )
                ]
            )
        
        logger.info("Prompts registered successfully")
    
    async def run_standalone_demo(self):
        """Run a standalone demo of the video processing capabilities"""
        logger.info("Running standalone demo...")
        
        # Test video URL (replace with actual video)
        test_url = "https://www.youtube.com/watch?v=C0uk2ZcOliw" # Using a new, valid video URL
        
        try:
            # Test video extraction
            logger.info("Testing video extraction...")
            video_content = await self.video_extractor.process_video(test_url, ["en"])
            print(f"✓ Video extracted: {video_content.metadata.title}")
            
            # Test notebook creation (if AI components available)
            if hasattr(self.notebook_processor, 'ai_available') and self.notebook_processor.ai_available:
                logger.info("Testing notebook creation...")
                notebook = await self.notebook_processor.process_video_to_notebook(test_url, ["en"])
                notebook_file = self.notebook_processor.export_notebook(notebook, "markdown")
                print(f"✓ Notebook created: {notebook_file}")
            else:
                print("⚠ Notebook creation skipped - AI components not available")
            
            # Test VideoPrism analysis (if CV components available)
            if hasattr(self.videoprism_analyzer, 'cv_available') and self.videoprism_analyzer.cv_available:
                logger.info("Testing VideoPrism analysis...")
                analysis = await self.videoprism_analyzer.analyze_video(test_url, ["en"])
                analysis_file = self.videoprism_analyzer.export_analysis(analysis, "json")
                print(f"✓ Analysis completed: {analysis_file}")
            else:
                print("⚠ VideoPrism analysis skipped - CV components not available")
            
            print("\n🎉 All available components tested successfully!")
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            print(f"❌ Demo failed: {e}")
    
    async def run_server(self):
        """Run the MCP server"""
        if not self.server:
            logger.error("MCP server not available")
            await self.run_standalone_demo()
            return
        
        logger.info("Starting Enhanced MCP Server...")
        
        # Import and run MCP server
        try:
            from mcp.server.stdio import stdio_server
            
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Server failed to start: {e}")
            traceback.print_exc()

# Standalone functions for direct usage
async def extract_video_content_standalone(video_url: str, languages: List[str] = None) -> VideoContent:
    """Standalone function to extract video content"""
    extractor = EnhancedVideoExtractor()
    return await extractor.process_video(video_url, languages or ["en"])

async def create_video_notebook_standalone(video_url: str, languages: List[str] = None, export_format: str = "markdown") -> str:
    """Standalone function to create video notebook"""
    processor = NotebookLMProcessor()
    notebook = await processor.process_video_to_notebook(video_url, languages or ["en"])
    return processor.export_notebook(notebook, export_format)

async def analyze_video_standalone(video_url: str, languages: List[str] = None, export_format: str = "json") -> str:
    """Standalone function to analyze video"""
    analyzer = VideoPrismAnalyzer()
    analysis = await analyzer.analyze_video(video_url, languages or ["en"])
    return analyzer.export_analysis(analysis, export_format)

async def process_video_complete_standalone(video_url: str, languages: List[str] = None) -> Dict[str, Any]:
    """Standalone function for complete video processing"""
    server = EnhancedMCPServer()
    
    results = {
        "video_url": video_url,
        "processing_started": datetime.now().isoformat()
    }
    
    try:
        # Extract video content
        video_content = await server.video_extractor.process_video(video_url, languages or ["en"])
        results["video_extraction"] = {
            "title": video_content.metadata.title,
            "duration": video_content.metadata.duration,
            "transcript_segments": len(video_content.transcript) if video_content.transcript else 0
        }
        
        # Create notebook if AI available
        if hasattr(server.notebook_processor, 'ai_available') and server.notebook_processor.ai_available:
            notebook = await server.notebook_processor.process_video_to_notebook(video_url, languages or ["en"])
            notebook_file = server.notebook_processor.export_notebook(notebook, "markdown")
            results["notebook_file"] = notebook_file
        
        # Perform analysis if CV available
        if hasattr(server.videoprism_analyzer, 'cv_available') and server.videoprism_analyzer.cv_available:
            analysis = await server.videoprism_analyzer.analyze_video(video_url, languages or ["en"])
            analysis_file = server.videoprism_analyzer.export_analysis(analysis, "json")
            results["analysis_file"] = analysis_file
        
        results["status"] = "success"
        results["processing_completed"] = datetime.now().isoformat()
        
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
    
    return results

# Main execution
async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced MCP Server for Video Processing")
    parser.add_argument("--mode", choices=["server", "demo", "extract", "notebook", "analyze", "complete"], 
                       default="server", help="Operation mode")
    parser.add_argument("--video-url", help="Video URL for processing")
    parser.add_argument("--languages", nargs="+", default=["en"], help="Languages for transcript extraction")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Output format")
    
    args = parser.parse_args()
    
    if args.mode == "server":
        server = EnhancedMCPServer()
        await server.run_server()
    
    elif args.mode == "demo":
        server = EnhancedMCPServer()
        await server.run_standalone_demo()
    
    elif args.mode == "extract" and args.video_url:
        result = await extract_video_content_standalone(args.video_url, args.languages)
        print(json.dumps(asdict(result), indent=2, default=str))
    
    elif args.mode == "notebook" and args.video_url:
        output_file = await create_video_notebook_standalone(args.video_url, args.languages, args.format)
        print(f"Notebook created: {output_file}")
    
    elif args.mode == "analyze" and args.video_url:
        output_file = await analyze_video_standalone(args.video_url, args.languages, args.format)
        print(f"Analysis completed: {output_file}")
    
    elif args.mode == "complete" and args.video_url:
        results = await process_video_complete_standalone(args.video_url, args.languages)
        print(json.dumps(results, indent=2))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())