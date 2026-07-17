#!/usr/bin/env python3
"""
Knowledge Base — Technology Learning from Video Analysis
=========================================================

Persists technology observations extracted from video analyses so that
the AI Code Generator can build context over time.  Each video's
extracted technologies are recorded with metadata (video ID, title, URL,
timestamp).  The accumulated knowledge is surfaced as prompt context for
architecture decisions.

Storage: JSON file at ``<project_root>/data/knowledge_base.json``.
Thread-safe via ``threading.Lock``.

Required API (consumed by ``ai_code_generator.py``):
    get_knowledge_base() -> KnowledgeBase
    KnowledgeBase.capture_from_video(video_id, title, technologies, video_url)
    KnowledgeBase.get_technology_context() -> str
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Resolve project root: scripts/ sits one level below the repo root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_KB_PATH = _PROJECT_ROOT / "data" / "knowledge_base.json"


class KnowledgeBase:
    """
    File-backed knowledge base that accumulates technology observations
    from video analyses.

    Thread-safe.  Designed for both local dev and Cloud Run (uses /tmp
    fallback if the default path is not writable).
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = Path(path) if path else self._resolve_storage_path()
        self._lock = threading.Lock()
        self._data: dict[str, Any] = self._load()
        logger.info(
            f"📚 Knowledge base loaded from {self._path} "
            f"({len(self._data.get('technologies', {}))} unique techs, "
            f"{len(self._data.get('videos', {}))} videos)"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture_from_video(
        self,
        video_id: str,
        title: str,
        technologies: list[str],
        video_url: str = "",
    ) -> dict[str, Any]:
        """
        Record technologies observed in a video analysis.

        Args:
            video_id:     YouTube video ID (or other unique identifier).
            title:        Video title / display name.
            technologies: Technology names extracted from the video.
            video_url:    Original video URL.

        Returns:
            ``{"captured": <int>, "total_unique": <int>}``
        """
        with self._lock:
            techs = self._data.setdefault("technologies", {})
            videos = self._data.setdefault("videos", {})
            now = datetime.now(timezone.utc).isoformat()

            captured = 0
            for tech in technologies:
                key = tech.strip().lower()
                if not key:
                    continue
                entry = techs.setdefault(
                    key,
                    {
                        "name": tech.strip(),
                        "count": 0,
                        "first_seen": now,
                        "video_ids": [],
                    },
                )
                entry["count"] += 1
                entry["last_seen"] = now
                if video_id not in entry["video_ids"]:
                    entry["video_ids"].append(video_id)
                captured += 1

            videos[video_id] = {
                "title": title,
                "url": video_url,
                "technologies": [t.strip() for t in technologies if t.strip()],
                "captured_at": now,
            }

            self._data["last_updated"] = now
            self._save()

        logger.info(
            f"📚 Captured {captured} techs from video '{title}' "
            f"(total unique: {len(techs)})"
        )
        return {"captured": captured, "total_unique": len(techs)}

    def get_technology_context(self) -> str:
        """
        Return a prompt-friendly context string summarising the accumulated
        technology knowledge.

        The string is designed to be injected into Gemini prompts to inform
        architecture decisions.
        """
        with self._lock:
            techs = self._data.get("technologies", {})
            videos = self._data.get("videos", {})

        if not techs:
            return ""

        # Sort by observation count (most frequent first)
        ranked = sorted(techs.values(), key=lambda t: t["count"], reverse=True)

        lines = [
            "ACCUMULATED TECHNOLOGY KNOWLEDGE (from previous video analyses):",
            f"  Videos analysed: {len(videos)}",
            f"  Unique technologies observed: {len(techs)}",
            "",
            "  Most frequently observed technologies:",
        ]
        for tech in ranked[:20]:
            lines.append(
                f"    - {tech['name']} (seen {tech['count']}× "
                f"across {len(tech['video_ids'])} video(s))"
            )

        lines.append("")
        lines.append(
            "  Use this knowledge to inform your architecture choices — "
            "prefer technologies with higher adoption across analysed videos."
        )
        return "\n".join(lines)

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics for health checks."""
        with self._lock:
            techs = self._data.get("technologies", {})
            videos = self._data.get("videos", {})
            return {
                "unique_technologies": len(techs),
                "videos_processed": len(videos),
                "last_updated": self._data.get("last_updated"),
                "storage_path": str(self._path),
            }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_storage_path() -> Path:
        """Pick the best writable location for the knowledge store."""
        # Allow override via environment variable
        env_path = os.getenv("KNOWLEDGE_BASE_PATH")
        if env_path:
            return Path(env_path)

        # Default location: <project_root>/data/
        default = _DEFAULT_KB_PATH
        try:
            default.parent.mkdir(parents=True, exist_ok=True)
            # Quick writability check
            test_file = default.parent / ".write_test"
            test_file.touch()
            test_file.unlink()
            return default
        except OSError:
            # Fallback for Cloud Run / read-only filesystems
            fallback = Path("/tmp/uvai/knowledge_base.json")
            fallback.parent.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Default KB path not writable, using {fallback}")
            return fallback

    def _load(self) -> dict[str, Any]:
        """Load existing knowledge base from disk."""
        if self._path.exists():
            try:
                with open(self._path, "r") as f:
                    data = json.load(f)
                return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(f"Failed to load knowledge base: {exc}. Starting fresh.")
        return {
            "technologies": {},
            "videos": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _save(self) -> None:
        """Persist current state to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2)
        except OSError as exc:
            logger.error(f"Failed to persist knowledge base: {exc}")


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_instance: Optional[KnowledgeBase] = None
_instance_lock = threading.Lock()


def get_knowledge_base() -> KnowledgeBase:
    """Return the global KnowledgeBase singleton (lazy-initialised)."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:  # double-check locking
                _instance = KnowledgeBase()
    return _instance


# ------------------------------------------------------------------
# CLI test
# ------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    kb = get_knowledge_base()
    print("\n📚 Knowledge Base Test")
    print("=" * 40)

    # Simulate a video capture
    result = kb.capture_from_video(
        video_id="dQw4w9WgXcQ",
        title="Test Video",
        technologies=["Python", "FastAPI", "React", "PostgreSQL"],
        video_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
    )
    print(f"Captured: {result}")
    print(f"\nStats: {kb.get_stats()}")
    print(f"\nContext:\n{kb.get_technology_context()}")
