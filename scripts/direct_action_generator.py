#!/usr/bin/env python3
"""
Direct Action Generator - Emergency Fix for Prompt Length Issues
Bypasses complex agent coordination to generate actions immediately.
"""

import json
import sys
from typing import Dict, List, Any
from datetime import datetime

class DirectActionGenerator:
    """Simple, direct action generator without complex coordination."""
    
    def __init__(self):
        self.content_categories = {
            "educational": self._generate_educational_actions,
            "business": self._generate_business_actions,
            "creative": self._generate_creative_actions,
            "health": self._generate_health_actions,
            "programming": self._generate_programming_actions
        }
    
    def generate_actions(self, transcript: str, video_id: str = None) -> Dict[str, Any]:
        """Generate actions directly from transcript without complex processing."""
        
        # Simple category detection
        category = self._detect_category(transcript)
        
        # Generate category-specific actions
        actions = self.content_categories.get(category, self._generate_default_actions)(transcript)
        
        return {
            "video_id": video_id or "unknown",
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "actions": actions,
            "total_actions": len(actions),
            "estimated_total_time": sum(action.get("estimated_minutes", 5) for action in actions)
        }
    
    def _detect_category(self, transcript: str) -> str:
        """Simple keyword-based category detection."""
        text = transcript.lower()
        
        if any(word in text for word in ["learn", "teach", "education", "lesson", "course"]):
            return "educational"
        elif any(word in text for word in ["business", "strategy", "marketing", "sales"]):
            return "business"
        elif any(word in text for word in ["code", "programming", "python", "javascript", "software"]):
            return "programming"
        elif any(word in text for word in ["cook", "recipe", "workout", "fitness", "health"]):
            return "health"
        elif any(word in text for word in ["diy", "build", "create", "craft", "make"]):
            return "creative"
        else:
            return "general"
    
    def _generate_educational_actions(self, transcript: str) -> List[Dict[str, Any]]:
        """Generate educational content actions."""
        return [
            {
                "type": "study_plan",
                "title": "Create structured learning pathway",
                "description": "Break down the educational content into digestible modules",
                "estimated_minutes": 15,
                "priority": "high",
                "deliverables": ["study_schedule", "learning_modules", "progress_tracker"]
            },
            {
                "type": "practice_exercises", 
                "title": "Generate practice problems",
                "description": "Create hands-on exercises to reinforce learning",
                "estimated_minutes": 20,
                "priority": "high",
                "deliverables": ["exercise_list", "answer_key", "difficulty_progression"]
            },
            {
                "type": "knowledge_test",
                "title": "Build assessment quiz",
                "description": "Test understanding with targeted questions",
                "estimated_minutes": 10,
                "priority": "medium",
                "deliverables": ["quiz_questions", "grading_rubric"]
            }
        ]
    
    def _generate_business_actions(self, transcript: str) -> List[Dict[str, Any]]:
        """Generate business content actions."""
        return [
            {
                "type": "process_documentation",
                "title": "Document business processes",
                "description": "Create step-by-step process documentation",
                "estimated_minutes": 25,
                "priority": "high",
                "deliverables": ["process_flowchart", "checklist", "templates"]
            },
            {
                "type": "automation_script",
                "title": "Identify automation opportunities",
                "description": "Find repetitive tasks that can be automated",
                "estimated_minutes": 30,
                "priority": "medium",
                "deliverables": ["automation_candidates", "roi_analysis", "implementation_plan"]
            }
        ]
    
    def _generate_programming_actions(self, transcript: str) -> List[Dict[str, Any]]:
        """Generate programming content actions."""
        return [
            {
                "type": "code_implementation",
                "title": "Implement code examples",
                "description": "Create working code based on video examples",
                "estimated_minutes": 45,
                "priority": "high",
                "deliverables": ["source_code", "documentation", "test_cases"]
            },
            {
                "type": "environment_setup",
                "title": "Set up development environment",
                "description": "Configure tools and dependencies",
                "estimated_minutes": 20,
                "priority": "high",
                "deliverables": ["setup_guide", "requirements_file", "docker_config"]
            }
        ]
    
    def _generate_creative_actions(self, transcript: str) -> List[Dict[str, Any]]:
        """Generate creative/DIY content actions."""
        return [
            {
                "type": "materials_list",
                "title": "Compile materials and tools list",
                "description": "List everything needed for the project",
                "estimated_minutes": 10,
                "priority": "high",
                "deliverables": ["shopping_list", "tool_requirements", "cost_estimate"]
            },
            {
                "type": "project_timeline",
                "title": "Create project timeline",
                "description": "Break project into manageable phases",
                "estimated_minutes": 15,
                "priority": "medium",
                "deliverables": ["timeline", "milestones", "checkpoint_reviews"]
            }
        ]
    
    def _generate_health_actions(self, transcript: str) -> List[Dict[str, Any]]:
        """Generate health/fitness/cooking actions."""
        return [
            {
                "type": "meal_plan",
                "title": "Create weekly meal plan",
                "description": "Plan meals based on video recommendations",
                "estimated_minutes": 20,
                "priority": "high",
                "deliverables": ["meal_schedule", "shopping_list", "prep_instructions"]
            },
            {
                "type": "tracking_system",
                "title": "Set up progress tracking",
                "description": "Create system to monitor health goals",
                "estimated_minutes": 15,
                "priority": "medium",
                "deliverables": ["tracking_sheet", "progress_metrics", "goal_milestones"]
            }
        ]
    
    def _generate_default_actions(self, transcript: str) -> List[Dict[str, Any]]:
        """Generate general actions for uncategorized content."""
        return [
            {
                "type": "summary_notes",
                "title": "Create summary notes",
                "description": "Summarize key points from the content",
                "estimated_minutes": 10,
                "priority": "medium",
                "deliverables": ["key_points", "action_items"]
            },
            {
                "type": "follow_up_research",
                "title": "Research related topics",
                "description": "Find additional resources and information",
                "estimated_minutes": 15,
                "priority": "low",
                "deliverables": ["resource_list", "reading_recommendations"]
            }
        ]

def main():
    """CLI interface for direct action generation."""
    if len(sys.argv) < 2:
        print("Usage: python direct_action_generator.py <transcript_file>")
        sys.exit(1)
    
    transcript_file = sys.argv[1]
    
    try:
        with open(transcript_file, 'r') as f:
            transcript = f.read()
        
        generator = DirectActionGenerator()
        result = generator.generate_actions(transcript)
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()