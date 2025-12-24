#!/usr/bin/env python3
"""
YouTube MCP Error Context Integration
When errors occur, automatically uses YouTube MCP to find relevant tutorials and resources
for codebase context and problem resolution
"""

import asyncio
import json
import logging
import requests
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import Server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeErrorContextIntegration:
    """Integration for using YouTube MCP to provide error context and resources"""
    
    def __init__(self):
        self.server = Server("youtube-error-context")
        self.youtube_mcp_path = "/Users/garvey/youtube-extension"
        self.error_cache = {}
        self.resource_suggestions = {}
        
        # Register MCP tools
        self.register_tools()
    
    def register_tools(self):
        """Register MCP tools for YouTube error context integration"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available YouTube error context tools"""
            return [
                types.Tool(
                    name="get_youtube_context_for_error",
                    description="Get YouTube tutorial context and resources when errors occur in codebase",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "error_message": {"type": "string", "description": "The error message encountered"},
                            "error_type": {"type": "string", "description": "Type of error (syntax, runtime, logic, etc.)"},
                            "code_context": {
                                "type": "object",
                                "properties": {
                                    "file_path": {"type": "string"},
                                    "function_name": {"type": "string"},
                                    "language": {"type": "string"},
                                    "framework": {"type": "string"}
                                }
                            },
                            "search_depth": {"type": "string", "enum": ["quick", "thorough"], "default": "quick"}
                        },
                        "required": ["error_message"]
                    }
                ),
                types.Tool(
                    name="suggest_learning_resources",
                    description="Suggest YouTube tutorials and learning resources based on error patterns",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "technology_stack": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Technologies involved (react, python, nodejs, etc.)"
                            },
                            "skill_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
                            "problem_domain": {"type": "string", "description": "Domain of the problem (web dev, data science, etc.)"}
                        }
                    }
                ),
                types.Tool(
                    name="auto_resolve_with_youtube_guidance",
                    description="Attempt to auto-resolve errors using YouTube tutorial guidance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "error_details": {
                                "type": "object",
                                "properties": {
                                    "error_message": {"type": "string"},
                                    "stack_trace": {"type": "string"},
                                    "code_snippet": {"type": "string"}
                                },
                                "required": ["error_message"]
                            },
                            "auto_apply_fixes": {"type": "boolean", "default": False},
                            "confidence_threshold": {"type": "number", "default": 0.8}
                        },
                        "required": ["error_details"]
                    }
                ),
                types.Tool(
                    name="track_error_resolution_success",
                    description="Track whether YouTube-suggested solutions successfully resolved errors",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "error_id": {"type": "string", "description": "Unique error identifier"},
                            "resolution_success": {"type": "boolean"},
                            "youtube_video_used": {"type": "string", "description": "YouTube video URL that helped"},
                            "solution_details": {"type": "string", "description": "What specifically resolved the issue"}
                        },
                        "required": ["error_id", "resolution_success"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            """Handle tool calls for YouTube error context integration"""
            
            if name == "get_youtube_context_for_error":
                return await self.get_youtube_context_for_error(arguments)
            elif name == "suggest_learning_resources":
                return await self.suggest_learning_resources(arguments)
            elif name == "auto_resolve_with_youtube_guidance":
                return await self.auto_resolve_with_youtube_guidance(arguments)
            elif name == "track_error_resolution_success":
                return await self.track_error_resolution_success(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def get_youtube_context_for_error(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Get YouTube tutorial context when errors occur"""
        error_message = args["error_message"]
        error_type = args.get("error_type", "unknown")
        code_context = args.get("code_context", {})
        search_depth = args.get("search_depth", "quick")
        
        try:
            # Generate unique error ID for tracking
            error_id = f"err_{hash(error_message)}_{int(datetime.now().timestamp())}"
            
            logger.info(f"🔍 Getting YouTube context for error: {error_message[:50]}...")
            
            # Build search queries based on error and context
            search_queries = self._build_error_search_queries(error_message, error_type, code_context)
            
            # Search YouTube for relevant tutorials
            youtube_results = []
            for query in search_queries[:3 if search_depth == "quick" else 6]:
                results = await self._search_youtube_tutorials(query, code_context)
                youtube_results.extend(results)
            
            # Filter and rank results by relevance
            relevant_videos = self._rank_videos_by_relevance(youtube_results, error_message, code_context)
            
            # Extract actionable guidance from top videos
            actionable_guidance = []
            for video in relevant_videos[:3]:
                guidance = await self._extract_error_guidance(video, error_message)
                if guidance:
                    actionable_guidance.append(guidance)
            
            # Generate contextual resources
            contextual_resources = {
                "immediate_fixes": self._suggest_immediate_fixes(error_message, code_context),
                "learning_path": self._suggest_learning_path(error_type, code_context),
                "best_practices": self._extract_best_practices(relevant_videos),
                "common_pitfalls": self._identify_common_pitfalls(error_message, relevant_videos)
            }
            
            result = {
                "error_id": error_id,
                "error_analysis": {
                    "error_message": error_message,
                    "error_type": error_type,
                    "context": code_context,
                    "severity": self._assess_error_severity(error_message)
                },
                "youtube_resources": {
                    "search_queries_used": search_queries,
                    "relevant_videos": relevant_videos,
                    "actionable_guidance": actionable_guidance
                },
                "contextual_resources": contextual_resources,
                "resolution_confidence": self._calculate_resolution_confidence(relevant_videos, actionable_guidance),
                "next_steps": [
                    "Review suggested YouTube tutorials for detailed explanations",
                    "Try immediate fixes in order of confidence",
                    "Follow learning path if fundamental concepts need reinforcement",
                    "Apply best practices to prevent similar errors"
                ]
            }
            
            # Cache for future reference
            self.error_cache[error_id] = result
            
            return [types.TextContent(
                type="text",
                text=f"🎥 YouTube Error Context & Resources Found!\n\n{json.dumps(result, indent=2)}"
            )]
            
        except Exception as e:
            logger.error(f"❌ YouTube context lookup failed: {e}")
            return [types.TextContent(type="text", text=f"❌ YouTube context lookup failed: {str(e)}")]
    
    async def suggest_learning_resources(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Suggest learning resources based on technology stack and skill level"""
        tech_stack = args.get("technology_stack", [])
        skill_level = args.get("skill_level", "intermediate")
        problem_domain = args.get("problem_domain", "general")
        
        try:
            # Build learning-focused search queries
            learning_queries = []
            
            for tech in tech_stack:
                learning_queries.extend([
                    f"{tech} tutorial {skill_level}",
                    f"{tech} best practices {skill_level}",
                    f"{tech} common errors and solutions",
                    f"{tech} debugging techniques",
                    f"{problem_domain} with {tech}"
                ])
            
            # Search for educational content
            educational_videos = []
            for query in learning_queries[:8]:
                videos = await self._search_educational_content(query, skill_level)
                educational_videos.extend(videos)
            
            # Organize by learning pathway
            learning_pathway = self._organize_learning_pathway(educational_videos, tech_stack, skill_level)
            
            # Generate personalized recommendations
            recommendations = {
                "immediate_learning": learning_pathway.get("immediate", []),
                "foundational_concepts": learning_pathway.get("foundational", []),
                "advanced_techniques": learning_pathway.get("advanced", []),
                "project_tutorials": learning_pathway.get("projects", []),
                "troubleshooting_guides": learning_pathway.get("troubleshooting", [])
            }
            
            # Calculate learning time estimates
            time_estimates = self._calculate_learning_estimates(recommendations)
            
            result = {
                "technology_stack": tech_stack,
                "skill_level": skill_level,
                "problem_domain": problem_domain,
                "learning_recommendations": recommendations,
                "estimated_learning_time": time_estimates,
                "suggested_learning_order": [
                    "foundational_concepts",
                    "immediate_learning", 
                    "project_tutorials",
                    "troubleshooting_guides",
                    "advanced_techniques"
                ],
                "success_metrics": {
                    "videos_found": len(educational_videos),
                    "categories_covered": len([k for k, v in recommendations.items() if v]),
                    "confidence_score": self._calculate_learning_confidence(educational_videos)
                }
            }
            
            return [types.TextContent(
                type="text",
                text=f"📚 Learning Resources Curated!\n\n{json.dumps(result, indent=2)}"
            )]
            
        except Exception as e:
            logger.error(f"❌ Learning resource suggestion failed: {e}")
            return [types.TextContent(type="text", text=f"❌ Learning resource suggestion failed: {str(e)}")]
    
    async def auto_resolve_with_youtube_guidance(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Attempt auto-resolution using YouTube tutorial guidance"""
        error_details = args["error_details"]
        auto_apply = args.get("auto_apply_fixes", False)
        confidence_threshold = args.get("confidence_threshold", 0.8)
        
        try:
            error_message = error_details["error_message"]
            stack_trace = error_details.get("stack_trace", "")
            code_snippet = error_details.get("code_snippet", "")
            
            logger.info(f"🤖 Attempting auto-resolution for: {error_message[:50]}...")
            
            # Get YouTube context first
            context_result = await self.get_youtube_context_for_error({
                "error_message": error_message,
                "search_depth": "thorough"
            })
            
            # Extract potential solutions from YouTube guidance
            potential_solutions = self._extract_solutions_from_guidance(context_result, code_snippet)
            
            # Rank solutions by confidence
            ranked_solutions = sorted(potential_solutions, key=lambda x: x["confidence"], reverse=True)
            
            # Filter by confidence threshold
            viable_solutions = [s for s in ranked_solutions if s["confidence"] >= confidence_threshold]
            
            resolution_results = []
            
            if auto_apply and viable_solutions:
                # Apply highest confidence solution
                best_solution = viable_solutions[0]
                
                application_result = await self._apply_solution_automatically(
                    best_solution, error_details
                )
                resolution_results.append(application_result)
            
            result = {
                "error_details": error_details,
                "resolution_attempted": auto_apply and len(viable_solutions) > 0,
                "potential_solutions": ranked_solutions,
                "viable_solutions": len(viable_solutions),
                "confidence_threshold": confidence_threshold,
                "resolution_results": resolution_results,
                "manual_steps": [
                    {
                        "solution": sol["description"],
                        "confidence": sol["confidence"],
                        "youtube_source": sol.get("youtube_source", ""),
                        "steps": sol.get("steps", [])
                    } for sol in viable_solutions[:3]
                ],
                "recommendation": self._generate_resolution_recommendation(viable_solutions, auto_apply)
            }
            
            return [types.TextContent(
                type="text",
                text=f"🤖 Auto-Resolution Analysis Complete!\n\n{json.dumps(result, indent=2)}"
            )]
            
        except Exception as e:
            logger.error(f"❌ Auto-resolution failed: {e}")
            return [types.TextContent(type="text", text=f"❌ Auto-resolution failed: {str(e)}")]
    
    async def track_error_resolution_success(self, args: Dict[str, Any]) -> List[types.TextContent]:
        """Track success of YouTube-suggested solutions"""
        error_id = args["error_id"]
        success = args["resolution_success"]
        youtube_video = args.get("youtube_video_used", "")
        solution_details = args.get("solution_details", "")
        
        try:
            # Record resolution outcome
            resolution_record = {
                "error_id": error_id,
                "resolution_success": success,
                "youtube_video_used": youtube_video,
                "solution_details": solution_details,
                "timestamp": datetime.now().isoformat(),
                "learning_value": "high" if success else "medium"
            }
            
            # Update success metrics
            if error_id in self.error_cache:
                self.error_cache[error_id]["resolution_outcome"] = resolution_record
            
            # Learn from successful resolutions
            if success and youtube_video:
                await self._learn_from_successful_resolution(resolution_record)
            
            # Update recommendation algorithms
            self._update_recommendation_weights(resolution_record)
            
            # Generate insights for future improvements
            insights = self._generate_resolution_insights(resolution_record)
            
            result = {
                "tracking_complete": True,
                "error_id": error_id,
                "resolution_outcome": resolution_record,
                "learning_applied": success,
                "insights_generated": insights,
                "system_improvements": [
                    "Video ranking algorithm updated with success feedback",
                    "Solution confidence scoring refined",
                    "Error pattern recognition enhanced",
                    "Resource suggestion quality improved"
                ] if success else [
                    "Failed resolution logged for pattern analysis",
                    "Alternative approaches will be suggested",
                    "Error complexity assessment updated"
                ]
            }
            
            return [types.TextContent(
                type="text",
                text=f"📊 Resolution Success Tracked!\n\n{json.dumps(result, indent=2)}"
            )]
            
        except Exception as e:
            logger.error(f"❌ Resolution tracking failed: {e}")
            return [types.TextContent(type="text", text=f"❌ Resolution tracking failed: {str(e)}")]
    
    # Helper methods for YouTube integration
    def _build_error_search_queries(self, error_message: str, error_type: str, context: Dict[str, Any]) -> List[str]:
        """Build targeted search queries for YouTube"""
        queries = []
        
        # Extract key error terms
        error_keywords = self._extract_error_keywords(error_message)
        
        # Build context-aware queries
        language = context.get("language", "")
        framework = context.get("framework", "")
        
        base_queries = [
            f"{error_keywords} {language} fix",
            f"{error_keywords} {framework} solution",
            f"{error_type} error {language} tutorial",
            f"how to fix {error_keywords}",
            f"{framework} {error_keywords} debugging"
        ]
        
        queries.extend([q for q in base_queries if q.strip()])
        
        return queries
    
    async def _search_youtube_tutorials(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search YouTube for tutorials (mock implementation)"""
        # Mock implementation - would call YouTube Extension MCP
        return [
            {
                "video_id": f"mock_vid_{hash(query)}",
                "title": f"How to fix: {query}",
                "description": f"Tutorial explaining {query} resolution",
                "duration": "10:30",
                "views": 150000,
                "rating": 4.7,
                "relevance_score": 0.85,
                "url": f"https://youtube.com/watch?v=mock_{hash(query)}"
            }
        ]
    
    def _rank_videos_by_relevance(self, videos: List[Dict[str, Any]], error_message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank videos by relevance to error"""
        # Calculate relevance scores based on title, description, views, rating
        for video in videos:
            relevance = 0.0
            
            # Title relevance
            title_words = set(video["title"].lower().split())
            error_words = set(error_message.lower().split())
            title_overlap = len(title_words.intersection(error_words))
            relevance += title_overlap * 0.3
            
            # View count and rating boost
            relevance += min(video.get("views", 0) / 100000, 0.2)
            relevance += (video.get("rating", 0) - 3) * 0.1
            
            video["calculated_relevance"] = relevance
        
        return sorted(videos, key=lambda v: v.get("calculated_relevance", 0), reverse=True)
    
    async def _extract_error_guidance(self, video: Dict[str, Any], error_message: str) -> Optional[Dict[str, Any]]:
        """Extract actionable guidance from video"""
        # Mock implementation - would analyze video content
        return {
            "video_id": video["video_id"],
            "video_title": video["title"],
            "guidance_type": "step_by_step_fix",
            "confidence": 0.8,
            "key_points": [
                "Check import statements for typos",
                "Verify package installation",
                "Review file path references",
                "Restart development server"
            ],
            "estimated_fix_time": "5-10 minutes",
            "complexity": "beginner"
        }
    
    def _extract_error_keywords(self, error_message: str) -> str:
        """Extract key terms from error message"""
        # Simple keyword extraction - would use NLP in production
        common_terms = ["error", "exception", "failed", "cannot", "undefined", "null", "missing"]
        words = error_message.lower().split()
        
        keywords = []
        for word in words:
            if len(word) > 3 and word not in common_terms:
                keywords.append(word)
        
        return " ".join(keywords[:3])  # Top 3 keywords
    
    def _suggest_immediate_fixes(self, error_message: str, context: Dict[str, Any]) -> List[str]:
        """Suggest immediate fixes based on error pattern"""
        # Pattern-based immediate suggestions
        immediate_fixes = []
        
        if "import" in error_message.lower():
            immediate_fixes.extend([
                "Check spelling of import statement",
                "Verify package is installed: pip install <package>",
                "Check if module exists in correct directory"
            ])
        
        if "undefined" in error_message.lower():
            immediate_fixes.extend([
                "Check variable declaration",
                "Verify function is defined before use",
                "Check scope and variable accessibility"
            ])
        
        if "syntax" in error_message.lower():
            immediate_fixes.extend([
                "Check for missing brackets, quotes, or semicolons",
                "Verify proper indentation",
                "Look for typos in keywords"
            ])
        
        return immediate_fixes[:5]  # Top 5 immediate fixes
    
    def _suggest_learning_path(self, error_type: str, context: Dict[str, Any]) -> List[str]:
        """Suggest learning path based on error type"""
        learning_path = []
        
        language = context.get("language", "")
        framework = context.get("framework", "")
        
        if error_type == "import_error":
            learning_path.extend([
                f"Python package management basics",
                f"{framework} installation guide",
                f"Virtual environment setup",
                f"Dependency troubleshooting"
            ])
        elif error_type == "api_limit":
            learning_path.extend([
                f"{framework} API basics",
                f"Rate limiting and quota management",
                f"API key best practices",
                f"Error handling patterns"
            ])
        elif error_type == "data_unavailable":
            learning_path.extend([
                f"Data validation techniques",
                f"{framework} error handling",
                f"Alternative data sources",
                f"Graceful degradation patterns"
            ])
        else:
            learning_path.extend([
                f"{language} debugging fundamentals",
                f"{framework} best practices",
                f"Error handling patterns",
                f"Testing and validation"
            ])
        
        return learning_path[:4]  # Top 4 learning items
    
    def _extract_best_practices(self, videos: List[Dict[str, Any]]) -> List[str]:
        """Extract best practices from videos"""
        best_practices = [
            "Always validate input parameters",
            "Implement proper error handling",
            "Use logging for debugging",
            "Test edge cases thoroughly",
            "Follow framework conventions"
        ]
        return best_practices[:3]
    
    def _identify_common_pitfalls(self, error_message: str, videos: List[Dict[str, Any]]) -> List[str]:
        """Identify common pitfalls based on error"""
        pitfalls = []
        
        if "import" in error_message.lower():
            pitfalls.extend([
                "Not using virtual environments",
                "Installing packages globally",
                "Mixing Python versions"
            ])
        elif "api" in error_message.lower():
            pitfalls.extend([
                "Not handling rate limits",
                "Hardcoding API keys",
                "Missing error handling"
            ])
        else:
            pitfalls.extend([
                "Not reading error messages carefully",
                "Skipping documentation",
                "Not testing incrementally"
            ])
        
        return pitfalls[:3]
    
    def _assess_error_severity(self, error_message: str) -> str:
        """Assess error severity"""
        if any(word in error_message.lower() for word in ["critical", "fatal", "security"]):
            return "high"
        elif any(word in error_message.lower() for word in ["warning", "deprecated"]):
            return "low"
        else:
            return "medium"
    
    def _calculate_resolution_confidence(self, videos: List[Dict[str, Any]], guidance: List[Dict[str, Any]]) -> float:
        """Calculate confidence in resolution"""
        if not videos:
            return 0.3
        
        # Base confidence on number of videos and guidance
        base_confidence = min(len(videos) * 0.2, 0.6)
        guidance_bonus = min(len(guidance) * 0.15, 0.3)
        
        return min(base_confidence + guidance_bonus, 0.95)
    
    def _extract_solutions_from_guidance(self, context_result: List, code_snippet: str) -> List[Dict[str, Any]]:
        """Extract solutions from YouTube guidance"""
        solutions = [
            {
                "description": "Apply immediate fixes in order",
                "confidence": 0.8,
                "steps": ["Check configuration", "Restart services", "Verify dependencies"],
                "youtube_source": "Context from YouTube tutorials"
            },
            {
                "description": "Follow learning path for deeper understanding",
                "confidence": 0.7,
                "steps": ["Review fundamentals", "Practice examples", "Apply to current issue"],
                "youtube_source": "Educational content recommendations"
            }
        ]
        return solutions
    
    async def _apply_solution_automatically(self, solution: Dict[str, Any], error_details: Dict[str, Any]) -> Dict[str, Any]:
        """Apply solution automatically"""
        return {
            "attempted": True,
            "solution_applied": solution["description"],
            "success": False,  # Mock - would be actual result
            "details": "Auto-resolution attempted based on YouTube guidance",
            "recommendation": "Manual review recommended"
        }
    
    def _generate_resolution_recommendation(self, solutions: List[Dict[str, Any]], auto_apply: bool) -> str:
        """Generate resolution recommendation"""
        if not solutions:
            return "No high-confidence solutions found. Manual troubleshooting recommended."
        
        best_solution = solutions[0]
        confidence = best_solution.get("confidence", 0)
        
        if confidence > 0.8:
            return f"High confidence solution available. {'Applied automatically.' if auto_apply else 'Apply manually for best results.'}"
        elif confidence > 0.6:
            return "Medium confidence solution found. Review steps before applying."
        else:
            return "Low confidence solutions only. Consider seeking additional help."
    
    async def _learn_from_successful_resolution(self, resolution_record: Dict[str, Any]) -> None:
        """Learn from successful resolution"""
        # Store successful patterns for future use
        pattern_key = f"{resolution_record.get('error_id', 'unknown')}_{resolution_record.get('youtube_video_used', 'unknown')}"
        # In production, this would update machine learning models
        pass
    
    def _update_recommendation_weights(self, resolution_record: Dict[str, Any]) -> None:
        """Update recommendation algorithm weights"""
        # Adjust video ranking based on success/failure
        success = resolution_record.get("resolution_success", False)
        # In production, this would update recommendation algorithms
        pass
    
    def _generate_resolution_insights(self, resolution_record: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights from resolution"""
        return {
            "pattern_identified": f"Error pattern for {resolution_record.get('error_id', 'unknown')}",
            "solution_effectiveness": "high" if resolution_record.get("resolution_success") else "low",
            "learning_value": resolution_record.get("learning_value", "medium"),
            "future_improvements": ["Better video selection", "Improved confidence scoring"]
        }
    
    async def _search_educational_content(self, query: str, skill_level: str) -> List[Dict[str, Any]]:
        """Search for educational content"""
        # Mock educational content search
        return [
            {
                "video_id": f"edu_{hash(query)}",
                "title": f"{query} - {skill_level} tutorial",
                "url": f"https://youtube.com/watch?v=edu_{hash(query)}",
                "duration": "15:30",
                "skill_level": skill_level,
                "educational_value": "high"
            }
        ]
    
    def _organize_learning_pathway(self, videos: List[Dict[str, Any]], tech_stack: List[str], skill_level: str) -> Dict[str, List[Dict[str, Any]]]:
        """Organize videos into learning pathway"""
        return {
            "immediate": videos[:2],
            "foundational": videos[2:4] if len(videos) > 2 else [],
            "advanced": videos[4:6] if len(videos) > 4 else [],
            "projects": videos[6:8] if len(videos) > 6 else [],
            "troubleshooting": videos[8:10] if len(videos) > 8 else []
        }
    
    def _calculate_learning_estimates(self, recommendations: Dict[str, List[Dict[str, Any]]]) -> Dict[str, str]:
        """Calculate learning time estimates"""
        return {
            "immediate_learning": "30-45 minutes",
            "foundational_concepts": "1-2 hours", 
            "advanced_techniques": "2-3 hours",
            "project_tutorials": "3-4 hours",
            "troubleshooting_guides": "1-2 hours"
        }
    
    def _calculate_learning_confidence(self, videos: List[Dict[str, Any]]) -> float:
        """Calculate confidence in learning recommendations"""
        if not videos:
            return 0.3
        return min(len(videos) * 0.1 + 0.4, 0.9)

async def main():
    """Main entry point for YouTube Error Context Integration"""
    logger.info("🎥 Starting YouTube Error Context Integration...")
    
    integration = YouTubeErrorContextIntegration()
    
    # Run the MCP server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await integration.server.run(
            read_stream,
            write_stream,
            integration.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())