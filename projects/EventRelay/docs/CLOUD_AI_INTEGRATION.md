# Cloud AI Integration Guide

This document describes the comprehensive cloud AI/ML video processing integration added to the YouTube Extension platform.

## Overview

The cloud AI integration provides unified access to major cloud AI/ML providers for advanced video analysis capabilities:

- **Google Cloud Video Intelligence & Vision API**
- **Amazon Rekognition**
- **Microsoft Azure AI Vision** 
- **Apple FastVLM**

## Features

### Supported Analysis Types

| Analysis Type | Google Cloud | AWS Rekognition | Azure Vision | Apple FastVLM |
|---------------|-------------|-----------------|--------------|---------------|
| Object Tracking | ✅ | ✅ | ✅ | ✅ |
| OCR/Text Detection | ✅ | ✅ | ✅ | ✅ |
| Label Detection | ✅ | ✅ | ✅ | ✅ |
| Logo Recognition | ✅ | ❌ | ❌ | ❌ |
| Shot Detection | ✅ | ❌ | ❌ | ❌ |
| Face Detection | ❌ | ✅ | ✅ | ❌ |
| Content Moderation | ❌ | ✅ | ❌ | ❌ |
| Scene Analysis | ❌ | ✅ | ✅ | ✅ |

### Key Capabilities

1. **Multi-Provider Support**: Analyze videos with multiple AI providers simultaneously
2. **Intelligent Fallback**: Automatic failover to alternate providers
3. **Batch Processing**: Process multiple videos efficiently
4. **Cost Estimation**: Estimate processing costs before analysis
5. **Performance Monitoring**: Track response times and success rates
6. **Unified API**: Consistent interface across all providers

## Quick Start

### 1. Installation

The cloud AI integration is included with the YouTube Extension. Install optional dependencies for specific providers:

```bash
# Google Cloud
pip install google-cloud-videointelligence google-cloud-vision

# AWS Rekognition
pip install boto3

# Azure Vision
pip install azure-cognitiveservices-vision-computervision

# Apple FastVLM (local model - no additional dependencies)
```

### 2. Configuration

Set up provider credentials using environment variables:

```bash
# Google Cloud
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"

# AWS
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"

# Azure
export AZURE_COGNITIVE_SERVICES_KEY="your-subscription-key"
export AZURE_COGNITIVE_SERVICES_ENDPOINT="https://your-region.api.cognitive.microsoft.com/"

# Apple FastVLM
export APPLE_FASTVLM_MODEL_PATH="/path/to/fastvlm/model"
```

### 3. Basic Usage

#### Python SDK

```python
import asyncio
from youtube_extension.integrations.cloud_ai import (
    CloudAIIntegrator, AnalysisType, CloudAIProvider
)

async def analyze_video():
    config = {
        "google_cloud": {
            "enabled": True,
            "project_id": "your-project"
        }
    }
    
    async with CloudAIIntegrator(config) as ai:
        result = await ai.analyze_video(
            "https://youtube.com/watch?v=example",
            [AnalysisType.LABEL_DETECTION, AnalysisType.OBJECT_TRACKING]
        )
        
        print(f"Found {len(result.labels)} labels")
        for label in result.labels[:5]:
            print(f"- {label.label}: {label.confidence:.2f}")

asyncio.run(analyze_video())
```

#### REST API

```bash
# Analyze single video
curl -X POST "http://localhost:8000/api/v1/cloud-ai/analyze/video" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=example",
    "analysis_types": ["label_detection", "object_tracking"],
    "preferred_provider": "google_cloud"
  }'

# Check provider status
curl "http://localhost:8000/api/v1/cloud-ai/providers/status"

# Get available analysis types
curl "http://localhost:8000/api/v1/cloud-ai/analysis-types"
```

## Advanced Features

### Multi-Provider Analysis

Compare results from multiple providers:

```python
async with CloudAIIntegrator(config) as ai:
    results = await ai.multi_provider_analysis(
        video_url, 
        [AnalysisType.LABEL_DETECTION]
    )
    
    for result in results:
        print(f"{result.provider.value}: {len(result.labels)} labels")
    
    # Aggregate results from all providers
    aggregated = ai.aggregate_results(results)
```

### Batch Processing

Process multiple videos efficiently:

```python
video_urls = [
    "https://youtube.com/watch?v=video1",
    "https://youtube.com/watch?v=video2", 
    "https://youtube.com/watch?v=video3"
]

async with CloudAIIntegrator(config) as ai:
    results = await ai.batch_analyze(
        video_urls,
        [AnalysisType.LABEL_DETECTION]
    )
```

### Configuration Management

Use the configuration management system:

```python
from youtube_extension.integrations.cloud_ai.config import CloudAIConfig

# Load from environment
config = CloudAIConfig.from_environment()

# Validate configuration
validation_results = config.validate_all()
print(f"Validation: {validation_results}")

# Check dependencies
availability = config.check_dependencies()
print(f"Available providers: {availability}")

# Save configuration
config.save_to_file("cloud_ai_config.json")
```

## Provider-Specific Details

### Google Cloud Video Intelligence

**Strengths:**
- Comprehensive video analysis features
- Excellent object tracking
- Shot change detection
- Logo recognition

