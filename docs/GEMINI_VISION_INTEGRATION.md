# Gemini Vision Integration - Stage 1: Multimodal Ingestion

## Overview

This document describes the implementation of Gemini Vision integration for Stage 1 of the Video-to-Anything pipeline. The integration enables deep visual context extraction from YouTube videos alongside existing Speech-to-Text (STT) capabilities.

## Architecture

### Stage 1: Multimodal Ingestion & Analysis

The enhanced pipeline now processes both **audio** and **visual** modalities:

```
YouTube Video URL
    │
    ├─→ Audio/Text Processing (existing)
    │   ├─ YouTube Transcript API (preferred)
    │   ├─ Google STT v2 (fallback)
    │   └─ Gemini text analysis
    │
    └─→ Visual Processing (NEW)
        ├─ Frame extraction (opencv-python)
        ├─ Gemini Vision analysis
        └─ Visual element extraction (code, diagrams, UI, terminal, text)
    │
    ↓
VideoPack Artifact
    ├─ audio_context (transcript + analysis)
    └─ visual_context (visual elements + summary)
```

## Implementation Details

### 1. Schema Extensions (`videopack/schema.py`)

Added two new Pydantic models to support visual context:

#### VisualElement
```python
class VisualElement(BaseModel):
    """Represents visual elements extracted from video frames"""
    timestamp: float              # When element appears in video
    element_type: str             # code|diagram|UI|terminal|text
    content: str                  # Extracted content or description
    confidence: float             # 0.0-1.0 confidence score
    frame_path: Optional[str]     # Path to saved frame image
```

#### VisualContext
```python
class VisualContext(BaseModel):
    """Visual context extracted from video frames using Gemini Vision"""
    visual_elements: List[VisualElement]
    summary: Optional[str]
    frame_analysis_count: int
    processing_timestamp: Optional[datetime]
```

#### Updated VideoPackV0
```python
class VideoPackV0(BaseModel):
    # ... existing fields ...

    # Stage 1: Multimodal Ingestion - Visual context from Gemini Vision
    visual_context: Optional[VisualContext] = None
```

### 2. GeminiService Enhancements (`services/ai/gemini_service.py`)

Added two key methods for visual processing:

#### extract_video_frames()
```python
async def extract_video_frames(
    self,
    video_path: Union[str, Path],
    *,
    frame_rate: Optional[int] = None,    # Frames per second to extract
    max_frames: int = 30,                 # Maximum frames to extract
    output_dir: Optional[Path] = None
) -> List[Dict[str, Any]]
```

**Features:**
- Uses OpenCV (cv2) for frame extraction
- Configurable sampling rate (default: 1 frame/second)
- Saves frames as JPG images with timestamps
- Returns frame metadata (timestamp, path, frame_number)

#### analyze_video_frames()
```python
async def analyze_video_frames(
    self,
    frames_info: List[Dict[str, Any]],
    *,
    analysis_prompt: Optional[str] = None,
    batch_size: int = 5,
    **kwargs
) -> Dict[str, Any]
```

**Features:**
- Analyzes frames using Gemini 2.0 Flash Vision
- Default prompt targets: code snippets, diagrams, UI elements, terminal output, text
- Batch processing with rate limiting
- JSON parsing with fallback handling
- Generates overall summary of visual content

### 3. EnhancedVideoProcessor Integration (`backend/enhanced_video_processor.py`)

#### Initialization
```python
def __init__(self):
    # ... existing initialization ...

    # Initialize Gemini Vision service if available
    if GEMINI_VISION_AVAILABLE and self.gemini_api_key:
        config = GeminiConfig(
            api_key=self.gemini_api_key,
            model_name="gemini-2.0-flash-exp",
            temperature=0.2,
            max_output_tokens=4096
        )
        self.gemini_vision = GeminiService(config)
```

#### Visual Context Extraction
```python
async def _extract_visual_context(
    self,
    video_url: str,
    video_id: str
) -> Dict[str, Any]
```

**Implementation:**
1. Checks if Gemini Vision service is available
2. Uses `process_youtube()` to analyze video directly from URL
3. Extracts visual elements with structured JSON response
4. Parses and categorizes visual elements by type
5. Returns VisualContext-compatible dictionary

#### Enhanced Markdown Generation

Updated `_generate_enhanced_markdown()` to include visual context section:

```markdown
## 🖼️ Visual Context Analysis (Stage 1: Multimodal Ingestion)

### Summary
[Visual content summary]

### Visual Elements Detected (N elements)

#### 💻 Code
**[2:30]** (confidence: 0.95)
```
def process_video(url):
    # Extracted code snippet
```

#### 📊 Diagram
**[5:45]** (confidence: 0.88)
```
Architecture diagram showing microservices architecture
```
```

## Usage

### Basic Example

```python
from src.youtube_extension.backend.enhanced_video_processor import EnhancedVideoProcessor

processor = EnhancedVideoProcessor()

# Process video with multimodal analysis
result = await processor.process_video("https://www.youtube.com/watch?v=VIDEO_ID")

# Access visual context
visual_context = result['visual_context']
visual_elements = visual_context['visual_elements']

# Elements are categorized by type
for elem in visual_elements:
    print(f"[{elem['timestamp']}s] {elem['element_type']}: {elem['content']}")
```

