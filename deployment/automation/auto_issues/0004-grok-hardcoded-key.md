Title: Security — Hardcoded Grok API key in source

Summary
-------
`build_extensions/uvai-platform/core/ai-reasoning-engine/video-analyzer/grok_enhanced_youtube_error.py` contains a hardcoded API key assigned to `self.grok_api_key`. This must be removed and rotated immediately.

Location
--------
- `build_extensions/uvai-platform/core/ai-reasoning-engine/video-analyzer/grok_enhanced_youtube_error.py`

Remediation
---------
1. Remove the hardcoded key and replace with reading from an environment variable: `os.getenv('GROK_API_KEY')`.
2. Rotate the key in the provider console and revoke the hardcoded one.
3. Add this repository to secret scanning tools and rotate any exposed keys.

Suggested labels: security, urgent
