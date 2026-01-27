# VibeVoice Evaluation & Integration Plan

**Source:** [Microsoft VibeVoice](https://microsoft.github.io/VibeVoice/)
**Repository:** [Groupthinking/VOICEvibe](https://github.com/Groupthinking/VOICEvibe) (Fork)

## Overview
VibeVoice is a TTS model optimized for:
- **Long-form audio** (up to 90 mins)
- **Multi-speaker consistency** (up to 4 speakers)
- **Conversational expressiveness** (podcasts, dialogue)
- **High efficiency** (7.5 Hz token rate)

## Relevance to EventRelay (UVAI)
EventRelay aims to transform video content into "actionable intelligence". VibeVoice fits into the **Output/Action** phase:
1.  **Audio Reconstruction:** Re-generating clear audio from noisy video inputs using transcript-based synthesis.
2.  **Workflow Enunciation:** Agents can "speak" their findings or actions in a natural, multi-speaker format (e.g., simulating a team debrief).
3.  **Content Repurposing:** Turning video summaries into podcast-style audio reports.

## Integration Strategy

### 1. New MCP Server: `speech-generation`
Create a dedicated MCP server (`mcp-servers/speech-generation`) that wraps VibeVoice.

**Capabilities:**
- `synthesize_dialogue(script: List[DialogTurn], style: str)`
- `clone_voice_from_sample(audio_sample: bytes)`

### 2. Pipeline Integration
Insert into the `video_agent_server.py` workflow:
- **Input:** Video Transcript -> **LLM** (Summarize/Script) -> **VibeVoice** -> **Audio Output**

### 3. Architecture
- **Model Hosting:** VibeVoice requires GPU. Deploy as a containerized service (Docker) on a GPU-enabled node (e.g., Cloud Run with GPU or external inference provider).
- **Interface:** The MCP server will communicate with this inference service via HTTP.

## Next Steps
1.  Clone `Groupthinking/VOICEvibe` to `external/VOICEvibe`.
2.  Build a Docker container for the inference engine.
3.  Develop `speech-generation` MCP server.
4.  Test with a sample transcript from EventRelay.
