# Hybrid Gemini/Veo Integration Baseline

## Overview
- Gemini service now supports dynamic model selection across Gemini, Gemma, and Veo families with async helpers for caching, batch execution, and ephemeral tokens (`src/youtube_extension/services/ai/gemini_service.py`).
- Hybrid processor exposes those helpers so downstream agents and APIs can manage reuse, heavy workloads, and client-issued tokens (`src/youtube_extension/services/ai/hybrid_processor_service.py`).
- Hybrid Vision Agent routes special commands (`action`/`command`) to the new helpers, enabling orchestration tasks such as cache priming, batch jobs, or token minting without media payloads (`src/youtube_extension/services/agents/hybrid_vision_agent.py`).
- Transcript Action workflow extracts transcripts via the robust YouTube service, falling back to Google Speech-to-Text V2 and now, when needed, Gemini’s video understanding with File API uploads (clipping/fps hints supported) before orchestrating summaries, project scaffolds, and task boards (`src/youtube_extension/services/workflows/transcript_action_workflow.py`, `src/youtube_extension/services/agents/transcript_action_agent.py`).
- Transcript fallback paths emit metrics (`transcript_fallback_success`, `transcript_fallback_latency_seconds`) so speech/Gemini performance can be tuned from production telemetry (metrics exposed through `metrics_service`).
- FastAPI now serves `/api/v1/hybrid/cache`, `/api/v1/hybrid/batch`, and `/api/v1/hybrid/ephemeral-token`, backed by a registered `hybrid_processor_service` singleton (`src/youtube_extension/backend/api/v1/router.py`, `containers/service_container.py`).
- Frontend service `ApiService` gained helper methods (`requestEphemeralToken`, `createHybridCache`, `submitHybridBatch`) plus shared TypeScript interfaces so web/mobile clients can call the new endpoints without exposing the primary API key (`frontend/src/services/api.ts`).

## Environment
- `google-generativeai` 0.8.5 installed locally; Gemini and Veo API keys loaded from `/Users/garvey/Desktop/api/` (see user-provided credentials) to unlock video generation and caching features.
- Default creative video routing now targets Veo; adjust `HybridConfig.model_routing[TaskType.CREATIVE_VIDEO]` as needed for `veo-3.0-generate-001` (quality) or `veo-3.0-fast-generate-001` (cost/speed).

## Validation
Run the focused unit suites to confirm the hybrid stack:
```
pytest tests/unit/test_gemini_service_batch_caching.py \
       tests/unit/test_hybrid_processor_cloud.py \
       tests/unit/test_gemini_service_model_selection.py \
       tests/unit/test_hybrid_vision_agent_actions.py -q
```
All tests should pass, verifying Gemini helpers, hybrid delegation, and agent command handling.

## Usage Notes
- **Ephemeral tokens:** `POST /api/v1/hybrid/ephemeral-token` or call `HybridVisionAgent` with `{"action": "create_ephemeral_token", ...}` to generate short-lived upload credentials.
- **Caching:** Use `/api/v1/hybrid/cache` (or agent action `start_cached_session`) to seed Gemini caches for repeated prompts.
- **Batch jobs:** Submit heavy workloads via `/api/v1/hybrid/batch`; set `wait=true` to poll for completion and retrieve serialized operation metadata.
- **Transcript-to-action:** Invoke `POST /api/v1/transcript-action` to extract transcripts, build deployment scaffolds, and receive task boards using the new `TranscriptActionWorkflow`. The pipeline now cascades through native captions → Speech-to-Text V2 → Gemini video transcription (YouTube ingestion with File API fallback), and callers can pass `video_options` (`start_seconds`, `end_seconds`, `fps`) to tighten Gemini processing windows.
- **Speech-to-Text setup:** Export `GOOGLE_SPEECH_PROJECT_ID`, `GOOGLE_SPEECH_LOCATION`, and `GOOGLE_SPEECH_RECOGNIZER` (matching your V2 recognizer) and install the `youtube` extra (`pip install -e .[youtube]`) so the fallback can reach Google Speech-to-Text V2.
- **Batch Speech V2:** Provide `GOOGLE_SPEECH_GCS_BUCKET` (and optionally `GOOGLE_SPEECH_GCS_PREFIX`) to enable automatic promotion of larger audio tracks to `BatchRecognize`; the service uploads temp objects, waits for inline results, deletes the blob, and the workflow metrics capture latency/success for ongoing tuning.
- **Creative video:** Invoke the batch helper with Veo prompts informed by Google’s dialogue/realism/style examples. Responses include serialized operation data for downstream asset retrieval.

## Next Steps
- Execute an end-to-end creative video generation against `veo-3` once prompts are finalized, confirming output storage and frontend playback.
- Layer additional analytics or monitoring around the new `/api/v1/hybrid/*` endpoints as production traffic grows.
