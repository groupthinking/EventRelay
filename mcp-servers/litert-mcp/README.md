# LiteRT-LM MCP Server

This MCP server provides an interface to Google's **LiteRT-LM**, a high-performance runtime for Large Language Models (LLMs) on edge devices (Android, iOS, Linux, MacOS, Windows).

It allows you to run inference on local models (like Gemma, Phi, Qwen) directly from your MCP ecosystem.

**Note:** This server currently wraps the `lit` CLI. Multimodal inputs (image/audio) are enabled in the interface but require the C++ API or Python bindings. The CLI wrapper currently supports **Text-only inference** until CLI flags for multimodal are verified.

## Prerequisites

1.  **LiteRT-LM**: You must have LiteRT-LM installed or built.
    *   Official Repository: [google-ai-edge/LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM)
    *   Follow the "Build and Run" instructions in the official repo to build the `lit` CLI or `litert_lm_main` binary.
    *   Alternatively, download prebuilt binaries if available for your platform.

2.  **Models**: Download a supported `.litertlm` model.
    *   Models are available on Hugging Face: [LiteRT Community](https://huggingface.co/litert-community)

## Configuration

Set the following environment variables:

*   `LIT_BINARY_PATH`: Path to the `lit` CLI executable or `litert_lm_main` binary. Defaults to `lit` (assuming it's in your PATH).
*   `LIT_MODEL_PATH`: Default path to your `.litertlm` model file. (Optional, can be passed per request).

## Usage

### Tools

#### `run_inference`

Runs inference using the configured LiteRT-LM model.

*   **Arguments**:
    *   `prompt` (string, required): The input text prompt.
    *   `model_path` (string, optional): Path to the `.litertlm` model file. Overrides `LIT_MODEL_PATH` env var.
    *   `image_path` (string, optional): Path to an image file for multimodal inference.
    *   `audio_path` (string, optional): Path to an audio file for multimodal inference.
    *   `backend` (string, optional): Backend to use (`cpu`, `gpu`, `npu`). Defaults to `cpu`.

### Example

```json
{
  "name": "run_inference",
  "arguments": {
    "prompt": "What is the capital of France?",
    "backend": "cpu"
  }
}
```

**Note**: The current CLI wrapper only supports text-only inference. For multimodal capabilities (image/audio), use the LiteRT-LM C++ or Python API directly.

## Setup for Development

This server uses a manual JSON-RPC implementation to avoid external dependencies in the base environment. Just run:

```bash
python3 server.py
```

Ensure `LIT_BINARY_PATH` is set correctly.
