#!/usr/bin/env python3
"""
Knowledge Base - Video Technology Persistence & Capability Generation
Stores extracted technologies from videos as accumulated knowledge.
Anti-bloat: <100 lines, JSON storage, no ML overhead
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

KNOWLEDGE_DB = Path(__file__).parent / "knowledge_database.json"

class KnowledgeBase:
    def __init__(self):
        self.data = self._load()

    def _load(self) -> Dict:
        if KNOWLEDGE_DB.exists():
            return json.loads(KNOWLEDGE_DB.read_text())
        return {"technologies": {}, "videos": [], "capabilities": [], "stats": {"total_videos": 0, "unique_techs": 0}}

    def _save(self):
        KNOWLEDGE_DB.write_text(json.dumps(self.data, indent=2))

    def capture_from_video(self, video_id: str, video_title: str, technologies: List[str], video_url: str = "") -> Dict:
        """Capture technologies from a processed video"""
        # Store video record
        video_record = {
            "id": video_id,
            "title": video_title,
            "url": video_url,
            "technologies": technologies,
            "captured_at": datetime.now().isoformat()
        }
        self.data["videos"].append(video_record)
        self.data["stats"]["total_videos"] += 1

        # Update technology frequency counts
        for tech in technologies:
            tech_lower = tech.lower().strip()
            if tech_lower not in self.data["technologies"]:
                self.data["technologies"][tech_lower] = {"name": tech, "count": 0, "first_seen": datetime.now().isoformat(), "videos": []}
            self.data["technologies"][tech_lower]["count"] += 1
            self.data["technologies"][tech_lower]["videos"].append(video_id)

        self.data["stats"]["unique_techs"] = len(self.data["technologies"])
        self._check_capability_generation()
        self._save()
        return {"captured": len(technologies), "total_unique": self.data["stats"]["unique_techs"]}

    def _check_capability_generation(self, threshold: int = 3):
        """Generate capability skills when technology appears in multiple videos"""
        for tech_key, tech_data in self.data["technologies"].items():
            if tech_data["count"] >= threshold:
                existing = [c for c in self.data["capabilities"] if c["technology"] == tech_key]
                if not existing:
                    capability = {
                        "id": len(self.data["capabilities"]) + 1,
                        "technology": tech_key,
                        "name": f"Generate {tech_data['name']} integration",
                        "trigger": f"When video mentions {tech_data['name']}",
                        "action": f"Include {tech_data['name']} patterns in generated code",
                        "count": tech_data["count"],
                        "created": datetime.now().isoformat()
                    }
                    self.data["capabilities"].append(capability)

    def get_relevant_capabilities(self, technologies: List[str]) -> List[Dict]:
        """Get capabilities relevant to given technologies"""
        relevant = []
        for tech in technologies:
            tech_lower = tech.lower().strip()
            for cap in self.data["capabilities"]:
                if cap["technology"] == tech_lower:
                    relevant.append(cap)
        return relevant

    def get_technology_context(self, limit: int = 10) -> str:
        """Get accumulated knowledge as context for code generation"""
        top_techs = sorted(self.data["technologies"].values(), key=lambda x: x["count"], reverse=True)[:limit]
        if not top_techs:
            return ""
        context = "ACCUMULATED KNOWLEDGE FROM PROCESSED VIDEOS:\n"
        for tech in top_techs:
            context += f"- {tech['name']}: seen in {tech['count']} videos\n"
        caps = [c for c in self.data["capabilities"]]
        if caps:
            context += "\nACTIVE CAPABILITIES:\n"
            for cap in caps[:5]:
                context += f"- {cap['name']}\n"
        return context

    def get_stats(self) -> Dict:
        return {**self.data["stats"], "capabilities": len(self.data["capabilities"])}

# Global instance
_kb = None
def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
