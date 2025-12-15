#!/usr/bin/env python3
"""
Development Artifacts Cleanup Script
===================================

Safely archives or removes development/test artifacts while preserving
production-relevant data.
"""

import os
import shutil
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DevArtifactsCleaner:
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.archive_dir = self.base_path / "archived_dev_artifacts"
        self.cleanup_report = {
            "timestamp": datetime.now().isoformat(),
            "directories_analyzed": [],
            "files_archived": [],
            "files_removed": [],
            "space_freed_mb": 0
        }
        
    def analyze_directory(self, dir_path: Path) -> Dict[str, any]:
        """Analyze a directory for cleanup potential"""
        if not dir_path.exists():
            return {"exists": False, "path": str(dir_path)}
            
        total_size = 0
        file_count = 0
        file_types = {}
        
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                file_count += 1
                size = file_path.stat().st_size
                total_size += size
                
                ext = file_path.suffix.lower()
                if ext not in file_types:
                    file_types[ext] = {"count": 0, "size": 0}
                file_types[ext]["count"] += 1
                file_types[ext]["size"] += size
                
        return {
            "exists": True,
            "path": str(dir_path),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "file_types": file_types
        }
        
    def should_preserve(self, file_path: Path) -> bool:
        """Determine if a file should be preserved"""
        # Preserve recent files (last 7 days)
        try:
            mtime = file_path.stat().st_mtime
            age_days = (datetime.now().timestamp() - mtime) / (86400)
            if age_days < 7:
                return True
        except:
            pass
            
        # Preserve files with certain patterns
        preserve_patterns = [
            "production", "prod_", "release", "deploy",
            "critical", "important", "backup"
        ]
        
        file_str = str(file_path).lower()
        for pattern in preserve_patterns:
            if pattern in file_str:
                return True
                
        return False
        
    def archive_directory(self, dir_path: Path, archive_name: str):
        """Archive a directory"""
        if not dir_path.exists():
            return
            
        # Create archive directory
        self.archive_dir.mkdir(exist_ok=True)
        
        # Create timestamp-based archive
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.archive_dir / f"{archive_name}_{timestamp}"
        
        # Move directory to archive
        shutil.move(str(dir_path), str(archive_path))
        logger.info(f"Archived {dir_path} to {archive_path}")
        
        self.cleanup_report["directories_analyzed"].append(str(dir_path))
        
    def clean_output_directories(self):
        """Clean up output directories"""
        output_dirs = [
            ("gdrive_results", "archive"),
            ("gemini_working_results", "archive"),
            ("grok4_processed_videos", "archive"),
            ("multi_llm_results", "archive"),
            ("ultimate_results", "archive"),
            ("workflow_output", "archive"),
            ("workflow_results", "archive"),
            ("youtube_processed_videos", "preserve_recent"),
            ("results", "preserve_recent"),
        ]
        
        for dir_name, action in output_dirs:
            dir_path = self.base_path / dir_name
            
            if not dir_path.exists():
                continue
                
            analysis = self.analyze_directory(dir_path)
            self.cleanup_report["directories_analyzed"].append(analysis)
            
            if action == "archive":
                self.archive_directory(dir_path, dir_name)
                self.cleanup_report["space_freed_mb"] += analysis.get("total_size_mb", 0)
                
            elif action == "preserve_recent":
                # Clean old files but preserve recent ones
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file() and not self.should_preserve(file_path):
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        file_path.unlink()
                        self.cleanup_report["files_removed"].append(str(file_path))
                        self.cleanup_report["space_freed_mb"] += size_mb
                        
    def clean_simulation_artifacts(self):
        """Clean up simulation and test artifacts"""
        simulation_files = [
            "FINAL_SIMULATION_CLEANUP_REPORT.json",
            "verification_log.json",
            "action_implementation.log",
            "enhanced_processing.log",
            "quality_agent.log",
        ]
        
        for file_name in simulation_files:
            file_path = self.base_path / file_name
            if file_path.exists():
                # Archive instead of delete
                archive_path = self.archive_dir / "logs"
                archive_path.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(archive_path / file_name))
                self.cleanup_report["files_archived"].append(file_name)
                
    def generate_report(self):
        """Generate cleanup report"""
        report_path = self.base_path / "CLEANUP_REPORT.json"
        with open(report_path, "w") as f:
            json.dump(self.cleanup_report, f, indent=2)
            
        logger.info(f"Cleanup report saved to {report_path}")
        logger.info(f"Total space freed: {self.cleanup_report['space_freed_mb']:.2f} MB")
        logger.info(f"Files archived: {len(self.cleanup_report['files_archived'])}")
        logger.info(f"Files removed: {len(self.cleanup_report['files_removed'])}")
        
    def run(self, dry_run: bool = False):
        """Run the cleanup process"""
        logger.info("Starting development artifacts cleanup...")
        
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            
        # Analyze directories
        self.clean_output_directories()
        self.clean_simulation_artifacts()
        
        # Generate report
        self.generate_report()
        
        logger.info("Cleanup complete!")
        

if __name__ == "__main__":
    import sys
    
    dry_run = "--dry-run" in sys.argv
    cleaner = DevArtifactsCleaner()
    cleaner.run(dry_run=dry_run)
