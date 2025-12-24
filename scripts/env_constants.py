"""
Shared constants for environment configuration tools
"""

# Placeholder values that should be replaced
PLACEHOLDER_VALUES = [
    'your-openai-key',
    'your-anthropic-key', 
    'your-gemini-key',
    'your-assemblyai-key',
    'AIzaSyYourProductionKeyGoesHere',
    '${GEMINI_API_KEY}',
]

# Required AI provider keys (user needs at least ONE)
REQUIRED_AI_KEYS = [
    'GEMINI_API_KEY',
    'OPENAI_API_KEY',
]

# Recommended but optional keys
RECOMMENDED_KEYS = [
    'YOUTUBE_API_KEY',
]

# API key validation patterns
KEY_PATTERNS = {
    'GEMINI_API_KEY': r'^[A-Za-z0-9_-]{30,}$',
    'OPENAI_API_KEY': r'^sk-[A-Za-z0-9]{20,}$',
    'ANTHROPIC_API_KEY': r'^sk-ant-[A-Za-z0-9_-]{20,}$',
    'YOUTUBE_API_KEY': r'^AIza[A-Za-z0-9_-]{35}$',  # Typically 39 chars total
    'ASSEMBLYAI_API_KEY': r'^[a-f0-9]{32}$',
}
