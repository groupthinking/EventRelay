# 🎯 Video ID Configuration Guide

## Testing vs Production Settings

### 🧪 **TESTING ENVIRONMENT**
- **Default Video ID**: `auJzb1D-fag`
- **Purpose**: Consistent test data across all test files
- **Usage**: All unit tests, integration tests, and development testing
- **Why this ID**: User-specified default for reliable testing

### 🚀 **PRODUCTION ENVIRONMENT**
- **Accepted Input**: Any valid YouTube URL or media type
- **Examples**:
  - `https://www.youtube.com/watch?v=VIDEO_ID`
  - `https://youtu.be/VIDEO_ID`
  - Direct video ID: `VIDEO_ID` (11 characters)
  - Future: Other media platforms as needed

### 🔧 **Implementation Guidelines**

#### For Test Files:
```python
# ✅ CORRECT - Use default test video
video_metadata = VideoMetadata(
    video_id="auJzb1D-fag",
    title="Test Video Tutorial",
    channel="Test Channel",
    duration="PT10M"
)
```

#### For Production Code:
```python
# ✅ CORRECT - Accept any valid input
def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from URL or return ID if already valid"""
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        # Extract from URL
        return extract_from_url(url_or_id)
    elif len(url_or_id) == 11:
        # Assume it's already a video ID
        return url_or_id
    else:
        raise ValueError("Invalid YouTube URL or video ID format")
```

### 📋 **Validation Rules**

#### Testing:
- Must use `auJzb1D-fag` for consistency
- All assertions must expect this exact ID
- No hardcoded URLs in tests

#### Production:
- Validate 11-character video ID format
- Support multiple URL formats
- Graceful error handling for invalid inputs
- Future-proof for additional media types

---

**Key Point**: Testing uses fixed data for consistency, production accepts any valid media input.