**Requirements:**
- Google Cloud project with Video Intelligence API enabled
- Service account credentials
- Billing enabled

**Pricing:** Pay per minute of video processed

### Amazon Rekognition

**Strengths:**
- Advanced face detection and analysis
- Content moderation capabilities
- Celebrity recognition
- Real-time streaming support

**Requirements:**
- AWS account with Rekognition access
- IAM credentials with appropriate permissions
- S3 bucket for video storage (for video analysis)

**Pricing:** Pay per image/minute analyzed

### Microsoft Azure AI Vision

**Strengths:**
- Robust OCR capabilities
- Multi-language text detection
- Custom model support
- Video Indexer integration

**Requirements:**
- Azure Cognitive Services subscription
- API key and endpoint
- Resource group in supported region

**Pricing:** Pay per transaction

### Apple FastVLM

**Strengths:**
- Local processing (no cloud dependency)
- Fast inference on Apple Silicon
- Multi-modal understanding
- Privacy-focused

**Requirements:**
- Local model files
- Compatible hardware (optimized for Apple Silicon)
- Sufficient storage and memory

**Pricing:** No per-use costs (local processing)

## API Reference

### Endpoints

#### `POST /api/v1/cloud-ai/analyze/video`
Analyze a single video with specified analysis types.

**Request:**
```json
{
  "video_url": "https://youtube.com/watch?v=example",
  "analysis_types": ["label_detection", "object_tracking"],
  "preferred_provider": "google_cloud",
  "use_fallback": true
}
```

**Response:**
```json
{
  "video_id": "example",
  "provider": "google_cloud",
  "processing_time": 12.5,
  "analysis_types": ["label_detection", "object_tracking"],
  "objects": [
    {
      "label": "person",
      "confidence": 0.95,
      "timestamp": 10.5,
      "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.6}
    }
  ],
  "labels": [
    {"label": "technology", "confidence": 0.92}
  ],
  "cost_estimate": 0.05
}
```

#### `GET /api/v1/cloud-ai/providers/status`
Get status of all cloud AI providers.

#### `POST /api/v1/cloud-ai/analyze/batch`
Start batch processing of multiple videos.

#### `POST /api/v1/cloud-ai/analyze/multi-provider`
Analyze video with multiple providers for comparison.

### Python SDK Classes

#### `CloudAIIntegrator`
Main orchestrator for cloud AI services.

```python
async with CloudAIIntegrator(config) as ai:
    result = await ai.analyze_video(video_url, analysis_types)
    status = await ai.get_provider_status()
```

#### `AnalysisType` (Enum)
- `OBJECT_TRACKING`
- `OCR` 
- `LABEL_DETECTION`
- `LOGO_RECOGNITION`
- `SHOT_DETECTION`
- `FACE_DETECTION`
- `TEXT_DETECTION`
- `CONTENT_MODERATION`
- `SCENE_ANALYSIS`

#### `CloudAIProvider` (Enum)
- `GOOGLE_CLOUD`
- `AWS_REKOGNITION`
- `AZURE_VISION`
- `APPLE_FASTVLM`

## Error Handling

The integration includes comprehensive error handling:

```python
from youtube_extension.integrations.cloud_ai import (
    CloudAIError, RateLimitError, ConfigurationError
)

try:
    result = await ai.analyze_video(video_url, analysis_types)
except RateLimitError as e:
    print(f"Rate limit exceeded, retry after {e.retry_after} seconds")
except ConfigurationError as e:
    print(f"Configuration issue: {e.missing_config}")
except CloudAIError as e:
    print(f"AI analysis failed: {e}")
```

## Performance Optimization

### Best Practices

1. **Provider Selection**: Choose providers based on your specific needs
2. **Batch Processing**: Use batch operations for multiple videos
3. **Caching**: Cache results to avoid repeated analysis
4. **Rate Limiting**: Respect provider rate limits
5. **Cost Monitoring**: Monitor usage and costs

### Rate Limits

| Provider | Rate Limit | Notes |
|----------|------------|-------|
| Google Cloud | 2000 requests/day | Default quota |
| AWS Rekognition | 5 TPS | Transactions per second |
| Azure Vision | 10 TPS | Can be increased |
| Apple FastVLM | No limit | Local processing |

## Troubleshooting

### Common Issues

1. **Import Errors**: Install provider-specific dependencies
2. **Authentication Failures**: Verify credentials and permissions
3. **Rate Limit Errors**: Implement exponential backoff
4. **Quota Exceeded**: Check billing and quotas in provider consoles

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Use the status endpoint to verify provider availability:

```bash
curl "http://localhost:8000/api/v1/cloud-ai/providers/status"
```

## Examples

See the `examples/cloud_ai/` directory for complete working examples:

- `basic_usage.py` - Simple video analysis
- `advanced_integration.py` - Advanced features and batch processing

## Contributing

To add support for new providers:

1. Create a new provider class inheriting from `BaseCloudAI`
2. Implement all required methods
3. Add provider to the `CloudAIIntegrator`
4. Update configuration and documentation

## License

This integration is part of the YouTube Extension project and follows the same MIT license.