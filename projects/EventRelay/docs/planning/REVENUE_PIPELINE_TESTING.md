# Revenue Pipeline Testing Guide

## Overview

The Revenue Pipeline is EventRelay's core monetizable feature that transforms YouTube videos into deployed web applications. This guide explains how to test the pipeline end-to-end.

## Architecture Flow

```
YouTube URL → Video Processing → AI Code Generation → Vercel Deployment
     ↓              ↓                    ↓                    ↓
  Extract ID    Get transcript      Generate code       Deploy to web
  Fetch meta    AI analysis        10+ packages         Live URL
```

## Prerequisites

### 1. System Requirements

- **Python**: 3.9 or higher
- **Node.js**: 16+ (if testing deployment)
- **Disk Space**: Minimum 5GB free space
- **OS**: Linux, macOS, or Windows with WSL2

### 2. API Keys (Required)

At least ONE of these AI API keys is required:

- `GEMINI_API_KEY` (recommended - cost-effective for transcription)
- `GOOGLE_API_KEY` (alternative to GEMINI_API_KEY)
- `OPENAI_API_KEY` (fallback option)

Optional but recommended:
- `YOUTUBE_API_KEY` (enhances metadata extraction)
- `ANTHROPIC_API_KEY` (additional AI capabilities)
- `ASSEMBLYAI_API_KEY` (alternative transcription)

### 3. Vercel Setup (Optional - for deployment testing)

Only needed if testing full deployment:
```bash
# Install Vercel CLI
npm install -g vercel

# Set Vercel token
export VERCEL_TOKEN=your_vercel_token
```

## Quick Start

### Step 1: Check Prerequisites

Run the prerequisite checker to verify your setup:

```bash
python3 scripts/check_revenue_pipeline_prerequisites.py
```

This will check:
- ✓ Python version
- ✓ Required dependencies
- ✓ API keys configuration
- ✓ .env file existence
- ✓ Vercel CLI (optional)
- ✓ Disk space

### Step 2: Setup Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .[dev,youtube,ml]

# Create .env file from example
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

### Step 3: Configure API Keys

Edit `.env` and add your keys:

```bash
# Required - at least one of these
GEMINI_API_KEY=your_gemini_key_here
# GOOGLE_API_KEY=your_google_key_here
# OPENAI_API_KEY=your_openai_key_here

# Optional but recommended
YOUTUBE_API_KEY=your_youtube_api_key_here

# Optional - for enhanced features
# ANTHROPIC_API_KEY=your_anthropic_key_here
# ASSEMBLYAI_API_KEY=your_assemblyai_key_here
```

### Step 4: Run Tests

```bash
# Test pipeline without deployment (faster - 30-60 seconds)
python3 scripts/test_revenue_pipeline.py

# Test complete pipeline with deployment (slower - 5-10 minutes)
# Requires Vercel CLI and VERCEL_TOKEN
python3 scripts/test_revenue_pipeline.py --with-deployment
```

## Test Modes

### Mode 1: Code Generation Only (Default)

Tests the pipeline without deploying:
- ✓ YouTube video processing
- ✓ Transcript extraction
- ✓ AI analysis
- ✓ Code generation
- ✗ Deployment (skipped)

**Duration**: 30-60 seconds  
**Cost**: $0.001-0.01 per video

```bash
python3 scripts/test_revenue_pipeline.py
```

### Mode 2: Full Pipeline with Deployment

Tests the complete pipeline including Vercel deployment:
- ✓ YouTube video processing
- ✓ Transcript extraction
- ✓ AI analysis
- ✓ Code generation
- ✓ Vercel deployment

**Duration**: 5-10 minutes  
**Cost**: $0.001-0.01 + Vercel hosting

```bash
# Run the test suite - it will automatically run Test 1 (generation only)
# then prompt for confirmation before running Test 2 (with deployment)
python3 scripts/test_revenue_pipeline.py

# When prompted "Continue with full deployment test? (y/N):", type 'y'
```

## Expected Output

### Successful Test Output

```
🚀 Revenue Pipeline Test Suite
============================================================
Testing: YouTube URL → AI Code Generation → Deployment

【 Test 1: Pipeline without deployment 】
🧪 Testing Revenue Pipeline (no deployment)
============================================================

📹 Processing video: https://www.youtube.com/watch?v=auJzb1D-fag
⏱️  This may take 30-60 seconds...

✅ Video processed: Sample Video Tutorial

✅ Code generated at: /path/to/generated/project

============================================================
📊 PIPELINE TEST RESULTS
============================================================
✅ Status: SUCCESS

📺 Video: Sample Tutorial Video
📁 Project: /tmp/generated_projects/sample-tutorial-abc123
⏱️  Duration: 45.23 seconds

📦 Steps Completed:
  ✅ Video Processing
  ✅ Code Generation
  ⏭️ Deployment

🔧 Metadata:
  Video ID: auJzb1D-fag
  Channel: Sample Channel
  Files Generated: 85
  Architecture: fullstack_app
  Framework: Next.js

🚀 Next Steps:
  1. cd /tmp/generated_projects/nextjs-tutorial-abc123
  2. npm install
  3. npm run dev
  4. vercel --prod  # To deploy

🎉 Revenue pipeline is operational!
Ready to convert YouTube videos to deployed applications.
```

## Troubleshooting

### Error: "GEMINI_API_KEY must be set"

