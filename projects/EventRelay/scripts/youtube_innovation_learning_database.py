#!/usr/bin/env python3
"""
YouTube Innovation Learning Database with MCP Integration
Competitive pressure-driven video intake with learning outcome tracking
"""

import asyncio
import json
import logging
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import hashlib
import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import Server

# Import our innovation pressure engine
from innovation_pressure_engine import InnovationPressureEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeInnovationLearningDB:
    """Database system for tracking YouTube video learning with competitive innovation"""
    
    def __init__(self, db_path: str = "logs/youtube_innovation_learning.db"):
        self.db_path = db_path
        self.innovation_engine = InnovationPressureEngine()
        self.server = Server("youtube-innovation-learning")
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Register MCP tools
        self._register_mcp_tools()
    
    def _init_database(self):
        """Initialize the learning database with innovation tracking"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Video intake tracking
                CREATE TABLE IF NOT EXISTS video_intakes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_url TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    title TEXT,
                    duration TEXT,
                    intake_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    video_hash TEXT UNIQUE,
                    metadata_json TEXT,
                    status TEXT DEFAULT 'pending'
                );
                
                -- Innovation pressure analysis
                CREATE TABLE IF NOT EXISTS innovation_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT REFERENCES video_intakes(video_id),
                    analysis_type TEXT, -- 'competitive', 'synthesis', 'breakthrough'
                    claude_hypothesis TEXT,
                    grok_hypothesis TEXT,
                    innovation_score REAL,
                    breakthrough_achieved BOOLEAN DEFAULT FALSE,
                    pressure_level REAL,
                    analysis_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    analysis_json TEXT
                );
                
                -- Implementation attempts
                CREATE TABLE IF NOT EXISTS implementations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT REFERENCES video_intakes(video_id),
                    innovation_analysis_id INTEGER REFERENCES innovation_analyses(id),
                    implementation_approach TEXT,
                    implementation_steps TEXT, -- JSON array
                    success_status TEXT, -- 'success', 'partial', 'failure'
                    completion_percentage REAL,
                    implementation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    implementation_json TEXT
                );
                
                -- Learning outcomes
                CREATE TABLE IF NOT EXISTS learning_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT REFERENCES video_intakes(video_id),
                    implementation_id INTEGER REFERENCES implementations(id),
                    learning_type TEXT, -- 'success_pattern', 'failure_pattern', 'innovation_insight'
                    learning_description TEXT,
                    learning_value REAL, -- 0-1 value of learning
                    pattern_identified TEXT,
                    future_application TEXT,
                    learning_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    learning_json TEXT
                );
                
                -- Success/failure patterns
                CREATE TABLE IF NOT EXISTS pattern_database (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT, -- 'success', 'failure', 'innovation'
                    pattern_name TEXT,
                    pattern_description TEXT,
                    video_count INTEGER DEFAULT 1,
                    success_rate REAL,
                    innovation_correlation REAL,
                    pattern_json TEXT,
                    created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Innovation breakthrough tracking
                CREATE TABLE IF NOT EXISTS breakthrough_tracker (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    breakthrough_title TEXT,
                    breakthrough_description TEXT,
                    originating_video_id TEXT,
                    innovation_score REAL,
                    practical_value REAL,
                    implementation_success BOOLEAN,
                    breakthrough_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    breakthrough_json TEXT
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_video_hash ON video_intakes(video_hash);
                CREATE INDEX IF NOT EXISTS idx_video_id ON innovation_analyses(video_id);
                CREATE INDEX IF NOT EXISTS idx_innovation_score ON innovation_analyses(innovation_score);
                CREATE INDEX IF NOT EXISTS idx_success_status ON implementations(success_status);
                CREATE INDEX IF NOT EXISTS idx_pattern_type ON pattern_database(pattern_type);
            """)
            
        logger.info(f"✅ YouTube Innovation Learning Database initialized at {self.db_path}")
    
    def _register_mcp_tools(self):
        """Register MCP tools for YouTube innovation learning"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="intake_youtube_video_with_innovation",
                    description="Intake YouTube video with competitive innovation analysis",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_url": {"type": "string", "description": "YouTube video URL"},
                            "innovation_goal": {"type": "string", "description": "Specific innovation goal for this video"},
                            "pressure_level": {"type": "number", "default": 1.0, "description": "Competitive pressure level (0.5-2.0)"},
                            "enable_breakthrough_detection": {"type": "boolean", "default": True}
                        },
                        "required": ["video_url", "innovation_goal"]
                    }
                ),
                types.Tool(
                    name="track_implementation_outcome",
                    description="Track implementation success/failure with learning extraction",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "video_id": {"type": "string", "description": "YouTube video ID"},
                            "implementation_steps": {"type": "array", "items": {"type": "string"}},
                            "success_status": {"type": "string", "enum": ["success", "partial", "failure"]},
                            "completion_percentage": {"type": "number", "minimum": 0, "maximum": 100},
                            "what_worked": {"type": "string", "description": "What aspects worked well"},
                            "what_failed": {"type": "string", "description": "What aspects failed"},
                            "learning_insights": {"type": "string", "description": "Key learning insights"}
                        },
                        "required": ["video_id", "success_status", "completion_percentage"]
                    }
                ),
                types.Tool(
                    name="query_learning_patterns",
                    description="Query learned patterns and success/failure data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern_type": {"type": "string", "enum": ["success", "failure", "innovation", "all"]},
                            "innovation_threshold": {"type": "number", "default": 0.8},
                            "video_topic": {"type": "string", "description": "Optional topic filter"},
                            "limit": {"type": "integer", "default": 10}
                        },
                        "required": []
                    }
                ),
                types.Tool(
                    name="generate_innovation_insights",
                    description="Generate innovation insights from learning database using competitive pressure",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "insight_focus": {"type": "string", "description": "Focus area for insight generation"},
                            "pressure_rounds": {"type": "integer", "default": 3, "description": "Number of competitive pressure rounds"},
                            "breakthrough_requirement": {"type": "boolean", "default": True}
                        },
                        "required": ["insight_focus"]
                    }
                ),
                types.Tool(
                    name="get_innovation_dashboard",
                    description="Get comprehensive dashboard of innovation learning metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "time_range": {"type": "string", "enum": ["24h", "7d", "30d", "all"], "default": "7d"},
                            "include_patterns": {"type": "boolean", "default": True},
                            "include_breakthroughs": {"type": "boolean", "default": True}
                        },
                        "required": []
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
            try:
                if name == "intake_youtube_video_with_innovation":
                    result = await self.intake_youtube_video_with_innovation(arguments)
                elif name == "track_implementation_outcome":
                    result = await self.track_implementation_outcome(arguments)
                elif name == "query_learning_patterns":
                    result = await self.query_learning_patterns(arguments)
                elif name == "generate_innovation_insights":
                    result = await self.generate_innovation_insights(arguments)
                elif name == "get_innovation_dashboard":
                    result = await self.get_innovation_dashboard(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return [types.TextContent(
                    type="text", 
                    text=f"Error: {str(e)}"
                )]
    
    async def intake_youtube_video_with_innovation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Intake YouTube video with competitive innovation analysis"""
        
        video_url = args["video_url"]
        innovation_goal = args["innovation_goal"]
        pressure_level = args.get("pressure_level", 1.0)
        enable_breakthrough = args.get("enable_breakthrough_detection", True)
        
        logger.info(f"🎥 Intaking YouTube video with innovation: {video_url}")
        
        # Extract video ID
        video_id = self._extract_video_id(video_url)
        video_hash = hashlib.md5(video_url.encode()).hexdigest()
        
        # Check if already processed
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id FROM video_intakes WHERE video_hash = ?",
                (video_hash,)
            ).fetchone()
            
            if existing:
                logger.info(f"📋 Video already in database, running additional innovation analysis")
        
        # Mock video metadata (in production, would use actual YouTube API)
        video_metadata = {
            "title": f"Innovation Tutorial: {innovation_goal}",
            "duration": "10:30",
            "description": f"Tutorial video for {innovation_goal}",
            "view_count": 15000,
            "like_count": 500
        }
        
        # Store video intake
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO video_intakes 
                (video_url, video_id, title, duration, video_hash, metadata_json, status)
                VALUES (?, ?, ?, ?, ?, ?, 'processing')
            """, (video_url, video_id, video_metadata["title"], video_metadata["duration"], 
                  video_hash, json.dumps(video_metadata)))
        
        # Run competitive innovation analysis
        innovation_challenge = {
            "topic": f"YouTube video learning: {innovation_goal}",
            "goal": f"Create breakthrough approach to implementing: {innovation_goal}",
            "constraints": ["Must be practical", "Should be implementable", "Based on video content"],
            "success_criteria": ["Clear implementation path", "Measurable outcomes", "Innovation beyond video content"]
        }
        
        # Set pressure level
        original_pressure = self.innovation_engine.competitive_rounds
        self.innovation_engine.competitive_rounds = max(1, int(pressure_level * 2))
        
        try:
            innovation_result = await self.innovation_engine.competitive_hypothesis_generation(innovation_challenge)
            
            # Extract innovation data
            innovation_data = innovation_result["innovation_competition_results"]
            breakthrough_hypotheses = innovation_result["breakthrough_hypotheses"]
            
            # Store innovation analysis
            with sqlite3.connect(self.db_path) as conn:
                analysis_id = conn.execute("""
                    INSERT INTO innovation_analyses 
                    (video_id, analysis_type, claude_hypothesis, grok_hypothesis, 
                     innovation_score, breakthrough_achieved, pressure_level, analysis_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_id, 
                    "competitive_intake",
                    breakthrough_hypotheses[0] if breakthrough_hypotheses else "No Claude hypothesis",
                    breakthrough_hypotheses[1] if len(breakthrough_hypotheses) > 1 else "No Grok hypothesis",
                    innovation_data["peak_innovation_score"],
                    innovation_data["breakthrough_achieved"],
                    pressure_level,
                    json.dumps(innovation_result)
                )).lastrowid
            
            # Check for breakthrough
            if innovation_data["breakthrough_achieved"] and enable_breakthrough:
                await self._record_breakthrough(video_id, innovation_result)
            
            # Update video status
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE video_intakes SET status = 'analyzed' WHERE video_id = ?",
                    (video_id,)
                )
            
            return {
                "video_intake": {
                    "video_id": video_id,
                    "video_url": video_url,
                    "title": video_metadata["title"],
                    "status": "analyzed"
                },
                "innovation_analysis": {
                    "analysis_id": analysis_id,
                    "innovation_score": innovation_data["peak_innovation_score"],
                    "breakthrough_achieved": innovation_data["breakthrough_achieved"],
                    "pressure_effectiveness": innovation_data["competitive_pressure_effectiveness"],
                    "rounds_completed": innovation_data["rounds_completed"]
                },
                "breakthrough_hypotheses": breakthrough_hypotheses,
                "implementation_recommendations": innovation_result.get("implementation_roadmap", {}),
                "next_steps": [
                    "Implement breakthrough hypotheses",
                    "Track implementation outcomes", 
                    "Learn from success/failure patterns",
                    "Apply insights to future videos"
                ]
            }
            
        finally:
            # Restore original pressure level
            self.innovation_engine.competitive_rounds = original_pressure
    
    async def track_implementation_outcome(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Track implementation outcomes with learning extraction"""
        
        video_id = args["video_id"]
        implementation_steps = args.get("implementation_steps", [])
        success_status = args["success_status"]
        completion_percentage = args["completion_percentage"]
        what_worked = args.get("what_worked", "")
        what_failed = args.get("what_failed", "")
        learning_insights = args.get("learning_insights", "")
        
        logger.info(f"📊 Tracking implementation outcome for {video_id}: {success_status}")
        
        # Get latest innovation analysis for this video
        with sqlite3.connect(self.db_path) as conn:
            analysis = conn.execute("""
                SELECT id, innovation_score, breakthrough_achieved 
                FROM innovation_analyses 
                WHERE video_id = ? 
                ORDER BY analysis_timestamp DESC 
                LIMIT 1
            """, (video_id,)).fetchone()
            
            if not analysis:
                raise ValueError(f"No innovation analysis found for video {video_id}")
            
            analysis_id = analysis[0]
            innovation_score = analysis[1]
            breakthrough_achieved = bool(analysis[2])
        
        # Store implementation outcome
        with sqlite3.connect(self.db_path) as conn:
            implementation_id = conn.execute("""
                INSERT INTO implementations 
                (video_id, innovation_analysis_id, implementation_approach, 
                 implementation_steps, success_status, completion_percentage, implementation_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                video_id,
                analysis_id,
                f"Implementation based on innovation analysis (score: {innovation_score})",
                json.dumps(implementation_steps),
                success_status,
                completion_percentage,
                json.dumps({
                    "what_worked": what_worked,
                    "what_failed": what_failed,
                    "learning_insights": learning_insights,
                    "innovation_correlation": innovation_score
                })
            )).lastrowid
        
        # Extract and store learning outcomes
        learning_outcomes = await self._extract_learning_outcomes(
            video_id, implementation_id, success_status, completion_percentage,
            what_worked, what_failed, learning_insights, innovation_score
        )
        
        # Update pattern database
        await self._update_pattern_database(success_status, innovation_score, learning_insights)
        
        return {
            "implementation_tracking": {
                "implementation_id": implementation_id,
                "video_id": video_id,
                "success_status": success_status,
                "completion_percentage": completion_percentage,
                "innovation_correlation": innovation_score
            },
            "learning_outcomes": learning_outcomes,
            "pattern_updates": f"Updated {success_status} patterns with innovation correlation",
            "recommendations": await self._generate_recommendations(success_status, innovation_score)
        }
    
    async def query_learning_patterns(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Query learning patterns from the database"""
        
        pattern_type = args.get("pattern_type", "all")
        innovation_threshold = args.get("innovation_threshold", 0.8)
        video_topic = args.get("video_topic", "")
        limit = args.get("limit", 10)
        
        with sqlite3.connect(self.db_path) as conn:
            # Query patterns
            if pattern_type == "all":
                pattern_query = "SELECT * FROM pattern_database ORDER BY updated_timestamp DESC LIMIT ?"
                patterns = conn.execute(pattern_query, (limit,)).fetchall()
            else:
                pattern_query = "SELECT * FROM pattern_database WHERE pattern_type = ? ORDER BY updated_timestamp DESC LIMIT ?"
                patterns = conn.execute(pattern_query, (pattern_type, limit)).fetchall()
            
            # Query high-innovation outcomes
            innovation_query = """
                SELECT v.title, i.success_status, i.completion_percentage, ia.innovation_score, ia.breakthrough_achieved
                FROM implementations i
                JOIN video_intakes v ON i.video_id = v.video_id
                JOIN innovation_analyses ia ON i.innovation_analysis_id = ia.id
                WHERE ia.innovation_score >= ?
                ORDER BY ia.innovation_score DESC
                LIMIT ?
            """
            high_innovation = conn.execute(innovation_query, (innovation_threshold, limit)).fetchall()
            
            # Query recent breakthroughs
            breakthrough_query = "SELECT * FROM breakthrough_tracker ORDER BY breakthrough_timestamp DESC LIMIT ?"
            breakthroughs = conn.execute(breakthrough_query, (limit,)).fetchall()
        
        return {
            "learning_patterns": {
                "pattern_count": len(patterns),
                "patterns": [
                    {
                        "pattern_name": p[2],
                        "pattern_type": p[1],
                        "description": p[3],
                        "video_count": p[4],
                        "success_rate": p[5],
                        "innovation_correlation": p[6]
                    } for p in patterns
                ]
            },
            "high_innovation_outcomes": [
                {
                    "video_title": h[0],
                    "success_status": h[1],
                    "completion_percentage": h[2],
                    "innovation_score": h[3],
                    "breakthrough_achieved": bool(h[4])
                } for h in high_innovation
            ],
            "recent_breakthroughs": [
                {
                    "title": b[1],
                    "description": b[2],
                    "innovation_score": b[4],
                    "practical_value": b[5],
                    "implementation_success": bool(b[6])
                } for b in breakthroughs
            ],
            "insights": {
                "total_patterns_identified": len(patterns),
                "high_innovation_correlation": len([h for h in high_innovation if h[3] >= innovation_threshold]),
                "breakthrough_rate": len(breakthroughs) / max(len(patterns), 1)
            }
        }
    
    async def generate_innovation_insights(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate innovation insights using competitive pressure on database"""
        
        insight_focus = args["insight_focus"]
        pressure_rounds = args.get("pressure_rounds", 3)
        breakthrough_requirement = args.get("breakthrough_requirement", True)
        
        # Query database for context
        with sqlite3.connect(self.db_path) as conn:
            # Get success/failure patterns
            patterns = conn.execute("SELECT pattern_type, pattern_name, success_rate, innovation_correlation FROM pattern_database").fetchall()
            
            # Get recent implementations
            implementations = conn.execute("""
                SELECT i.success_status, i.completion_percentage, ia.innovation_score, v.title
                FROM implementations i
                JOIN innovation_analyses ia ON i.innovation_analysis_id = ia.id
                JOIN video_intakes v ON i.video_id = v.video_id
                ORDER BY i.implementation_timestamp DESC
                LIMIT 20
            """).fetchall()
        
        # Create insight generation challenge
        database_context = {
            "success_patterns": [p for p in patterns if p[0] == "success"],
            "failure_patterns": [p for p in patterns if p[0] == "failure"],
            "recent_implementations": implementations,
            "innovation_correlations": [p[3] for p in patterns if p[3] is not None]
        }
        
        insight_challenge = {
            "topic": f"Database-driven innovation insights: {insight_focus}",
            "goal": f"Generate breakthrough insights about {insight_focus} using learning database patterns",
            "constraints": [
                "Must be based on actual database patterns",
                "Should predict future success probabilities",
                "Must identify innovation accelerators"
            ],
            "success_criteria": [
                "Novel insight not obvious from raw data",
                "Actionable recommendations",
                "Measurable success predictors"
            ],
            "database_context": database_context
        }
        
        # Run competitive insight generation
        original_rounds = self.innovation_engine.competitive_rounds
        self.innovation_engine.competitive_rounds = pressure_rounds
        
        try:
            insight_result = await self.innovation_engine.competitive_hypothesis_generation(insight_challenge)
            
            return {
                "insight_generation": {
                    "focus": insight_focus,
                    "pressure_rounds": pressure_rounds,
                    "breakthrough_achieved": insight_result["innovation_competition_results"]["breakthrough_achieved"],
                    "innovation_score": insight_result["innovation_competition_results"]["peak_innovation_score"]
                },
                "breakthrough_insights": insight_result["breakthrough_hypotheses"],
                "database_analysis": {
                    "patterns_analyzed": len(patterns),
                    "implementations_analyzed": len(implementations),
                    "average_innovation_score": sum(p[3] for p in patterns if p[3] is not None) / len([p for p in patterns if p[3] is not None]) if patterns else 0
                },
                "innovation_recommendations": insight_result.get("implementation_roadmap", {}),
                "competitive_pressure_insights": insight_result["innovation_insights"]
            }
            
        finally:
            self.innovation_engine.competitive_rounds = original_rounds
    
    async def get_innovation_dashboard(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive innovation dashboard"""
        
        time_range = args.get("time_range", "7d")
        include_patterns = args.get("include_patterns", True)
        include_breakthroughs = args.get("include_breakthroughs", True)
        
        # Convert time range to SQL
        time_filters = {
            "24h": "datetime('now', '-1 day')",
            "7d": "datetime('now', '-7 days')",
            "30d": "datetime('now', '-30 days')",
            "all": "datetime('2020-01-01')"
        }
        time_filter = time_filters.get(time_range, time_filters["7d"])
        
        with sqlite3.connect(self.db_path) as conn:
            # Video intake metrics
            video_stats = conn.execute(f"""
                SELECT COUNT(*) as total_videos,
                       COUNT(CASE WHEN status = 'analyzed' THEN 1 END) as analyzed_videos,
                       AVG(CASE WHEN status = 'analyzed' THEN 1.0 ELSE 0.0 END) as analysis_rate
                FROM video_intakes 
                WHERE intake_timestamp >= {time_filter}
            """).fetchone()
            
            # Innovation metrics
            innovation_stats = conn.execute(f"""
                SELECT AVG(innovation_score) as avg_innovation_score,
                       MAX(innovation_score) as peak_innovation_score,
                       COUNT(CASE WHEN breakthrough_achieved = 1 THEN 1 END) as breakthrough_count,
                       COUNT(*) as total_analyses
                FROM innovation_analyses 
                WHERE analysis_timestamp >= {time_filter}
            """).fetchone()
            
            # Implementation success rates
            implementation_stats = conn.execute(f"""
                SELECT success_status,
                       COUNT(*) as count,
                       AVG(completion_percentage) as avg_completion,
                       AVG(ia.innovation_score) as avg_innovation_correlation
                FROM implementations i
                JOIN innovation_analyses ia ON i.innovation_analysis_id = ia.id
                WHERE i.implementation_timestamp >= {time_filter}
                GROUP BY success_status
            """).fetchall()
            
            # Pattern evolution
            if include_patterns:
                pattern_stats = conn.execute(f"""
                    SELECT pattern_type, COUNT(*) as count, AVG(success_rate) as avg_success_rate
                    FROM pattern_database 
                    WHERE updated_timestamp >= {time_filter}
                    GROUP BY pattern_type
                """).fetchall()
            else:
                pattern_stats = []
            
            # Recent breakthroughs
            if include_breakthroughs:
                recent_breakthroughs = conn.execute(f"""
                    SELECT breakthrough_title, innovation_score, practical_value, implementation_success
                    FROM breakthrough_tracker 
                    WHERE breakthrough_timestamp >= {time_filter}
                    ORDER BY innovation_score DESC
                    LIMIT 5
                """).fetchall()
            else:
                recent_breakthroughs = []
        
        return {
            "dashboard_period": time_range,
            "video_intake_metrics": {
                "total_videos": video_stats[0] or 0,
                "analyzed_videos": video_stats[1] or 0,
                "analysis_rate": f"{(video_stats[2] or 0) * 100:.1f}%"
            },
            "innovation_metrics": {
                "average_innovation_score": round(innovation_stats[0] or 0, 3),
                "peak_innovation_score": round(innovation_stats[1] or 0, 3),
                "breakthrough_count": innovation_stats[2] or 0,
                "total_analyses": innovation_stats[3] or 0,
                "breakthrough_rate": f"{((innovation_stats[2] or 0) / max(innovation_stats[3] or 1, 1)) * 100:.1f}%"
            },
            "implementation_success_rates": {
                status[0]: {
                    "count": status[1],
                    "avg_completion": f"{status[2]:.1f}%",
                    "innovation_correlation": round(status[3] or 0, 3)
                } for status in implementation_stats
            },
            "pattern_insights": {
                pattern[0]: {
                    "pattern_count": pattern[1],
                    "avg_success_rate": f"{(pattern[2] or 0) * 100:.1f}%"
                } for pattern in pattern_stats
            } if include_patterns else {},
            "recent_breakthroughs": [
                {
                    "title": b[0],
                    "innovation_score": round(b[1], 3),
                    "practical_value": round(b[2], 3),
                    "implemented_successfully": bool(b[3])
                } for b in recent_breakthroughs
            ] if include_breakthroughs else [],
            "dashboard_insights": {
                "innovation_trajectory": "Improving" if (innovation_stats[0] or 0) > 0.7 else "Developing",
                "implementation_effectiveness": "High" if len([s for s in implementation_stats if s[0] == "success"]) > 0 else "Building",
                "breakthrough_momentum": "Strong" if (innovation_stats[2] or 0) > 0 else "Emerging"
            }
        }
    
    def _extract_video_id(self, video_url: str) -> str:
        """Extract YouTube video ID from URL"""
        if "youtube.com/watch?v=" in video_url:
            return video_url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in video_url:
            return video_url.split("youtu.be/")[1].split("?")[0]
        else:
            # Generate hash-based ID for non-YouTube URLs
            return hashlib.md5(video_url.encode()).hexdigest()[:11]
    
    async def _record_breakthrough(self, video_id: str, innovation_result: Dict[str, Any]) -> None:
        """Record breakthrough achievement"""
        
        breakthrough_data = innovation_result["innovation_competition_results"]
        breakthrough_insights = innovation_result["breakthrough_hypotheses"]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO breakthrough_tracker 
                (breakthrough_title, breakthrough_description, originating_video_id, 
                 innovation_score, practical_value, implementation_success, breakthrough_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"Innovation Breakthrough from Video {video_id}",
                breakthrough_insights[0] if breakthrough_insights else "Competitive pressure breakthrough",
                video_id,
                breakthrough_data["peak_innovation_score"],
                0.8,  # Default practical value
                False,  # Not yet implemented
                json.dumps(innovation_result)
            ))
    
    async def _extract_learning_outcomes(self, video_id: str, implementation_id: int, 
                                       success_status: str, completion_percentage: float,
                                       what_worked: str, what_failed: str, 
                                       learning_insights: str, innovation_score: float) -> List[Dict[str, Any]]:
        """Extract and store learning outcomes"""
        
        learning_outcomes = []
        
        # Success pattern learning
        if success_status == "success" and completion_percentage >= 80:
            learning_outcomes.append({
                "learning_type": "success_pattern",
                "learning_description": f"Successful implementation with {completion_percentage}% completion. Key factors: {what_worked}",
                "learning_value": min(1.0, completion_percentage / 100 + innovation_score * 0.2),
                "pattern_identified": f"High completion with innovation score {innovation_score}",
                "future_application": "Apply successful patterns to similar video implementations"
            })
        
        # Failure pattern learning
        elif success_status == "failure" or completion_percentage < 50:
            learning_outcomes.append({
                "learning_type": "failure_pattern", 
                "learning_description": f"Implementation challenges at {completion_percentage}% completion. Issues: {what_failed}",
                "learning_value": min(0.8, (100 - completion_percentage) / 100 + 0.3),
                "pattern_identified": f"Low completion with specific failure modes",
                "future_application": "Avoid identified failure patterns in future implementations"
            })
        
        # Innovation insight learning
        if innovation_score >= 0.8:
            learning_outcomes.append({
                "learning_type": "innovation_insight",
                "learning_description": f"High innovation score ({innovation_score}) provided insights: {learning_insights}",
                "learning_value": innovation_score,
                "pattern_identified": f"Innovation correlation with implementation outcome",
                "future_application": "Leverage high-innovation approaches for complex challenges"
            })
        
        # Store learning outcomes
        with sqlite3.connect(self.db_path) as conn:
            for outcome in learning_outcomes:
                conn.execute("""
                    INSERT INTO learning_outcomes 
                    (video_id, implementation_id, learning_type, learning_description, 
                     learning_value, pattern_identified, future_application, learning_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_id, implementation_id, outcome["learning_type"],
                    outcome["learning_description"], outcome["learning_value"],
                    outcome["pattern_identified"], outcome["future_application"],
                    json.dumps(outcome)
                ))
        
        return learning_outcomes
    
    async def _update_pattern_database(self, success_status: str, innovation_score: float, learning_insights: str) -> None:
        """Update pattern database with new data"""
        
        pattern_name = f"{success_status}_pattern_innovation_{innovation_score:.1f}"
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if pattern exists
            existing = conn.execute(
                "SELECT id, video_count, success_rate FROM pattern_database WHERE pattern_name = ?",
                (pattern_name,)
            ).fetchone()
            
            if existing:
                # Update existing pattern
                new_count = existing[1] + 1
                new_success_rate = (existing[2] * existing[1] + (1.0 if success_status == "success" else 0.0)) / new_count
                
                conn.execute("""
                    UPDATE pattern_database 
                    SET video_count = ?, success_rate = ?, innovation_correlation = ?, updated_timestamp = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_count, new_success_rate, innovation_score, existing[0]))
            else:
                # Create new pattern
                conn.execute("""
                    INSERT INTO pattern_database 
                    (pattern_type, pattern_name, pattern_description, video_count, 
                     success_rate, innovation_correlation, pattern_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    success_status,
                    pattern_name,
                    f"Pattern for {success_status} implementations with innovation score ~{innovation_score:.1f}",
                    1,
                    1.0 if success_status == "success" else 0.0,
                    innovation_score,
                    json.dumps({"learning_insights": learning_insights})
                ))
    
    async def _generate_recommendations(self, success_status: str, innovation_score: float) -> List[str]:
        """Generate recommendations based on outcome"""
        
        recommendations = []
        
        if success_status == "success":
            recommendations.extend([
                "🎉 Success! Apply these patterns to similar challenges",
                f"💡 Innovation score {innovation_score:.2f} shows effective approach",
                "📈 Share successful patterns with team"
            ])
        elif success_status == "partial":
            recommendations.extend([
                "⚠️ Partial success - analyze what worked vs what didn't",
                f"🔄 Innovation score {innovation_score:.2f} suggests room for improvement",
                "🎯 Focus on completing remaining implementation steps"
            ])
        else:  # failure
            recommendations.extend([
                "❌ Implementation failed - extract maximum learning value",
                f"🧠 Innovation score {innovation_score:.2f} - try different approach",
                "🔄 Use competitive pressure to generate alternative solutions"
            ])
        
        # Innovation-specific recommendations
        if innovation_score >= 0.9:
            recommendations.append("🚀 Exceptional innovation - document as breakthrough pattern")
        elif innovation_score >= 0.7:
            recommendations.append("💡 Good innovation - consider scaling approach")
        else:
            recommendations.append("🔄 Low innovation - apply competitive pressure for breakthroughs")
        
        return recommendations

async def main():
    """Main MCP server entry point"""
    logger.info("🚀 Starting YouTube Innovation Learning Database MCP Server")
    
    db = YouTubeInnovationLearningDB()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await db.server.run(
            read_stream,
            write_stream,
            db.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())