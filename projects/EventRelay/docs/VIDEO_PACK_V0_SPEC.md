# Video Pack v0 (Draft)

Purpose: Portable, versioned AI context pack derived from a single video, consumable by UVAI orchestrator to generate code/apps/automations. Inspired by code packing patterns (e.g., PACKD/Repomix) but video‑first.

References: [PACKD](https://github.com/groupthinking/PACKD/tree/main), [Repomix Guide](https://repomix.com/guide/configuration)

## Format
- Layout: a folder or tarball containing:
  - `pack.json` (canonical JSON index)
  - `guide.md` (normalized learning/analysis guide)
  - `assets/` (keyframes, `ocr.json`, optional `topics.json`)
- Determinism: stable field ordering + SHA256 checksums in `pack.json`
- Discoverability: MCP tool `video_packager` exposes list/call + health

## pack.json (schema v0)
```json
{
  "pack_version": "0.1.0",
  "created_at": "<iso8601>",
  "source": {
    "video_id": "<11 chars>",
    "url": "<string>",
    "channel": { "id": "<string>", "name": "<string>", "verified": true },
    "title": "<string>",
    "description": "<string>",
    "duration": "PT#H#M#S",
    "publish_date": "<iso8601>",
    "thumbnails": [ { "url": "<string>", "width": 1280, "height": 720 } ]
  },
  "structure": {
    "chapters": [ { "title": "<string>", "start": 0.0 } ],
    "transcript": {
      "segments": [ { "start": 0.0, "end": 3.2, "text": "<string>", "confidence": 0.92 } ],
      "provider": "youtube|yt-dlp|asr|fallback"
    },
    "topics": [ "<topic>" ],
    "entities": [ { "type": "api|library|concept|person", "text": "<string>" } ],
    "skills": [ "<skill>" ]
  },
  "evidence": {
    "keyframes": [ { "time": 12.3, "path": "assets/kf_001.jpg" } ],
    "ocr": { "path": "assets/ocr.json", "present": false },
    "links": [ { "url": "https://...", "label": "<string>" } ]
  },
  "code_cues": {
    "snippets": [ { "language": "python", "code": "..." } ],
    "libraries": [ "fastapi", "react" ],
    "apis": [ "openai", "github" ]
  },
  "tasks": {
    "requirements": [ "<user story or acceptance criterion>" ],
    "data_flows": [ "<flow>" ],
    "build_targets": [ "web_app", "api_service", "infra" ]
  },
  "constraints": {
    "licenses": [ "yt-standard" ],
    "rate_limits": { "youtube": "unit" },
    "privacy": { "contains_pii": false }
  },
  "quality": {
    "extraction_path": "api|transcript|fallback",
    "confidence_overall": 0.0,
    "noise_ratio": 0.0,
    "validation_flags": [ "transcript_missing|chapters_inferred|fallback_used" ]
  },
  "attachments": {
    "guide_markdown": "guide.md",
    "assets": [ "assets/kf_001.jpg", "assets/ocr.json" ]
  },
  "checksums": {
    "guide.md": "sha256:...",
    "pack.json": "sha256:..."
  }
}
```

## Success Criteria (v0)
- Required: title, (transcript.segments OR fallback_text in guide.md), topics (≥1)
- Quality: noise_ratio < 0.25, confidence_overall ≥ 0.6
- Actionable: at least one build_targets entry

## Notes
- Transcript precedence: native → alt language → ASR → sanitized fallback
- Boilerplate filters: drop known YouTube footer/header strings, ads, unrelated UI text
- Provenance: always record extraction_path and set fallback_used flag when applicable
