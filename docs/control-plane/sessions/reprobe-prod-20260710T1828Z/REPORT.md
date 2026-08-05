# Production re-probe after PR #654 merge

**When:** 2026-07-10T18:22Z – 18:29Z UTC
**Merged:** `bf710a99` (PR #654 GATE-4)
**Vercel prod deploy:** `v0-uvai-n2hhek9ky-garv1.vercel.app` → Ready ~18:27Z
**Aliases on that deploy:** `v0-uvai-garv1.vercel.app`, `v0-uvai-git-main-garv1.vercel.app`
**Note:** `uvai.io` is a custom domain on project `v0-uvai` (third-party DNS).

---

## Phase A — During deploy (still old code)

| Check | HTTP | Result |
|-------|------|--------|
| SSRF `169.254…` | **200** partial | Old BFF — allowlist **not** live yet |
| leading-dash | **200** partial | Old BFF |
| Valid YouTube async | **200** job pending | Happy path OK |
| Veo free | **402** | Pro gate OK |
| API health | **200** | OK |
| Checkout / webhook | 403 / 503 | GATE-3 still open |
| Auth providers | 500 | GATE-3 still open |

Evidence: `sessions/reprobe-prod-20260710T1822Z/`

---

## Phase B — After production Ready (current)

Anonymous probes of `https://uvai.io/api/pipeline` and `/api/video/*` now return:

```json
{"error":"Authentication required"}
```
**HTTP 401** (stable across 3 retries).

| Check | HTTP | Interpretation |
|-------|------|----------------|
| SSRF / dash / evil URLs | **401** | Blocked by **auth middleware** before route handler |
| Valid YouTube | **401** | Same — public unauthenticated pipeline no longer open |
| Veo free | **401** | Auth before Pro check (would be 402 if authenticated free user) |
| `api.uvai.io` health | **200** | Backend still public-health |

**Why 401?** `NEXTAUTH_SECRET` is set on Vercel Production → `AUTH_ENABLED` in `proxy.ts` → all `/api/*` except `/api/auth`, `/api/health`, `/api/billing` require a NextAuth session.

---

## GATE-4 allowlist (400) verification status

| Surface | Can verify unauthenticated? | Result |
|---------|----------------------------|--------|
| `uvai.io` route handlers | **No** — 401 first | **INCONCLUSIVE** for 400 body |
| `*.vercel.app` deployment URLs | **No** — Vercel Deployment Protection SSO | **INCONCLUSIVE** |
| Unit tests (merged) | Yes | **PASS** in CI/local |

**Honest conclusion:**
- Code for 400 invalid YouTube URL is **merged**.
- Production traffic now hits **auth gate** first, so we cannot prove the 400 allowlist from public curl.
- Security posture for anonymous attackers is **stricter** (401 on all non-public APIs) than pre-merge (200 partial on SSRF URLs).
- Residual: once a user is logged in, allowlist still matters — verify with a session cookie later.

---

## Deploy topology issue (ops)

New production deploy aliases:

- `v0-uvai-garv1.vercel.app`
- `v0-uvai-git-main-garv1.vercel.app`

Both are **Deployment Protection** protected (SSO).
`uvai.io` custom domain serves the app without that protection but with **app-level** NextAuth gate.

During the race window, `uvai.io` briefly still served the **previous** deploy id `dpl_CHKfkAtwmwBwYraAvuAdXbYaRs3B` (SSRF → 200).

---

## Still broken (GATE-3, unchanged)

| Endpoint | HTTP |
|----------|------|
| `/api/billing/checkout` | 403 turnstile_not_configured |
| `/api/billing/webhook` | 503 webhook_not_configured |
| `/api/auth/providers` | 500 config |

---

## Recommended next probes (need session)

1. Browser sign-in once Google OAuth works (GATE-3).
2. With session cookie:
   ```bash
   curl -sS -b 'session=...' -X POST https://uvai.io/api/pipeline \
     -H 'content-type: application/json' \
     -d '{"url":"http://169.254.169.254/aaaaaaaaaaa"}'
   # expect 400 invalid_youtube_url
   ```
3. Or temporarily add a non-prod-only test header — **not recommended** for prod.

---

## Bottom line

| Question | Answer |
|----------|--------|
| Is #654 merged and deployed as Vercel Production Ready? | **Yes** (`n2hhek9ky`, ~18:27Z) |
| Did anonymous SSRF still get 200 after Ready? | **No longer** — now **401** on pipeline |
| Did we prove BFF returns 400 for SSRF? | **Not yet** (auth blocks first) |
| Is free public pipeline still open? | **No** — auth required |
| API backend health | **200** |
| Launch (GATE-3) | Still blocked |
