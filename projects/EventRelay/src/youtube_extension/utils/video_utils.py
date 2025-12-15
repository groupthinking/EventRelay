#!/usr/bin/env python3
"""
Video Utilities
================

Shared utilities for video processing operations.
Consolidates duplicated video-related helper functions across the codebase.
"""

import re
from typing import Optional


def extract_video_id(url: str) -> str:
    """
    Extract video ID from YouTube URL or validate direct video ID.
    
    This function supports multiple YouTube URL formats:
    - Standard watch URLs: https://www.youtube.com/watch?v=VIDEO_ID
    - Short URLs: https://youtu.be/VIDEO_ID
    - Embed URLs: https://www.youtube.com/embed/VIDEO_ID
    - Shorts URLs: https://www.youtube.com/shorts/VIDEO_ID
    - Direct video IDs: VIDEO_ID (11 characters)
    
    Args:
        url: YouTube video URL or video ID
        
    Returns:
        Extracted 11-character video ID
        
    Raises:
        ValueError: If video ID cannot be extracted from the input
        
    Examples:
        >>> extract_video_id("https://www.youtube.com/watch?v=auJzb1D-fag")
        'auJzb1D-fag'
        >>> extract_video_id("https://youtu.be/auJzb1D-fag")
        'auJzb1D-fag'
        >>> extract_video_id("auJzb1D-fag")
        'auJzb1D-fag'
    """
    # Comprehensive patterns for YouTube URL formats
    patterns = [
        # Standard watch URL with query parameters
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        # Shorts format
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
        # Embed format variations
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        # /v/ format
        r'youtube\.com/v/([^&\n?#]+)',
        # General format with v= parameter
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        # Watch URL with various parameters
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
        # Direct 11-character ID
        r'^([0-9A-Za-z_-]{11})$'
    ]
    
    # Try each pattern
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # Validate it's exactly 11 characters (YouTube standard)
            if len(video_id) == 11:
                return video_id
    
    raise ValueError(
        f"Could not extract valid YouTube video ID from: {url}. "
        f"Please provide a valid YouTube URL or 11-character video ID."
    )


def is_valid_video_id(video_id: Optional[str]) -> bool:
    """
    Check if a string is a valid YouTube video ID format.
    
    Args:
        video_id: String to validate
        
    Returns:
        True if the string matches YouTube video ID format, False otherwise
        
    Examples:
        >>> is_valid_video_id("auJzb1D-fag")
        True
        >>> is_valid_video_id("invalid")
        False
        >>> is_valid_video_id("auJzb1D-fag123")  # Too long
        False
    """
    if not video_id or not isinstance(video_id, str):
        return False
    
    # YouTube video IDs are exactly 11 characters: alphanumeric, underscore, hyphen
    pattern = r'^[0-9A-Za-z_-]{11}$'
    return bool(re.match(pattern, video_id))


def normalize_video_url(url: str) -> str:
    """
    Normalize a YouTube URL to standard format.
    
    Args:
        url: YouTube video URL or video ID
        
    Returns:
        Normalized YouTube watch URL
        
    Examples:
        >>> normalize_video_url("auJzb1D-fag")
        'https://www.youtube.com/watch?v=auJzb1D-fag'
        >>> normalize_video_url("https://youtu.be/auJzb1D-fag")
        'https://www.youtube.com/watch?v=auJzb1D-fag'
    """
    video_id = extract_video_id(url)
    return f"https://www.youtube.com/watch?v={video_id}"


def parse_duration_to_seconds(duration: str) -> int:
    """
    Parse ISO 8601 duration (YouTube format) to total seconds.
    
    Args:
        duration: ISO 8601 duration string (e.g., "PT1H2M3S")
        
    Returns:
        Total duration in seconds
        
    Examples:
        >>> parse_duration_to_seconds("PT1H2M3S")
        3723
        >>> parse_duration_to_seconds("PT5M30S")
        330
        >>> parse_duration_to_seconds("PT45S")
        45
    """
    # Parse PT1H2M3S format
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds


def format_duration(duration: str) -> str:
    """
    Format ISO 8601 duration to human-readable string.
    
    Args:
        duration: ISO 8601 duration string (e.g., "PT1H2M3S")
        
    Returns:
        Human-readable duration string
        
    Examples:
        >>> format_duration("PT1H2M3S")
        '1h 2m 3s'
        >>> format_duration("PT5M30S")
        '5m 30s'
        >>> format_duration("PT45S")
        '45s'
    """
    # Parse PT1H2M3S format
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    
    if not match:
        return duration
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"