### Environment Configuration

Required environment variables in `.env`:

```bash
# Required for Gemini Vision
GEMINI_API_KEY=your-gemini-api-key-here
GOOGLE_API_KEY=${GEMINI_API_KEY}  # Alias

# Optional for frame extraction from downloaded videos
# (Not required if using YouTube URL directly with Gemini)
# pip install opencv-python
```

### Dependencies

```bash
# Core dependencies (already included)
pip install google-generativeai
pip install pydantic
pip install aiohttp

# Optional: For local video frame extraction
pip install opencv-python
```

## Visual Element Types

The system recognizes and categorizes five types of visual elements:

1. **code** 💻
   - Code snippets shown on screen
   - Includes language identification when possible
   - Extracted as text for code generation

2. **diagram** 📊
   - Flowcharts, architecture diagrams
   - System design illustrations
   - Data flow diagrams

3. **UI** 🎨
   - User interface demonstrations
   - UI/UX design elements
   - Application screenshots

4. **terminal** ⌨️
   - Command-line interfaces
   - Terminal commands and output
   - Shell scripts

5. **text** 📝
   - Important text overlays
   - Titles and headings
   - Educational content text

## API Response Format

### Visual Context Structure

```json
{
  "visual_elements": [
    {
      "timestamp": 45.5,
      "element_type": "code",
      "content": "import tensorflow as tf\nmodel = tf.keras.Sequential([...])",
      "confidence": 0.95,
      "frame_path": "/path/to/frame_0010_t45.50s.jpg"
    },
    {
      "timestamp": 120.0,
      "element_type": "diagram",
      "content": "Neural network architecture with 3 hidden layers",
      "confidence": 0.88,
      "frame_path": "/path/to/frame_0024_t120.00s.jpg"
    }
  ],
  "summary": "Video demonstrates TensorFlow neural network implementation with architectural diagrams",
  "frame_analysis_count": 30,
  "processing_timestamp": "2026-03-20T10:45:00.000Z"
}
```

## Testing

### Schema Tests

```python
from src.youtube_extension.videopack.schema import VisualContext, VisualElement

# Create visual element
elem = VisualElement(
    timestamp=10.5,
    element_type="code",
    content="def hello(): print('world')",
    confidence=0.95
)

# Create visual context
context = VisualContext(
    visual_elements=[elem],
    summary="Simple hello world demonstration",
    frame_analysis_count=1
)
```

### Integration Tests

Run the test suite:

```bash
# Run all Gemini Vision tests
pytest tests/test_gemini_vision_integration.py -v

# Run specific test
pytest tests/test_gemini_vision_integration.py::TestVisualContextSchema::test_videopack_with_visual_context -v

# Skip tests requiring API keys
pytest tests/test_gemini_vision_integration.py -v -m "not slow"
```

## Performance Considerations

### Frame Extraction
- Default: 1 frame/second (configurable)
- Max frames: 30 (configurable)
- Typical video (10 min) → 10-30 frames analyzed

### API Costs
- Gemini 2.0 Flash: ~$0.075 per 1K characters
- Typical frame analysis: ~500 tokens per frame
- 30 frames @ ~500 tokens each = ~15K tokens (~$0.0011)
- Total Stage 1 cost per video: **~$0.001-0.01**

### Processing Time
- Frame extraction: ~5-10 seconds
- Gemini Vision analysis: ~2-3 seconds per frame
- 30 frames with batching: ~60-90 seconds
- Total Stage 1 processing: **~1-2 minutes per video**

## Integration with Stage 3: Code Generation

Visual context enhances code generation accuracy by:

1. **Code Structure Understanding**
   - Actual code shown on screen vs. just mentioned
   - Variable names and function signatures
   - Import statements and dependencies

2. **Architecture Awareness**
   - Visual diagrams inform system design
   - Component relationships
   - Data flow patterns

3. **UI/UX Implementation**
   - Exact UI elements demonstrated
   - Layout and styling details
   - Interaction patterns

## Limitations

1. **YouTube URL Processing**
   - Requires Gemini 2.0 Flash or later
   - Not supported with Vertex AI backend
   - May not work with all video types

2. **Frame Extraction**
   - Requires `opencv-python` for local videos
   - Works best with screen recordings and tutorials
   - May miss fast-changing content

3. **Visual Element Detection**
   - Accuracy depends on video quality
   - Works best with clear, high-contrast visuals
   - May miss handwritten diagrams

## Future Enhancements

1. **Intelligent Frame Selection**
   - Scene change detection
   - Focus on frames with code/diagrams
   - Skip redundant frames

2. **Multi-Modal Fusion**
   - Correlate visual elements with transcript timestamps
   - Cross-reference audio and visual content
   - Detect discrepancies

3. **Enhanced Element Extraction**
   - OCR for better code extraction
   - Diagram vectorization
   - UI element bounding boxes

## References

- [Gemini 2.0 Flash Documentation](https://ai.google.dev/gemini-api/docs)
- [VideoPackV0 Schema](../src/youtube_extension/videopack/schema.py)
- [GeminiService Implementation](../src/youtube_extension/services/ai/gemini_service.py)
- [EnhancedVideoProcessor](../src/youtube_extension/backend/enhanced_video_processor.py)
