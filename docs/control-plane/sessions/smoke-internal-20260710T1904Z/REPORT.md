# Controlled smoke (internal auth bypass) — GATE-4 live proof

**When:** 2026-07-10T19:04Z UTC
**Host:** `https://uvai.io`
**Method:** Temporary **ops** bypass — `INTERNAL_REQUEST_TOKEN` + header `x-eventrelay-internal`
**Not public:** Anonymous requests still **401**. No public auth hole was opened.

Redeploy: `v0-uvai-npedgxdfz-garv1.vercel.app` (Production Ready, env refresh).

---

## Results — **PASS_ALL**

| Check | Expected | Actual | Pass |
|-------|----------|--------|------|
| Anonymous SSRF (no header) | 401 | **401** | YES |
| SSRF `http://169.254.169.254/aaaaaaaaaaa` | 400 | **400** `invalid_youtube_url` | YES |
| Leading-dash injection | 400 | **400** `invalid_youtube_url` | YES |
| Evil host `evil.example` | 400 | **400** `invalid_youtube_url` | YES |
| Valid YouTube (Me at the zoo) | 200 | **200** (local-fallback this run; backend abort) | YES |
| Veo free user | 402 | **402** Pro required | YES |
| `/api/video` SSRF | 400 | **400** `invalid_youtube_url` | YES |

---

## What this proves

1. **GATE-4 BFF allowlist is live** on `uvai.io` for requests that reach the route handler.
2. **Public surface stays locked** without the internal header (401).
3. Veo Pro gate still works (402) after bypassing NextAuth.

---

## Ops note

`INTERNAL_REQUEST_TOKEN` was added to Vercel Production for this smoke. It is a **server-only** secret for health/smoke loops. Treat it like an API key; rotate if leaked.

Token file on operator machine only: `/tmp/er-smoke-internal-token.txt` (not committed).

To smoke again:

```bash
TOKEN=$(cat /tmp/er-smoke-internal-token.txt)  # or from Vercel env
curl -sS -X POST https://uvai.io/api/pipeline \
  -H "content-type: application/json" \
  -H "x-eventrelay-internal: $TOKEN" \
  -d '{"url":"http://169.254.169.254/aaaaaaaaaaa"}'
# expect 400 invalid_youtube_url
```

To remove the token after ops:

```bash
vercel env rm INTERNAL_REQUEST_TOKEN production
vercel redeploy <current-production-url>
```
