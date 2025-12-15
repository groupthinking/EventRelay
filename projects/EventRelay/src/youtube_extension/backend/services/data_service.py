#!/usr/bin/env python3
"""
Data Service
============

Extracted data handling business logic.
Handles video information retrieval, learning logs, feedback collection, and data persistence.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DataService:
    """
    Service for handling data operations.
    Provides unified interface for video information, learning logs, and feedback management.
    """
    
    def __init__(self, 
                 enhanced_analysis_dir: str = "youtube_processed_videos/enhanced_analysis",
                 feedback_dir: str = "youtube_processed_videos/feedback"):
        """
        Initialize data service.
        
        Args:
            enhanced_analysis_dir: Directory for enhanced analysis data
            feedback_dir: Directory for feedback data
        """
        self.enhanced_analysis_dir = Path(enhanced_analysis_dir)
        self.feedback_dir = Path(feedback_dir)
        
        # Ensure directories exist
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
    
    def get_learning_log(self) -> List[Dict[str, Any]]:
        """
        Generate learning log from enhanced analysis files.
        
        Returns:
            List of learning log entries
        """
        try:
            items = []
            
            if not self.enhanced_analysis_dir.exists():
                logger.warning(f"Enhanced analysis directory does not exist: {self.enhanced_analysis_dir}")
                return items
            
            for category_dir in self.enhanced_analysis_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                
                for md_file in category_dir.glob("*_enhanced.md"):
                    try:
                        # Extract video ID from filename
                        video_id = md_file.name.split("_")[0]
                        
                        # Find corresponding metadata file
                        metadata_file = next(category_dir.glob(f"{video_id}_*_metadata.json"), None)
                        metadata = {}
                        
                        if metadata_file and metadata_file.exists():
                            try:
                                with open(metadata_file, "r", encoding="utf-8") as f:
                                    metadata = json.load(f)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse metadata file {metadata_file}: {e}")
                        
                        # Get file statistics
                        stat = md_file.stat()
                        
                        # Extract title from metadata
                        title = (metadata.get("title") or 
                                metadata.get("snippet", {}).get("title") or
                                f"Video {video_id}")
                        
                        items.append({
                            "video_id": video_id,
                            "category": category_dir.name,
                            "title": title,
                            "actions_generated": None,  # Could be extracted from content
                            "transcript_segments": None,  # Could be extracted from metadata
                            "processing_time": None,  # Could be stored in metadata
                            "quality_assessment": None,  # Could be computed from content
                            "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "feedback": None  # Could be linked to feedback data
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error processing learning log entry for {md_file}: {e}")
                        continue
            
            # Sort by timestamp (newest first)
            items.sort(key=lambda x: x["timestamp"], reverse=True)
            
            logger.info(f"Generated learning log with {len(items)} entries")
            return items
            
        except Exception as e:
            logger.error(f"Error building learning log: {e}")
            return []
    
    def get_videos_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary list of processed videos.
        
        Returns:
            List of video summaries
        """
        try:
            results = []
            
            if not self.enhanced_analysis_dir.exists():
                logger.warning(f"Enhanced analysis directory does not exist: {self.enhanced_analysis_dir}")
                return results
            
            for category_dir in self.enhanced_analysis_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                
                for md_file in category_dir.glob("*_enhanced.md"):
                    try:
                        # Extract video ID from filename
                        video_id = md_file.name.split("_")[0]
                        
                        # Find corresponding metadata file
                        metadata_file = next(category_dir.glob(f"{video_id}_*_metadata.json"), None)
                        metadata = {}
                        
                        if metadata_file and metadata_file.exists():
                            try:
                                with open(metadata_file, "r", encoding="utf-8") as f:
                                    metadata = json.load(f)
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse metadata file {metadata_file}: {e}")
                        
                        # Get file statistics
                        stat = md_file.stat()
                        
                        # Extract information from metadata
                        title = (metadata.get("title") or 
                                metadata.get("snippet", {}).get("title") or
                                f"Video {video_id}")
                        
                        published_at = (metadata.get("published_at") or 
                                      metadata.get("snippet", {}).get("publishedAt"))
                        
                        view_count = (metadata.get("view_count") or 
                                    metadata.get("statistics", {}).get("viewCount"))
                        
                        results.append({
                            "video_id": video_id,
                            "category": category_dir.name,
                            "title": title,
                            "published_at": published_at,
                            "view_count": view_count,
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "markdown_path": str(md_file),
                            "metadata_path": str(metadata_file) if metadata_file else None
                        })
                        
                    except Exception as e:
                        logger.warning(f"Error processing video summary for {md_file}: {e}")
                        continue
            
            # Sort by last modified (newest first)
            results.sort(key=lambda x: x["last_modified"], reverse=True)
            
            logger.info(f"Generated videos summary with {len(results)} entries")
            return results
            
        except Exception as e:
            logger.error(f"Error listing videos: {e}")
            return []
    
    def get_video_detail(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific video.
        
        Args:
            video_id: Video ID to retrieve
            
        Returns:
            Video details or None if not found
        """
        try:
            if not self.enhanced_analysis_dir.exists():
                logger.warning(f"Enhanced analysis directory does not exist: {self.enhanced_analysis_dir}")
                return None
            
            for category_dir in self.enhanced_analysis_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                
                # Find markdown file for this video
                md_file = next(category_dir.glob(f"{video_id}_*_enhanced.md"), None)
                if not md_file or not md_file.exists():
                    continue
                
                # Find corresponding metadata file
                metadata_file = next(category_dir.glob(f"{video_id}_*_metadata.json"), None)
                metadata = {}
                
                if metadata_file and metadata_file.exists():
                    try:
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse metadata file {metadata_file}: {e}")
                
                # Read markdown content
                try:
                    with open(md_file, "r", encoding="utf-8") as f:
                        markdown = f.read()
                except Exception as e:
                    logger.error(f"Failed to read markdown file {md_file}: {e}")
                    markdown = ""
                
                # Extract title
                title = (metadata.get("title") or 
                        metadata.get("snippet", {}).get("title") or
                        f"Video {video_id}")
                
                return {
                    "video_id": video_id,
                    "category": category_dir.name,
                    "title": title,
                    "metadata": metadata,
                    "markdown": markdown,
                    "markdown_path": str(md_file),
                    "metadata_path": str(metadata_file) if metadata_file else None
                }
            
            # Video not found
            logger.info(f"Video not found: {video_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error reading video detail: {e}")
            return None
    
    def save_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """
        Save feedback data to persistent storage.
        
        Args:
            feedback_data: Feedback data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure feedback directory exists
            self.feedback_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare feedback entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                **feedback_data
            }
            
            # Append to JSONL feedback file
            log_file = self.feedback_dir / "feedback.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            
            logger.info(f"Feedback saved successfully for entry: {entry.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            return False
    
    def get_feedback_summary(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent feedback entries.
        
        Args:
            limit: Maximum number of feedback entries to return
            
        Returns:
            List of feedback entries
        """
        try:
            log_file = self.feedback_dir / "feedback.jsonl"
            
            if not log_file.exists():
                logger.info("No feedback file found")
                return []
            
            entries = []
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse feedback line: {e}")
                            continue
            
            # Sort by timestamp (newest first) and limit
            entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return entries[:limit]
            
        except Exception as e:
            logger.error(f"Error getting feedback summary: {e}")
            return []
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive data statistics.
        
        Returns:
            Statistics about stored data
        """
        try:
            stats = {
                "enhanced_videos": 0,
                "categories": {},
                "feedback_entries": 0,
                "total_storage_mb": 0,
                "last_updated": None
            }
            
            # Analyze enhanced analysis data
            if self.enhanced_analysis_dir.exists():
                newest_time = 0
                total_size = 0
                
                for category_dir in self.enhanced_analysis_dir.iterdir():
                    if not category_dir.is_dir():
                        continue
                    
                    category_name = category_dir.name
                    enhanced_files = list(category_dir.glob("*_enhanced.md"))
                    category_count = len(enhanced_files)
                    category_size = sum(f.stat().st_size for f in enhanced_files)
                    
                    stats["categories"][category_name] = {
                        "count": category_count,
                        "size_mb": round(category_size / 1024 / 1024, 2)
                    }
                    
                    stats["enhanced_videos"] += category_count
                    total_size += category_size
                    
                    # Track newest modification time
                    for f in enhanced_files:
                        mtime = f.stat().st_mtime
                        if mtime > newest_time:
                            newest_time = mtime
                
                stats["total_storage_mb"] = round(total_size / 1024 / 1024, 2)
                
                if newest_time > 0:
                    stats["last_updated"] = datetime.fromtimestamp(newest_time).isoformat()
            
            # Count feedback entries
            feedback_file = self.feedback_dir / "feedback.jsonl"
            if feedback_file.exists():
                try:
                    with open(feedback_file, "r", encoding="utf-8") as f:
                        stats["feedback_entries"] = sum(1 for line in f if line.strip())
                except Exception as e:
                    logger.warning(f"Error counting feedback entries: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting data statistics: {e}")
            return {
                "enhanced_videos": 0,
                "categories": {},
                "feedback_entries": 0,
                "total_storage_mb": 0,
                "error": str(e)
            }
    
    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, Any]:
        """
        Clean up data older than specified days.
        
        Args:
            days_old: Number of days after which data is considered old
            
        Returns:
            Cleanup summary
        """
        try:
            import time
            
            cutoff_time = time.time() - (days_old * 24 * 60 * 60)
            cleanup_summary = {
                "files_removed": 0,
                "size_freed_mb": 0,
                "categories_processed": 0
            }
            
            if not self.enhanced_analysis_dir.exists():
                return cleanup_summary
            
            for category_dir in self.enhanced_analysis_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                
                cleanup_summary["categories_processed"] += 1
                
                for file_path in category_dir.iterdir():
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleanup_summary["files_removed"] += 1
                        cleanup_summary["size_freed_mb"] += file_size
                
                # Remove empty directories
                if not any(category_dir.iterdir()):
                    category_dir.rmdir()
            
            cleanup_summary["size_freed_mb"] = round(cleanup_summary["size_freed_mb"] / 1024 / 1024, 2)
            
            logger.info(f"Cleanup completed: {cleanup_summary}")
            return cleanup_summary
            
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
            return {
                "files_removed": 0,
                "size_freed_mb": 0,
                "categories_processed": 0,
                "error": str(e)
            }