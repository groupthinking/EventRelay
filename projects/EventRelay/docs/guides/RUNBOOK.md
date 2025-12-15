# Runbook

## Start (local)

```bash
# Ensure .env contains keys
python3 start_enhanced_backend.py
# or
python3 - <<'PY'
import sys, uvicorn
sys.path.insert(0, 'backend')
from main import app
uvicorn.run(app, host='0.0.0.0', port=8000)
PY
```

## Health

```bash
curl -s http://localhost:8000/health | jq
```

## Process a video

```bash
curl -s -X POST http://localhost:8000/api/process-video-markdown \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.youtube.com/watch?v=aircAruvnKk"}' | jq -r '.markdown_content' | head -100
```

## Cache

- Stats: `GET /api/cache/stats`
- Clear one: `DELETE /api/cache/{video_id}`
- Clear all: `DELETE /api/cache`

## Troubleshooting

- 422: Check JSON body, ensure `video_url` is valid
- 503: Processor unavailable – verify keys and logs
- SSL transcript warning: transcript comments fetch can be skipped; processing still succeeds
