#!/usr/bin/env python3
"""
AUTHENTICITY VALIDATION SYSTEM
Detects simulation artifacts and enforces real processing
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [VALIDATOR] %(message)s'
)
logger = logging.getLogger("authenticity_validator")

class AuthenticityValidator:
    """Bulletproof validator to detect simulation artifacts"""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.validation_errors = []
        self.validation_warnings = []
        
    def validate_processing_result(self, result: Dict[str, Any]) -> bool:
        """Comprehensive validation of processing results"""
        
        logger.info("🔍 Starting authenticity validation...")
        
        # Reset validation state
        self.validation_errors = []
        self.validation_warnings = []
        
        # Run all validation checks
        self._validate_processing_time(result)
        self._validate_transcript_data(result)
        self._validate_video_metadata(result)
        self._validate_actionable_content(result)
        self._validate_gdrive_results(result)
        self._validate_timestamp_consistency(result)
        
        # Determine validation result
        if self.validation_errors:
            logger.error(f"❌ VALIDATION FAILED: {len(self.validation_errors)} errors detected")
            for error in self.validation_errors:
                logger.error(f"   ERROR: {error}")
            return False
        
        if self.validation_warnings:
            logger.warning(f"⚠️ VALIDATION WARNINGS: {len(self.validation_warnings)} warnings")
            for warning in self.validation_warnings:
                logger.warning(f"   WARNING: {warning}")
        
        logger.info("✅ AUTHENTICITY VALIDATION PASSED")
        return True
    
    def _validate_processing_time(self, result: Dict[str, Any]):
        """Validate processing time is realistic"""
        processing_time = result.get('processing_time', 0)
        
        if processing_time <= 0:
            self.validation_errors.append("Processing time is zero or negative")
        elif processing_time < 0.5:
            self.validation_errors.append(f"Processing time too fast: {processing_time}s (minimum: 0.5s)")
        elif processing_time > 300:
            self.validation_errors.append(f"Processing time too slow: {processing_time}s (maximum: 300s)")
        elif processing_time < 1.0:
            self.validation_warnings.append(f"Processing time unusually fast: {processing_time}s")
    
    def _validate_transcript_data(self, result: Dict[str, Any]):
        """Validate transcript data authenticity"""
        transcript_data = result.get('transcript_data', [])
        
        if not transcript_data:
            self.validation_errors.append("Transcript data is empty")
            return
        
        if not isinstance(transcript_data, list):
            self.validation_errors.append("Transcript data is not a list")
            return
        
        # Check minimum segment count
        if len(transcript_data) < 5:
            self.validation_errors.append(f"Too few transcript segments: {len(transcript_data)} (minimum: 5)")
        
        # Validate segment structure
        for i, segment in enumerate(transcript_data[:10]):  # Check first 10 segments
            if not isinstance(segment, dict):
                self.validation_errors.append(f"Segment {i} is not a dictionary")
                continue
            
            if 'text' not in segment:
                self.validation_errors.append(f"Segment {i} missing 'text' field")
            elif not segment['text'] or len(segment['text'].strip()) < 5:
                self.validation_warnings.append(f"Segment {i} has very short text")
            
            # Check for timestamp fields
            has_timestamp = any(key in segment for key in ['start', 'timestamp', 'duration'])
            if not has_timestamp:
                self.validation_warnings.append(f"Segment {i} missing timestamp information")
        
        # Check total text length
        total_text = ' '.join([seg.get('text', '') for seg in transcript_data])
        if len(total_text) < 200:
            self.validation_errors.append(f"Total transcript text too short: {len(total_text)} chars (minimum: 200)")
    
    def _validate_video_metadata(self, result: Dict[str, Any]):
        """Validate video metadata"""
        video_id = result.get('video_id', '')
        video_url = result.get('video_url', '')
        
        if not video_id:
            self.validation_errors.append("Video ID is missing")
        elif len(video_id) != 11:
            self.validation_errors.append(f"Invalid video ID format: {video_id} (should be 11 characters)")
        elif not video_id.replace('-', '').replace('_', '').isalnum():
            self.validation_errors.append(f"Video ID contains invalid characters: {video_id}")
        
        if not video_url:
            self.validation_warnings.append("Video URL is missing")
        elif 'youtube.com' not in video_url and 'youtu.be' not in video_url:
            self.validation_warnings.append(f"Video URL doesn't appear to be YouTube: {video_url}")
    
    def _validate_actionable_content(self, result: Dict[str, Any]):
        """Validate actionable content generation"""
        actionable_content = result.get('actionable_content', {})
        
        if not actionable_content:
            self.validation_errors.append("Actionable content is missing")
            return
        
        # Validate category
        category = actionable_content.get('category', '')
        valid_categories = ['Educational_Content', 'Business_Professional', 'Creative_DIY', 'Health_Fitness_Cooking']
        if category not in valid_categories:
            self.validation_errors.append(f"Invalid category: {category}")
        
        # Validate actions
        actions = actionable_content.get('actions', [])
        if not actions:
            self.validation_errors.append("No actions generated")
        elif len(actions) < 2:
            self.validation_warnings.append(f"Very few actions generated: {len(actions)}")
        
        # Validate action structure
        for i, action in enumerate(actions):
            required_fields = ['type', 'title', 'description', 'estimated_time', 'priority']
            for field in required_fields:
                if field not in action:
                    self.validation_errors.append(f"Action {i} missing '{field}' field")
        
        # Validate transcript summary
        transcript_summary = actionable_content.get('transcript_summary', '')
        if not transcript_summary:
            self.validation_warnings.append("Transcript summary is empty")
        elif len(transcript_summary) < 100:
            self.validation_warnings.append("Transcript summary is very short")
    
    def _validate_gdrive_results(self, result: Dict[str, Any]):
        """Validate Google Drive save results"""
        gdrive_result = result.get('gdrive_result', {})
        
        if not gdrive_result:
            self.validation_errors.append("Google Drive result is missing")
            return
        
        if not gdrive_result.get('success', False):
            self.validation_errors.append("Google Drive save was not successful")
        
        file_path = gdrive_result.get('file_path', '')
        if not file_path:
            self.validation_errors.append("Google Drive file path is missing")
        elif not Path(file_path).exists():
            self.validation_errors.append(f"Google Drive result file does not exist: {file_path}")
        
        # Validate file content
        if file_path and Path(file_path).exists():
            try:
                with open(file_path, 'r') as f:
                    saved_data = json.load(f)
                
                if not saved_data.get('real_processing_validated', False):
                    self.validation_errors.append("Saved file lacks real processing validation flag")
                
                if saved_data.get('video_id') != result.get('video_id'):
                    self.validation_errors.append("Video ID mismatch between result and saved file")
                    
            except Exception as e:
                self.validation_errors.append(f"Cannot validate saved file: {e}")
    
    def _validate_timestamp_consistency(self, result: Dict[str, Any]):
        """Validate timestamp consistency"""
        timestamp = result.get('timestamp', '')
        
        if not timestamp:
            self.validation_warnings.append("Processing timestamp is missing")
            return
        
        try:
            processing_datetime = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            current_datetime = datetime.now()
            
            # Check if timestamp is reasonable (within last hour)
            time_diff = abs((current_datetime - processing_datetime).total_seconds())
            if time_diff > 3600:  # 1 hour
                self.validation_warnings.append(f"Processing timestamp seems old: {time_diff}s ago")
            
        except Exception as e:
            self.validation_errors.append(f"Invalid timestamp format: {timestamp}")
    
    def validate_result_file(self, file_path: str) -> bool:
        """Validate a saved result file"""
        
        logger.info(f"🔍 Validating result file: {file_path}")
        
        if not Path(file_path).exists():
            logger.error(f"❌ Result file does not exist: {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                result = json.load(f)
            
            return self.validate_processing_result(result)
            
        except Exception as e:
            logger.error(f"❌ Cannot validate result file: {e}")
            return False
    
    def validate_directory(self, directory_path: str) -> Dict[str, Any]:
        """Validate all result files in a directory"""
        
        logger.info(f"🔍 Validating all files in: {directory_path}")
        
        directory = Path(directory_path)
        if not directory.exists():
            logger.error(f"❌ Directory does not exist: {directory_path}")
            return {'success': False, 'error': 'Directory not found'}
        
        result_files = list(directory.glob('**/*_results.json'))
        if not result_files:
            logger.warning(f"⚠️ No result files found in: {directory_path}")
            return {'success': True, 'files_validated': 0, 'warnings': ['No result files found']}
        
        validation_summary = {
            'total_files': len(result_files),
            'valid_files': 0,
            'invalid_files': 0,
            'warnings': 0,
            'errors': 0,
            'file_results': []
        }
        
        for file_path in result_files:
            logger.info(f"Validating: {file_path.name}")
            
            is_valid = self.validate_result_file(str(file_path))
            
            file_result = {
                'file': str(file_path),
                'valid': is_valid,
                'errors': len(self.validation_errors),
                'warnings': len(self.validation_warnings)
            }
            
            validation_summary['file_results'].append(file_result)
            
            if is_valid:
                validation_summary['valid_files'] += 1
            else:
                validation_summary['invalid_files'] += 1
            
            validation_summary['errors'] += len(self.validation_errors)
            validation_summary['warnings'] += len(self.validation_warnings)
        
        # Calculate success rate
        success_rate = (validation_summary['valid_files'] / validation_summary['total_files']) * 100
        validation_summary['success_rate'] = success_rate
        
        logger.info(f"📊 VALIDATION SUMMARY:")
        logger.info(f"   Total Files: {validation_summary['total_files']}")
        logger.info(f"   Valid Files: {validation_summary['valid_files']}")
        logger.info(f"   Invalid Files: {validation_summary['invalid_files']}")
        logger.info(f"   Success Rate: {success_rate:.1f}%")
        
        return validation_summary

def main():
    """Main validation function"""
    
    if len(sys.argv) < 2:
        print("Usage: python validate_authenticity.py <file_or_directory> [--strict-mode]")
        sys.exit(1)
    
    target_path = sys.argv[1]
    strict_mode = '--strict-mode' in sys.argv
    
    validator = AuthenticityValidator(strict_mode=strict_mode)
    
    if Path(target_path).is_file():
        # Validate single file
        success = validator.validate_result_file(target_path)
        sys.exit(0 if success else 1)
    
    elif Path(target_path).is_dir():
        # Validate directory
        summary = validator.validate_directory(target_path)
        
        if strict_mode and summary['invalid_files'] > 0:
            logger.error("❌ STRICT MODE: Validation failed due to invalid files")
            sys.exit(1)
        
        logger.info("✅ Directory validation complete")
        sys.exit(0)
    
    else:
        logger.error(f"❌ Path does not exist: {target_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()