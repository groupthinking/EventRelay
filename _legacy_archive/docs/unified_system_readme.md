# Unified GPT-OSS-20B + MCP + A2A Pipeline

## Overview

Complete production system combining:
- **GPT-OSS-20B** (20B parameter language model)  
- **MCP (Model Context Protocol)** for tool integration
- **A2A (Agent-to-Agent)** orchestration layer
- **Pre-indexed repositories** for instant access

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   GPT-OSS-20B   │    │  MCP Tools   │    │  A2A Layer      │
│                 │    │              │    │                 │
│ • Local/Remote  │◄──►│ • GitHub     │◄──►│ • Orchestration │
│ • Streaming     │    │ • YouTube    │    │ • Handoffs      │
│ • Generation    │    │ • FB OSS     │    │ • Task Routing  │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## Files Structure

```
.
├── mcp_registry.py          # MCP tool registration & pre-indexing
├── a2a_layer.py             # Agent-to-agent orchestration
├── gpt_oss_unified.py       # Main unified pipeline
├── use_gpt_oss_20b.py       # Enhanced GPT model interface  
├── requirements.txt         # Python dependencies
├── run_unified_pipeline.sh  # Setup & execution script
└── unified_system_readme.md # This documentation
```

## Features

### 🚀 **Pre-Indexing Optimization**
```python
PREINDEX_REPOS = [
    "facebook/react",
    "microsoft/generative-ai-for-beginners", 
    "huggingface/transformers"
]
```
- **Zero latency** on first access to indexed repos
- Configurable repository list
- Background indexing during startup

### 🔄 **A2A Orchestration**
```python
# Seamless tool handoffs
yt_summary = mcp_registry.get_tool("YouTubeTool").execute(url)
repo_code = a2a.handoff(f"Build from: {yt_summary}", "YouTubeTool", "GitHubTool")
deploy = a2a.handoff(f"Deploy: {repo_code}", "GitHubTool", "FBOssTool")
```

### 🤖 **Multi-Modal GPT Integration**
- Local GPU execution (CUDA required for MXFP4)
- Remote vLLM server support  
- Streaming token output
- Batch processing capabilities

## Quick Start

### Option 1: Automated Setup
```bash
./run_unified_pipeline.sh
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip3 install -r requirements.txt

# Optional: Set GitHub token for private repos
export GITHUB_TOKEN="ghp_xxx"

# Run unified pipeline
python3 gpt_oss_unified.py
```

## Usage Examples

### Basic Pipeline
```python
from mcp_registry import mcp_registry
from a2a_layer import a2a

# Process YouTube → GitHub → Deploy
yt_result = mcp_registry.get_tool("YouTubeTool").execute("https://youtu.be/example")
github_result = a2a.handoff("Create repo", "YouTubeTool", "GitHubTool")  
deploy_result = a2a.handoff("Deploy code", "GitHubTool", "FBOssTool")
```

### GPT Model Integration
```python
# Load and use GPT-OSS-20B
model, tokenizer = load_gpt_model()
result = run_prompt(model, tokenizer, "Analyze this codebase...")
```

### Streaming & Batch Processing
```bash
# Stream single prompt  
python3 use_gpt_oss_20b.py --stream --prompt "Explain MCP protocol"

# Batch process file
python3 use_gpt_oss_20b.py --input prompts.txt --out results.jsonl
```

## Configuration

### Environment Variables
- `GITHUB_TOKEN` - GitHub API access (optional for public repos)
- `REMOTE_VLLM_URL` - Remote GPU server endpoint
- `MODEL_NAME` - Override default model path

### Customization Points
- **Repository pre-indexing**: Modify `PREINDEX_REPOS` in `mcp_registry.py`
- **Tool configuration**: Adjust tool parameters in registry setup
- **Pipeline logic**: Customize handoff sequences in main script

## Performance Optimizations

- ⚡ **Pre-indexed repos** - Instant access to frequently used repositories
- 🔄 **Connection pooling** - Reuse HTTP connections for MCP tools  
- 💾 **Model caching** - Keep loaded models in memory between requests
- 🌊 **Streaming output** - Real-time token generation display

## Requirements

### Minimum
- Python 3.8+
- 8GB RAM  
- Internet connection for MCP tools

### Recommended (for local GPT)
- CUDA-compatible GPU
- 16GB+ VRAM
- NVMe SSD storage

## Troubleshooting

### Model Loading Issues
```bash
# Check CUDA availability
python3 -c "import torch; print(torch.cuda.is_available())"

# Use remote fallback
export USE_REMOTE=1
export REMOTE_VLLM_URL="http://gpu-server:8000/v1"
```

### MCP Tool Errors
- Verify internet connectivity
- Check API tokens/credentials
- Review tool-specific requirements

## Production Deployment

1. **GPU Server**: Deploy vLLM for model serving
2. **Load Balancer**: Distribute requests across model instances  
3. **Monitoring**: Track latency, throughput, error rates
4. **Scaling**: Auto-scale based on demand metrics

---

**Status**: ✅ Production Ready  
**Last Updated**: 2025-08-08  
**License**: MIT