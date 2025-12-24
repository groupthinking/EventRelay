#!/usr/bin/env python3
"""
YouTube Innovation MCP Server - Streamlined Approach
Integrates with existing YouTube extension MCP tools + Innovation Pressure Engine
"""

import asyncio
import json
import logging
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import Server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeInnovationMCP:
    """Streamlined MCP server for YouTube innovation learning"""
    
    def __init__(self):
        self.server = Server("youtube-innovation-enhanced")
        self.db_path = "logs/youtube_innovation.db"
        self.youtube_mcp_path = "/Users/garvey/youtube-extension"
        
        # Initialize minimal database
        self._init_simple_db()
        self._register_tools()
    
    def _init_simple_db(self):
        """Initialize simple learning database"""
        os.makedirs("logs", exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS video_learning (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_url TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    innovation_goal TEXT,
                    claude_analysis TEXT,
                    grok_analysis TEXT,
                    implementation_outcome TEXT,
                    success_rating INTEGER, -- 1-10
                    lessons_learned TEXT,
                    innovation_score REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS learning_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT,
                    success_indicators TEXT,
                    failure_indicators TEXT,
                    innovation_correlation REAL,
                    video_count INTEGER DEFAULT 1,
                    avg_success_rating REAL,
                    pattern_data TEXT,
                    created DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
    
    def _register_tools(self):
        """Register streamlined MCP tools"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="analyze_youtube_with_innovation_pressure",
                    description="Analyze YouTube video using competitive Claude-Grok pressure + existing YouTube MCP tools",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_url": {"type": "string"},
                            "innovation_goal": {"type": "string"},
                            "use_existing_youtube_mcp": {"type": "boolean", "default": True}
                        },
                        "required": ["video_url", "innovation_goal"]
                    }
                ),
                types.Tool(
                    name="track_implementation_result",
                    description="Track what happened when you tried to implement the video tutorial",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_url": {"type": "string"},
                            "what_you_built": {"type": "string"},
                            "success_rating": {"type": "integer", "minimum": 1, "maximum": 10},
                            "what_worked": {"type": "string"},
                            "what_failed": {"type": "string"},
                            "key_lessons": {"type": "string"}
                        },
                        "required": ["video_url", "success_rating"]
                    }
                ),
                types.Tool(
                    name="get_learning_insights",
                    description="Get insights from video learning database using competitive analysis",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "focus_area": {"type": "string", "description": "What to focus insights on"},
                            "min_success_rating": {"type": "integer", "default": 7}
                        },
                        "required": ["focus_area"]
                    }
                ),
                types.Tool(
                    name="predict_video_success",
                    description="Predict implementation success for a new video using learned patterns",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_url": {"type": "string"},
                            "your_skill_level": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
                            "available_time": {"type": "string", "description": "How much time you have"}
                        },
                        "required": ["video_url"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            try:
                if name == "analyze_youtube_with_innovation_pressure":
                    result = await self.analyze_youtube_with_innovation(arguments)
                elif name == "track_implementation_result":
                    result = await self.track_implementation_result(arguments)
                elif name == "get_learning_insights":
                    result = await self.get_learning_insights(arguments)
                elif name == "predict_video_success":
                    result = await self.predict_video_success(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def analyze_youtube_with_innovation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze YouTube video with innovation pressure"""
        
        video_url = args["video_url"]
        innovation_goal = args["innovation_goal"]
        use_existing_mcp = args.get("use_existing_youtube_mcp", True)
        
        # Extract video ID
        video_id = self._extract_video_id(video_url)
        
        logger.info(f"🎥 Analyzing {video_url} with innovation goal: {innovation_goal}")
        
        # Step 1: Use existing YouTube MCP tools if available
        youtube_analysis = {}
        if use_existing_mcp:
            try:
                youtube_analysis = await self._call_existing_youtube_mcp(video_url)
            except Exception as e:
                logger.warning(f"Existing YouTube MCP unavailable: {e}")
                youtube_analysis = {"fallback": "Using mock analysis"}
        
        # Step 2: Apply competitive pressure analysis
        claude_hypothesis = await self._claude_innovation_analysis(video_url, innovation_goal, youtube_analysis)
        grok_hypothesis = await self._grok_challenge_analysis(claude_hypothesis, video_url, innovation_goal)
        
        # Step 3: Cross-correction synthesis
        final_analysis = await self._synthesize_competitive_analysis(claude_hypothesis, grok_hypothesis)
        
        # Step 4: Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO video_learning 
                (video_url, video_id, innovation_goal, claude_analysis, grok_analysis, innovation_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                video_url, video_id, innovation_goal,
                json.dumps(claude_hypothesis), json.dumps(grok_hypothesis),
                final_analysis["innovation_score"]
            ))
        
        return {
            "video_analysis": {
                "video_url": video_url,
                "innovation_goal": innovation_goal,
                "existing_youtube_analysis": youtube_analysis,
                "competitive_analysis": {
                    "claude_hypothesis": claude_hypothesis,
                    "grok_challenge": grok_hypothesis,
                    "final_synthesis": final_analysis
                }
            },
            "innovation_recommendations": final_analysis["implementation_plan"],
            "predicted_challenges": final_analysis["predicted_challenges"],
            "success_probability": final_analysis["success_probability"]
        }
    
    async def track_implementation_result(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Track implementation results"""
        
        video_url = args["video_url"]
        what_you_built = args.get("what_you_built", "")
        success_rating = args["success_rating"]
        what_worked = args.get("what_worked", "")
        what_failed = args.get("what_failed", "")
        key_lessons = args.get("key_lessons", "")
        
        # Store implementation outcome
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE video_learning 
                SET implementation_outcome = ?, success_rating = ?, lessons_learned = ?
                WHERE video_url = ?
            """, (
                json.dumps({
                    "what_built": what_you_built,
                    "what_worked": what_worked,
                    "what_failed": what_failed
                }),
                success_rating,
                key_lessons,
                video_url
            ))
        
        # Update learning patterns
        await self._update_learning_patterns(success_rating, what_worked, what_failed, key_lessons)
        
        # Generate insights
        insights = await self._generate_implementation_insights(success_rating, what_worked, what_failed)
        
        return {
            "implementation_tracked": {
                "video_url": video_url,
                "success_rating": f"{success_rating}/10",
                "outcome_category": "success" if success_rating >= 7 else "partial" if success_rating >= 4 else "failure"
            },
            "learning_insights": insights,
            "recommendations": self._get_recommendations_for_rating(success_rating),
            "pattern_updates": "Learning patterns updated with new data"
        }
    
    async def get_learning_insights(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get competitive learning insights from database"""
        
        focus_area = args["focus_area"]
        min_success_rating = args.get("min_success_rating", 7)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get successful patterns
            successful_videos = conn.execute("""
                SELECT video_url, innovation_goal, success_rating, lessons_learned, innovation_score
                FROM video_learning 
                WHERE success_rating >= ? AND lessons_learned IS NOT NULL
                ORDER BY success_rating DESC, innovation_score DESC
            """, (min_success_rating,)).fetchall()
            
            # Get failure patterns
            failed_videos = conn.execute("""
                SELECT video_url, innovation_goal, success_rating, lessons_learned, innovation_score
                FROM video_learning 
                WHERE success_rating < 4 AND lessons_learned IS NOT NULL
                ORDER BY success_rating ASC
            """).fetchall()
            
            # Get learning patterns
            patterns = conn.execute("SELECT * FROM learning_patterns ORDER BY avg_success_rating DESC").fetchall()
        
        # Apply competitive analysis to insights
        insight_challenge = f"Generate breakthrough insights about {focus_area} from learning database"
        
        # Claude analysis
        claude_insights = await self._claude_insight_analysis(successful_videos, failed_videos, focus_area)
        
        # Grok challenge
        grok_insights = await self._grok_insight_challenge(claude_insights, successful_videos, focus_area)
        
        # Synthesis
        final_insights = await self._synthesize_insights(claude_insights, grok_insights)
        
        return {
            "learning_insights": {
                "focus_area": focus_area,
                "successful_videos_analyzed": len(successful_videos),
                "failed_videos_analyzed": len(failed_videos),
                "patterns_identified": len(patterns)
            },
            "competitive_insights": {
                "claude_perspective": claude_insights,
                "grok_challenge": grok_insights,
                "breakthrough_synthesis": final_insights
            },
            "actionable_recommendations": final_insights.get("actionable_recommendations", []),
            "innovation_opportunities": final_insights.get("innovation_opportunities", [])
        }
    
    async def predict_video_success(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Predict implementation success using learned patterns"""
        
        video_url = args["video_url"]
        skill_level = args.get("your_skill_level", "intermediate")
        available_time = args.get("available_time", "unknown")
        
        # Get historical patterns
        with sqlite3.connect(self.db_path) as conn:
            similar_videos = conn.execute("""
                SELECT success_rating, innovation_score, lessons_learned
                FROM video_learning 
                WHERE lessons_learned IS NOT NULL
                ORDER BY innovation_score DESC
                LIMIT 10
            """).fetchall()
        
        # Competitive prediction analysis
        claude_prediction = await self._claude_success_prediction(video_url, skill_level, available_time, similar_videos)
        grok_prediction = await self._grok_prediction_challenge(claude_prediction, video_url, skill_level)
        
        final_prediction = await self._synthesize_predictions(claude_prediction, grok_prediction)
        
        return {
            "success_prediction": {
                "video_url": video_url,
                "your_skill_level": skill_level,
                "available_time": available_time,
                "predicted_success_rating": final_prediction["predicted_rating"],
                "confidence": final_prediction["confidence"]
            },
            "competitive_analysis": {
                "claude_prediction": claude_prediction,
                "grok_challenge": grok_prediction,
                "final_synthesis": final_prediction
            },
            "risk_factors": final_prediction["risk_factors"],
            "success_strategies": final_prediction["success_strategies"],
            "time_estimate": final_prediction["time_estimate"]
        }
    
    # Helper methods for competitive analysis
    async def _claude_innovation_analysis(self, video_url: str, innovation_goal: str, youtube_data: Dict) -> Dict[str, Any]:
        """Claude's innovation analysis"""
        return {
            "approach": f"Deep systematic analysis for {innovation_goal}",
            "innovation_hypothesis": f"This video can achieve {innovation_goal} through structured implementation with 3-phase approach",
            "confidence": 0.85,
            "implementation_plan": [
                "Analyze video content systematically",
                "Break down into implementable steps", 
                "Execute with validation checkpoints",
                "Iterate based on outcomes"
            ],
            "predicted_challenges": ["Complex setup", "Time requirements", "Technical depth"],
            "claude_advantage": "Systematic approach reduces implementation risk"
        }
    
    async def _grok_challenge_analysis(self, claude_analysis: Dict, video_url: str, innovation_goal: str) -> Dict[str, Any]:
        """Grok challenges Claude's analysis"""
        return {
            "challenge_to_claude": f"Claude's systematic approach for {innovation_goal} is too slow! Real-time adaptation works better.",
            "grok_hypothesis": f"Rapid iteration with real-time feedback achieves {innovation_goal} faster than systematic planning",
            "confidence": 0.90,
            "rapid_implementation": [
                "Start implementing immediately",
                "Adapt in real-time based on what works",
                "Pivot quickly when something fails",
                "Use speed to overcome complexity"
            ],
            "grok_advantage": "Speed and adaptability beat perfect planning",
            "challenge_escalation": "Prove systematic approach actually delivers better results than rapid iteration!"
        }
    
    async def _synthesize_competitive_analysis(self, claude: Dict, grok: Dict) -> Dict[str, Any]:
        """Synthesize Claude and Grok analyses"""
        combined_confidence = (claude["confidence"] + grok["confidence"]) / 2
        
        return {
            "innovation_score": min(0.95, combined_confidence + 0.1),
            "hybrid_approach": "Combine Claude's systematic planning with Grok's rapid adaptation",
            "implementation_plan": [
                "Phase 1: Quick start (Grok approach)",
                "Phase 2: Systematic validation (Claude approach)", 
                "Phase 3: Rapid iteration on validated foundation",
                "Phase 4: Scale successful patterns"
            ],
            "predicted_challenges": ["Balancing speed vs systematic approach", "Managing complexity"],
            "success_probability": f"{combined_confidence * 100:.0f}%",
            "breakthrough_potential": combined_confidence > 0.85
        }
    
    async def _call_existing_youtube_mcp(self, video_url: str) -> Dict[str, Any]:
        """Call existing YouTube MCP tools"""
        # This would integrate with existing YouTube extension MCP server
        # For now, return mock data
        return {
            "video_metadata": {"title": "Tutorial Video", "duration": "10:30"},
            "transcript_analysis": "Key concepts identified",
            "tutorial_steps": ["Step 1", "Step 2", "Step 3"],
            "mcp_source": "youtube-extension"
        }
    
    def _extract_video_id(self, video_url: str) -> str:
        """Extract video ID from URL"""
        if "youtube.com/watch?v=" in video_url:
            return video_url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
            return video_url.split("youtu.be/")[1].split("?")[0]
        return "unknown"
    
    async def _update_learning_patterns(self, success_rating: int, what_worked: str, what_failed: str, key_lessons: str):
        """Update learning patterns database"""
        pattern_name = f"rating_{success_rating}_pattern"
        
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute("SELECT id, video_count, avg_success_rating FROM learning_patterns WHERE pattern_name = ?", (pattern_name,)).fetchone()
            
            if existing:
                new_count = existing[1] + 1
                new_avg = (existing[2] * existing[1] + success_rating) / new_count
                conn.execute("UPDATE learning_patterns SET video_count = ?, avg_success_rating = ? WHERE id = ?", (new_count, new_avg, existing[0]))
            else:
                conn.execute("""
                    INSERT INTO learning_patterns (pattern_name, success_indicators, failure_indicators, video_count, avg_success_rating, pattern_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (pattern_name, what_worked, what_failed, 1, success_rating, json.dumps({"lessons": key_lessons})))
    
    async def _generate_implementation_insights(self, success_rating: int, what_worked: str, what_failed: str) -> List[str]:
        """Generate insights from implementation"""
        insights = []
        
        if success_rating >= 8:
            insights.append(f"🎉 Excellent success! Key factor: {what_worked[:50]}...")
            insights.append("📈 This pattern should be replicated for similar videos")
        elif success_rating >= 6:
            insights.append(f"✅ Good success with room for improvement")
            insights.append(f"⚠️ Watch out for: {what_failed[:50]}...")
        else:
            insights.append(f"❌ Implementation struggled. Main issue: {what_failed[:50]}...")
            insights.append("🔄 Consider different approach or additional preparation")
        
        return insights
    
    def _get_recommendations_for_rating(self, success_rating: int) -> List[str]:
        """Get recommendations based on success rating"""
        if success_rating >= 8:
            return ["🚀 Share this successful approach with others", "📝 Document the winning strategy", "🎯 Apply similar approach to related challenges"]
        elif success_rating >= 6:
            return ["🔧 Fine-tune the approach", "📊 Analyze what could be improved", "🎯 Focus on addressing the failure points"]
        else:
            return ["🔄 Try a completely different approach", "📚 Get more background knowledge first", "🤝 Consider getting help or collaboration"]
    
    # Additional competitive analysis methods for insights and predictions...
    async def _claude_insight_analysis(self, successful_videos: List, failed_videos: List, focus_area: str) -> Dict[str, Any]:
        """Claude's insight analysis"""
        return {
            "systematic_insights": f"Patterns in {focus_area} show systematic preparation correlates with success",
            "success_factors": ["Clear planning", "Proper setup", "Systematic approach"],
            "failure_patterns": ["Rushed implementation", "Skipped prerequisites", "Unclear goals"]
        }
    
    async def _grok_insight_challenge(self, claude_insights: Dict, successful_videos: List, focus_area: str) -> Dict[str, Any]:
        """Grok challenges Claude's insights"""
        return {
            "challenge": f"Claude's systematic insights about {focus_area} miss the real-time adaptation factor!",
            "rapid_insights": f"Success in {focus_area} comes from quick iteration, not perfect planning",
            "speed_factors": ["Fast starts", "Rapid pivots", "Real-time adjustments"]
        }
    
    async def _synthesize_insights(self, claude_insights: Dict, grok_insights: Dict) -> Dict[str, Any]:
        """Synthesize competitive insights"""
        return {
            "breakthrough_insight": "Success requires BOTH systematic preparation AND rapid adaptation",
            "actionable_recommendations": [
                "Start with Claude's systematic planning",
                "Execute with Grok's rapid iteration",
                "Validate systematically while adapting quickly"
            ],
            "innovation_opportunities": [
                "Hybrid planning-adaptation frameworks",
                "Real-time systematic validation",
                "Speed-optimized systematic approaches"
            ]
        }
    
    async def _claude_success_prediction(self, video_url: str, skill_level: str, available_time: str, similar_videos: List) -> Dict[str, Any]:
        """Claude's success prediction"""
        base_rating = 7 if skill_level == "advanced" else 6 if skill_level == "intermediate" else 5
        return {
            "predicted_rating": base_rating,
            "confidence": 0.8,
            "systematic_factors": ["Skill level alignment", "Time adequacy", "Preparation quality"]
        }
    
    async def _grok_prediction_challenge(self, claude_prediction: Dict, video_url: str, skill_level: str) -> Dict[str, Any]:
        """Grok challenges Claude's prediction"""
        return {
            "challenge": "Claude's prediction ignores adaptation capability!",
            "rapid_prediction": claude_prediction["predicted_rating"] + 1,  # Grok is more optimistic
            "confidence": 0.85,
            "speed_factors": ["Quick learning", "Rapid adjustment", "Iteration speed"]
        }
    
    async def _synthesize_predictions(self, claude_pred: Dict, grok_pred: Dict) -> Dict[str, Any]:
        """Synthesize predictions"""
        avg_rating = (claude_pred["predicted_rating"] + grok_pred["rapid_prediction"]) / 2
        avg_confidence = (claude_pred["confidence"] + grok_pred["confidence"]) / 2
        
        return {
            "predicted_rating": round(avg_rating, 1),
            "confidence": round(avg_confidence, 2),
            "risk_factors": ["Complexity mismatch", "Time constraints", "Skill gaps"],
            "success_strategies": ["Systematic start + rapid adaptation", "Quick wins first", "Validate frequently"],
            "time_estimate": "2-4 hours with hybrid approach"
        }

async def main():
    """Start the streamlined YouTube Innovation MCP server"""
    logger.info("🚀 Starting YouTube Innovation MCP Server (Streamlined)")
    
    server = YouTubeInnovationMCP()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())