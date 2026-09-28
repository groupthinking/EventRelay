# Loom share → xAI STT → Pro Grok (dogfood)

Pro session only (stored Pro entitlement, or the signed-in paywall bypass). Anonymous chat does not run this path. This does not change the YouTube → Video Pack → Gemini caption path, and it is not a G.A.T.E. PASS.

## Paste

On uvai.io Home or Studio, paste a public Loom share:

- `https://www.loom.com/share/<32 hex id>`
- `https://www.loom.com/embed/<32 hex id>`
- `https://loom.com/share/<32 hex id>` (query string ignored)

YouTube URLs still emit a Video Pack. A Loom share does not.

## What the server does

1. `POST /api/loom/build` with `{ "url": "<share or embed>" }`.
2. Acquire audio. A direct file on `cdn.loom.com` or `luna.loom.com` (`.mp4`, `.webm`, `.m4a`, …) is probed and sent to xAI as `url`. If Loom only returns HLS, the server downloads the audio rendition and sends AAC bytes as `file`. The share/embed HTML page is never sent to STT. If neither a direct file nor AAC bytes can be obtained, the route returns **422** `loom_audio_unavailable`: “Loom did not yield extractable audio. The watch page alone cannot be transcribed.”
3. `POST https://api.x.ai/v1/stt` multipart. `model=grok-voice-transcribe-2.0`. Key order: `GROK_XAI_API_KEY`, then `XAI_API_KEY`, then `GROK_API_KEY`.
4. Non-empty `text` and `duration` > 0 are required. That transcript is the user prompt to the existing `grokChatCompletion` Pro path (`provider: "xai"`).

## Response

```json
{
  "ok": true,
  "loomId": "<32 hex>",
  "shareUrl": "https://www.loom.com/share/<32 hex>",
  "transcript": "<non-empty text>",
  "duration": 18.2,
  "answer": "<in-session Grok build>",
  "provider": "xai",
  "model": "grok-4-1-fast",
  "sttModel": "grok-voice-transcribe-2.0",
  "audioSource": "transcoded-url",
  "plan": "pro"
}
```

`audioSource` is `transcoded-url`, `graphql-mp4`, `graphql-webm`, `raw-url`, or `hls-audio`.

Studio shows `transcript` in the transcript pane and `answer` under Summary (`data-testid="studio-loom-grok-build"`).

## Not a pass

Private or password-protected shares fail closed. HLS audio larger than 48MB fails closed. A 402 `pro_required` means the caller is not a Pro session. Do not treat a successful local response as a product PASS until Loop dogfoods a real public Loom on uvai.io.
