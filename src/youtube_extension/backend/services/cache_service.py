#!/usr/bin/env python3
"""
Cache Service
=============

Extracted cache management business logic.
Handles video processing result caching, statistics, and cleanup operations.
"""

import hashlib
import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from youtube_extension.utils import extract_video_id

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service for managing cached video processing results.
    Provides unified interface for cache operations across different storage formats.
    """
    
    def __init__(self, cache_dir: str = "youtube_processed_videos/markdown_analysis"):
        """
        Initialize cache service.
        
        Args:
            cache_dir: Base directory for cache storage
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Enhanced analysis cache directory
        self.enhanced_cache_dir = Path('youtube_processed_videos') / 'enhanced_analysis'
    
    def _get_cache_key(self, video_url: str) -> str:
        """Generate cache key from video URL"""
        return hashlib.md5(video_url.encode()).hexdigest()[:12]
    
    def get_cached_result(self, video_url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available.
        Checks both legacy markdown_analysis and enhanced_analysis caches.
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            Cached result or None if not found/expired
        """
        try:
            video_id = extract_video_id(video_url)
            
            # Check legacy markdown_analysis cache
            legacy_result = self._get_legacy_cached_result(video_id, video_url)
            if legacy_result:
                return legacy_result
            
            # Check enhanced analysis cache
            enhanced_result = self._get_enhanced_cached_result(video_id, video_url)
            if enhanced_result:
                return enhanced_result
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None
    
    def _get_legacy_cached_result(self, video_id: str, video_url: str) -> Optional[Dict[str, Any]]:
        """Check legacy markdown_analysis cache"""
        try:
            for category_dir in self.cache_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                    
                markdown_file = category_dir / f"{video_id}_analysis.md"
                metadata_file = category_dir / f"{video_id}_metadata.json"
                
                if markdown_file.exists() and metadata_file.exists():
                    # Check if cache is still valid (within 24 hours)
                    age = time.time() - markdown_file.stat().st_mtime
                    if age < 86400:  # 24 hours
                        with open(markdown_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        return {
                            'video_id': video_id,
                            'video_url': video_url,
                            'markdown_content': content,
                            'metadata': metadata,
                            'save_path': str(markdown_file),
                            'cached': True
                        }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error checking legacy cache: {e}")
            return None
    
    def _get_enhanced_cached_result(self, video_id: str, video_url: str) -> Optional[Dict[str, Any]]:
        """Check enhanced_analysis cache"""
        try:
            if not self.enhanced_cache_dir.exists():
                return None
            
            for category_dir in self.enhanced_cache_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                
                # Find latest enhanced markdown for this video_id
                candidates = sorted(category_dir.glob(f"{video_id}_*_enhanced.md"))
                if candidates:
                    md_path = candidates[-1]
                    
                    # Find matching metadata file
                    meta_candidates = sorted(category_dir.glob(f"{video_id}_*_metadata.json"))
                    metadata = {}
                    if meta_candidates:
                        with open(meta_candidates[-1], 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    with open(md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    return {
                        'video_id': video_id,
                        'video_url': video_url,
                        'markdown_content': content,
                        'metadata': metadata,
                        'save_path': str(md_path),
                        'cached': True
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error checking enhanced cache: {e}")
            return None
    
    def clear_cache(self, video_url: str = None):
        """
        Clear cache for specific video or all videos.
        
        Args:
            video_url: Specific video URL to clear, or None to clear all
        """
        try:
            if video_url:
                self._clear_video_cache(video_url)
            else:
                self._clear_all_cache()
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def _clear_video_cache(self, video_url: str):
        """Clear cache for specific video"""
        try:
            video_id = extract_video_id(video_url)
            
            # Clear from legacy cache
            for category_dir in self.cache_dir.iterdir():
                if category_dir.is_dir():
                    markdown_file = category_dir / f"{video_id}_analysis.md"
                    metadata_file = category_dir / f"{video_id}_metadata.json"
                    
                    if markdown_file.exists():
                        markdown_file.unlink()
                    if metadata_file.exists():
                        metadata_file.unlink()
            
            # Clear from enhanced cache
            if self.enhanced_cache_dir.exists():
                for category_dir in self.enhanced_cache_dir.iterdir():
                    if category_dir.is_dir():
                        # Remove all files for this video_id
                        for file_path in category_dir.glob(f"{video_id}_*"):
                            file_path.unlink()
            
            logger.info(f"Cleared cache for video: {video_id}")
            
        except Exception as e:
            logger.error(f"Error clearing video cache: {e}")
    
    def _clear_all_cache(self):
        """Clear all cached content"""
        try:
            # Clear legacy cache
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Clear enhanced cache
            if self.enhanced_cache_dir.exists():
                shutil.rmtree(self.enhanced_cache_dir)
            
            logger.info("Cleared all cache")
            
        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        try:
            stats = {
                "total_cached_videos": 0,
                "categories": {},
                "total_size_mb": 0,
                "oldest_cache": None,
                "newest_cache": None,
                "enhanced_cache_stats": {}
            }
            
            # Analyze legacy cache
            self._analyze_legacy_cache_stats(stats)
            
            # Analyze enhanced cache
            self._analyze_enhanced_cache_stats(stats)
            
            # Convert total size to MB
            stats["total_size_mb"] = round(stats["total_size_mb"] / 1024 / 1024, 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "total_cached_videos": 0,
                "categories": {},
                "total_size_mb": 0,
                "error": str(e)
            }
    
    def _analyze_legacy_cache_stats(self, stats: Dict[str, Any]):
        """Analyze legacy cache statistics"""
        if not self.cache_dir.exists():
            return
        
        oldest_time = float('inf')
        newest_time = 0
        
        for category_dir in self.cache_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category_name = category_dir.name
            markdown_files = list(category_dir.glob("*_analysis.md"))
            category_count = len(markdown_files)
            category_size = sum(f.stat().st_size for f in markdown_files)
            
            stats["categories"][category_name] = {
                "count": category_count,
                "size_mb": round(category_size / 1024 / 1024, 2),
                "type": "legacy"
            }
            
            stats["total_cached_videos"] += category_count
            stats["total_size_mb"] += category_size
            
            # Track timestamps
            for f in markdown_files:
                mtime = f.stat().st_mtime
                if mtime < oldest_time:
                    oldest_time = mtime
                if mtime > newest_time:
                    newest_time = mtime
        
        # Set timestamp info
        if oldest_time != float('inf'):
            stats["oldest_cache"] = datetime.fromtimestamp(oldest_time).isoformat()
        if newest_time > 0:
            stats["newest_cache"] = datetime.fromtimestamp(newest_time).isoformat()
    
    def _analyze_enhanced_cache_stats(self, stats: Dict[str, Any]):
        """Analyze enhanced cache statistics"""
        if not self.enhanced_cache_dir.exists():
            return
        
        enhanced_stats = {
            "total_videos": 0,
            "categories": {},
            "total_size_mb": 0
        }
        
        for category_dir in self.enhanced_cache_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category_name = f"enhanced_{category_dir.name}"
            enhanced_files = list(category_dir.glob("*_enhanced.md"))
            category_count = len(enhanced_files)
            category_size = sum(f.stat().st_size for f in enhanced_files)
            
            enhanced_stats["categories"][category_name] = {
                "count": category_count,
                "size_mb": round(category_size / 1024 / 1024, 2),
                "type": "enhanced"
            }
            
            enhanced_stats["total_videos"] += category_count
            enhanced_stats["total_size_mb"] += category_size
            
            # Also include in main stats
            stats["categories"][category_name] = enhanced_stats["categories"][category_name]
            stats["total_cached_videos"] += category_count
            stats["total_size_mb"] += category_size
        
        stats["enhanced_cache_stats"] = enhanced_stats
    
    def get_video_cache_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cache information for specific video.
        
        Args:
            video_id: Video ID to lookup
            
        Returns:
            Cache information or None if not found
        """
        try:
            # Search legacy cache
            for category_dir in self.cache_dir.iterdir():
                if not category_dir.is_dir():
                    continue
                    
                analysis_path = category_dir / f"{video_id}_analysis.md"
                metadata_path = category_dir / f"{video_id}_metadata.json"
                
                if analysis_path.exists():
                    with open(analysis_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    metadata = {}
                    if metadata_path.exists():
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    
                    # Skip frontmatter if present
                    markdown_content = content
                    if content.startswith('---'):
                        end_idx = content.find('---', 3)
                        if end_idx != -1:
                            markdown_content = content[end_idx + 3:].strip()
                    
                    # File statistics
                    file_stats = analysis_path.stat()
                    age_hours = (time.time() - file_stats.st_mtime) / 3600
                    
                    return {
                        "video_id": video_id,
                        "markdown_content": markdown_content,
                        "metadata": metadata,
                        "cached": True,
                        "cache_age_hours": round(age_hours, 2),
                        "file_size": file_stats.st_size,
                        "last_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                        "cache_type": "legacy"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting video cache info: {e}")
            return None