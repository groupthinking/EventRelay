#!/usr/bin/env python3
"""
Self-Healing Skill Builder - Autonomous Error Resolution
Captures error → resolution patterns as reusable skills
Anti-bloat: <100 lines, uses existing tools
"""
import json
from datetime import datetime
from pathlib import Path

SKILLS_DB = Path(__file__).parent / "skills_database.json"

class SkillBuilder:
    def __init__(self):
        self.skills = self._load_skills()

    def _load_skills(self):
        """Load existing skills"""
        if SKILLS_DB.exists():
            return json.loads(SKILLS_DB.read_text())
        return {"skills": [], "stats": {"total_errors_handled": 0, "auto_resolved": 0}}

    def _save_skills(self):
        """Persist skills"""
        SKILLS_DB.write_text(json.dumps(self.skills, indent=2))

    def capture_error_resolution(self, error_type, error_msg, resolution, context=""):
        """Capture new skill from error resolution"""
        skill = {
            "id": len(self.skills["skills"]) + 1,
            "error_type": error_type,
            "pattern": error_msg,
            "resolution": resolution,
            "context": context,
            "created": datetime.now().isoformat(),
            "usage_count": 0,
            "success_rate": 100.0
        }
        self.skills["skills"].append(skill)
        self.skills["stats"]["total_errors_handled"] += 1
        self._save_skills()
        return skill

    def find_matching_skill(self, error_type, error_msg):
        """Find skill that matches current error"""
        for skill in self.skills["skills"]:
            if skill["error_type"] == error_type and skill["pattern"] in error_msg:
                return skill
        return None

    def apply_skill(self, skill_id, success=True):
        """Apply skill and track success"""
        for skill in self.skills["skills"]:
            if skill["id"] == skill_id:
                skill["usage_count"] += 1
                if success:
                    self.skills["stats"]["auto_resolved"] += 1
                # Update success rate
                skill["success_rate"] = (
                    self.skills["stats"]["auto_resolved"] /
                    self.skills["stats"]["total_errors_handled"] * 100
                )
                self._save_skills()
                return True
        return False

    def get_top_skills(self, limit=5):
        """Get most used skills"""
        return sorted(
            self.skills["skills"],
            key=lambda x: x["usage_count"],
            reverse=True
        )[:limit]

    def get_stats(self):
        """Get resolution statistics"""
        return self.skills["stats"]

def auto_resolve(error_type, error_msg, context=""):
    """Autonomous error resolution with skill learning"""
    builder = SkillBuilder()

    # Check if we have a skill for this error
    skill = builder.find_matching_skill(error_type, error_msg)

    if skill:
        print(f"🔧 Auto-resolving with skill #{skill['id']}")
        print(f"   Resolution: {skill['resolution']}")
        builder.apply_skill(skill['id'], success=True)
        return skill['resolution']
    else:
        print(f"⚠️  New error detected: {error_type}")
        print(f"   Message: {error_msg}")
        print(f"   Awaiting resolution to capture as skill...")
        return None

if __name__ == "__main__":
    # Demo: Capture common errors from session
    builder = SkillBuilder()

    # Skill 1: YouTube API method change
    builder.capture_error_resolution(
        error_type="AttributeError",
        error_msg="'YouTubeTranscriptApi' has no attribute 'get_transcript'",
        resolution="Use YouTubeTranscriptApi().fetch(video_id) instead of get_transcript()",
        context="YouTube Transcript API updated to new method"
    )

    # Skill 2: Import path errors
    builder.capture_error_resolution(
        error_type="ModuleNotFoundError",
        error_msg="No module named 'src.youtube_extension.backend.services.youtube.adapters.api_cost_monitor'",
        resolution="Fix relative import: use ...api_cost_monitor (three dots) for correct path",
        context="Import from parent directory requires correct relative path"
    )

    print("\n📚 Skill Database Initialized")
    print(f"Total skills: {len(builder.skills['skills'])}")
    print(f"Stats: {builder.get_stats()}")
