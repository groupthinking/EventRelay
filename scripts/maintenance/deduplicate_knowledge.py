#!/usr/bin/env python3
"""
Knowledge Base Deduplication and Consolidation Tool
===================================================

Identifies duplicate video and technology observations inside the knowledge database,
consolidating duplicates, recalculating reference counts, and updating stats.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [Deduplicator] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default file paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATABASE_PATH = _PROJECT_ROOT / "docs" / "knowledge_prototypes" / "mcp-servers" / "docs" / "knowledge_database.json"


class KnowledgeDeduplicator:
    """Handles parsing, deduplicating, and consolidating a knowledge database JSON file."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.data: Dict[str, Any] = {}
        self.report_stats: Dict[str, Any] = {}

    def load(self) -> bool:
        """Loads database from file."""
        if not self.db_path.exists():
            logger.error(f"Database file not found at {self.db_path}")
            return False
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading database file: {e}")
            return False

    def save(self) -> bool:
        """Saves current state back to the database file."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logger.info(f"Database written successfully to {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write database: {e}")
            return False

    def run_deduplication(self, dry_run: bool = False, consolidate_similar: bool = False) -> Dict[str, Any]:
        """
        Executes complete deduplication process:
        - Deduplicate list of videos (by video ID).
        - Deduplicate technology references in technologies list.
        - Merge highly similar tech entries if requested.
        - Re-compute counts and update stats block.
        """
        if not self.data:
            logger.warning("No data loaded. Skipping deduplication.")
            return {}

        original_videos_count = len(self.data.get("videos", []))
        original_techs_count = len(self.data.get("technologies", {}))

        # 1. Deduplicate Videos
        videos_list = self.data.get("videos", [])
        unique_videos: Dict[str, Dict[str, Any]] = {}

        for video in videos_list:
            v_id = video.get("id")
            if not v_id:
                continue

            if v_id not in unique_videos:
                unique_videos[v_id] = {
                    "id": v_id,
                    "title": video.get("title", ""),
                    "url": video.get("url", ""),
                    "technologies": list(set(video.get("technologies", []))),
                    "captured_at": video.get("captured_at", "")
                }
            else:
                # Merge technologies lists
                existing_techs = set(unique_videos[v_id]["technologies"])
                new_techs = set(video.get("technologies", []))
                unique_videos[v_id]["technologies"] = list(existing_techs.union(new_techs))

                # Keep earliest captured_at timestamp if present
                old_ts = unique_videos[v_id].get("captured_at")
                new_ts = video.get("captured_at")
                if new_ts and (not old_ts or new_ts < old_ts):
                    unique_videos[v_id]["captured_at"] = new_ts

        deduplicated_videos = list(unique_videos.values())

        # 2. Rebuild and Clean Technologies Dict
        techs_dict = self.data.get("technologies", {})
        cleaned_techs: Dict[str, Dict[str, Any]] = {}

        for key, entry in techs_dict.items():
            norm_key = key.strip().lower()
            if not norm_key:
                continue

            entry_videos = entry.get("videos", [])
            # Also support 'video_ids' list from other knowledge base structures
            if not entry_videos and "video_ids" in entry:
                entry_videos = entry["video_ids"]

            # Filter entry videos to only include unique existing video IDs
            unique_vids = list(set([v for v in entry_videos if v in unique_videos]))

            if norm_key not in cleaned_techs:
                cleaned_techs[norm_key] = {
                    "name": entry.get("name", key),
                    "count": len(unique_vids),
                    "first_seen": entry.get("first_seen", ""),
                    "videos": unique_vids
                }
            else:
                # Merge lists
                existing_entry = cleaned_techs[norm_key]
                merged_vids = list(set(existing_entry["videos"] + unique_vids))
                existing_entry["videos"] = merged_vids
                existing_entry["count"] = len(merged_vids)

                # Keep earlier first_seen
                old_ts = existing_entry.get("first_seen")
                new_ts = entry.get("first_seen")
                if new_ts and (not old_ts or new_ts < old_ts):
                    existing_entry["first_seen"] = new_ts

        # 3. High-Similarity Consolidation (Optional)
        # e.g., 'containers' or 'dockerode' -> merge under 'docker'
        similar_mappings = {
            "containers": "docker",
            "dockerode": "docker",
            "natural language processing": "large language models (llms)"
        }

        consolidations_done = []
        if consolidate_similar:
            for source, target in similar_mappings.items():
                if source in cleaned_techs and target in cleaned_techs:
                    source_entry = cleaned_techs[source]
                    target_entry = cleaned_techs[target]

                    # Merge videos
                    merged_vids = list(set(target_entry["videos"] + source_entry["videos"]))
                    target_entry["videos"] = merged_vids
                    target_entry["count"] = len(merged_vids)

                    # Remove the old source entry
                    del cleaned_techs[source]
                    consolidations_done.append(f"{source} consolidated into {target}")

        # Update actual frequency counts of remaining technologies
        for norm_key, entry in cleaned_techs.items():
            entry["count"] = len(entry["videos"])

        # 4. Rebuild Capabilities mappings (optional)
        capabilities = self.data.get("capabilities", [])
        cleaned_capabilities = []
        seen_caps = set()
        for cap in capabilities:
            tech = cap.get("technology", "").strip().lower()
            if consolidate_similar and tech in similar_mappings:
                tech = similar_mappings[tech]

            # Normalize trigger/action/name
            name = cap.get("name")
            cap_key = f"{tech}:{name}"
            if cap_key not in seen_caps:
                seen_caps.add(cap_key)
                cap["technology"] = tech
                cleaned_capabilities.append(cap)

        # 5. Populate updated fields
        if not dry_run:
            self.data["videos"] = deduplicated_videos
            self.data["technologies"] = cleaned_techs
            self.data["capabilities"] = cleaned_capabilities
            self.data["stats"] = {
                "total_videos": len(deduplicated_videos),
                "unique_techs": len(cleaned_techs)
            }
            self.save()

        # Gather summary report stats
        self.report_stats = {
            "original_videos": original_videos_count,
            "deduplicated_videos": len(deduplicated_videos),
            "original_techs": original_techs_count,
            "deduplicated_techs": len(cleaned_techs),
            "consolidated_similar": consolidations_done,
            "dry_run": dry_run
        }

        return self.report_stats

    def generate_report(self) -> str:
        """Generates a human-readable text report of the deduplication."""
        stats = self.report_stats
        if not stats:
            return "No deduplication run completed."

        report = [
            "===================================================",
            "📚 KNOWLEDGE BASE DEDUPLICATION REPORT",
            "===================================================",
            f"Dry Run Mode:          {stats['dry_run']}",
            f"Original Videos:       {stats['original_videos']}",
            f"Deduplicated Videos:   {stats['deduplicated_videos']}",
            f"Videos Merged/Removed: {stats['original_videos'] - stats['deduplicated_videos']}",
            f"Original Techs:        {stats['original_techs']}",
            f"Deduplicated Techs:    {stats['deduplicated_techs']}",
            f"Techs Consolidated:    {len(stats['consolidated_similar'])}",
        ]

        if stats["consolidated_similar"]:
            report.append("\nConsolidation details:")
            for item in stats["consolidated_similar"]:
                report.append(f"  - {item}")

        report.append("===================================================")
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Knowledge Base Deduplicator")
    parser.add_argument("--path", default=str(DEFAULT_DATABASE_PATH), help="Path to knowledge_database.json")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without writing changes")
    parser.add_argument("--consolidate", action="store_true", help="Consolidate highly similar technology terms")

    args = parser.parse_args()

    deduplicator = KnowledgeDeduplicator(args.path)
    if not deduplicator.load():
        sys.exit(1)

    deduplicator.run_deduplication(dry_run=args.dry_run, consolidate_similar=args.consolidate)
    print(deduplicator.generate_report())


if __name__ == "__main__":
    main()
