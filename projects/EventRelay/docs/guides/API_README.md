# YouTube Extension API

Minimal API for converting YouTube videos into polished, cached learning guides.

## Base URL

- Local: `http://localhost:8000`

## Endpoints

- GET `/health`
  - Returns health and processor availability

- POST `/api/process-video-markdown`
  - Body: `{ "video_url": string, "force_regenerate"?: boolean }`
  - Response: `{ video_id, video_url, metadata, markdown_content, cached, save_path, processing_time, status }`

- GET `/api/markdown/{video_id}`
  - Returns cached markdown and metadata if available

- GET `/api/cache/stats`
  - Returns cache counts and sizes

- DELETE `/api/cache/{video_id}`
  - Clears cache for a specific video

- DELETE `/api/cache`
  - Clears all caches

- GET `/metrics`
  - Plain text counters for basic monitoring

## Example

```bash
curl -s -X POST http://localhost:8000/api/process-video-markdown \
  -H 'Content-Type: application/json' \
  -d '{"video_url":"https://www.youtube.com/watch?v=aircAruvnKk"}'
```

## Environment

- `YOUTUBE_API_KEY` (39 chars, starts with `AIzaSy`)
- `OPENAI_API_KEY` (if using OpenAI for markdown generation)


