"""
Utilities Module
================

Common utilities for YouTube Extension.
"""

from .proxy import (
    get_proxy_dict,
    get_proxy_url,
    get_transcript_proxy_config,
    redact_proxy_credentials,
)
from .video_utils import (
    extract_video_id,
    format_duration,
    is_valid_video_id,
    normalize_video_url,
    parse_duration_to_seconds,
)

__all__ = [
    'extract_video_id',
    'is_valid_video_id',
    'normalize_video_url',
    'parse_duration_to_seconds',
    'format_duration',
    'get_proxy_url',
    'get_proxy_dict',
    'get_transcript_proxy_config',
    'redact_proxy_credentials',
]