**Solution**: Add API key to `.env` file:
```bash
echo "GEMINI_API_KEY=your_key_here" >> .env
```

### Error: "No space left on device"

**Solution**: Free up disk space:
```bash
# Clean pip cache
pip cache purge

# Remove unused Docker images/containers
docker system prune -a

# Check disk usage
df -h
```

### Error: "ModuleNotFoundError: No module named 'fastapi'"

**Solution**: Install dependencies:
```bash
source .venv/bin/activate
pip install -e .[dev,youtube,ml]
```

### Error: "Vercel CLI not found"

This is only an error if you're testing deployment. For code generation only, this is normal.

**Solution for deployment testing**:
```bash
npm install -g vercel
```

### Error: "Connection timeout" or "API rate limit"

**Solution**: 
- Check your internet connection
- Verify API keys are valid and have quota
- Wait a few minutes and retry
- Use a different API provider (e.g., switch from OpenAI to Gemini)

## Performance Metrics

### Expected Performance

| Metric | Value |
|--------|-------|
| Video Processing | 10-20 seconds |
| AI Analysis | 5-15 seconds |
| Code Generation | 15-25 seconds |
| **Total (no deploy)** | **30-60 seconds** |
| Vercel Deployment | 4-8 minutes |
| **Total (with deploy)** | **5-10 minutes** |

### Resource Usage

| Resource | Usage |
|----------|-------|
| API Cost per Video | $0.001-0.01 |
| Memory | ~500MB-2GB |
| CPU | 1-2 cores |
| Disk (temp files) | ~100MB per video |
| Network | ~10-50MB download |

## Test Videos

### Recommended Test Videos

The test script uses this default video (short, well-structured):
- URL: `https://www.youtube.com/watch?v=auJzb1D-fag`
- Video ID: `auJzb1D-fag` (standard test video per project guidelines)
- Language: English
- Content: Technical tutorial

### Alternative Test Videos

You can test with your own videos by editing the test script:

```python
# In scripts/test_revenue_pipeline.py
test_video_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

Best practices for test videos:
- ✓ Publicly accessible
- ✓ Has captions/transcript available
- ✓ Technical content (programming, design, etc.)
- ✓ English language (or your target language)
- ✓ 5-60 minutes duration
- ✗ Avoid music videos, live streams, private videos

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Test Revenue Pipeline

on: [push, pull_request]

jobs:
  test-pipeline:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev,youtube,ml]
      
      - name: Check prerequisites
        run: python3 scripts/check_revenue_pipeline_prerequisites.py
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      
      - name: Test pipeline (no deployment)
        run: python3 scripts/test_revenue_pipeline.py
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
```

## API Costs Breakdown

### Gemini API (Recommended)

- Video transcription: $0.0001-0.001 per video
- AI analysis: $0.001-0.005 per video
- **Total per video**: ~$0.001-0.006

### OpenAI API

- Transcription (Whisper): $0.006 per minute
- GPT-4 analysis: $0.01-0.05 per analysis
- **Total per 30min video**: ~$0.19-0.23

### Comparison

| Provider | Cost per Video | Speed | Quality |
|----------|---------------|-------|---------|
| Gemini | $0.001-0.006 | Fast | Excellent |
| OpenAI | $0.19-0.23 | Fast | Excellent |
| AssemblyAI | $0.15-0.37 | Medium | Excellent |

**Recommendation**: Use Gemini API for cost-effective testing and production.

## Development Workflow

### 1. Local Development

```bash
# Activate environment
source .venv/bin/activate

# Run prerequisite check
python3 scripts/check_revenue_pipeline_prerequisites.py

# Test pipeline
python3 scripts/test_revenue_pipeline.py

# View generated code
cd /tmp/generated_projects/<project-name>
npm install
npm run dev
```

### 2. Code Changes

When modifying the pipeline:

```bash
# Make your changes to:
# - src/youtube_extension/backend/revenue_pipeline.py
# - src/youtube_extension/backend/enhanced_video_processor.py  
# - src/youtube_extension/backend/ai_code_generator.py

# Test changes
python3 scripts/test_revenue_pipeline.py

# Check results
less /tmp/generated_projects/<latest-project>/README.md
```

### 3. Debugging

Enable detailed logging:

```bash
# Set log level in .env
LOG_LEVEL=DEBUG

# Run with verbose output
python3 scripts/test_revenue_pipeline.py 2>&1 | tee pipeline_test.log
```

## Next Steps

After successful testing:

1. **Try Custom Videos**: Test with your own YouTube videos
2. **Customize Generation**: Modify project templates in `ai_code_generator.py`
3. **Deploy to Vercel**: Run full pipeline with deployment
4. **Monitor Costs**: Track API usage and costs
5. **Production Setup**: Configure for production use

## Support

For issues or questions:

- Check [REVENUE_PIPELINE.md](REVENUE_PIPELINE.md) for architecture details
- Review [README.md](README.md) for general setup
- Open an issue on GitHub
- Review test implementation in `scripts/test_revenue_pipeline.py`

## Related Documentation

- [REVENUE_PIPELINE.md](REVENUE_PIPELINE.md) - Pipeline architecture and design
- [README.md](README.md) - Project overview and setup
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Development guidelines
- [PHASE_1_3_VERIFICATION.md](PHASE_1_3_VERIFICATION.md) - Project phases and milestones
