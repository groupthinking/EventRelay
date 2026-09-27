# yt-dlp acquisition path (AUDIT-011)

`src/youtube_extension/backend/services/youtube/adapters/robust.py` tries API-backed metadata first, then **PyTube**, then **yt-dlp** (`--dump-json`).

## Failure modes

- Missing `yt-dlp` binary → subprocess error; logged and surfaced as metadata failure.
- Datacenter IP blocks → prefer PyTube/API path; yt-dlp remains last resort.

## Hardening checklist

- [ ] Circuit-breaker counter per video_id when yt-dlp fails repeatedly
- [ ] Health metric for `source_api=yt-dlp` error rate
- [ ] Document required `yt-dlp` version in deploy runbooks (see `pyproject.toml` optional extra)

No mock transcript data in production paths (`REAL_MODE_ONLY`).
