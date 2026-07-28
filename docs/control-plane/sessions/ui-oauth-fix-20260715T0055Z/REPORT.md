# UI + OAuth interactive verification (2026-07-15)

## Root cause of "website blocked" / OAuthSignin

Vercel production runtime logs:

```
[next-auth][error][SIGNIN_OAUTH_ERROR] client_id is required
```

`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` were **missing** from Vercel Production.
`NEXTAUTH_URL` was also unset.

## Fix applied

1. Created production env:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`
   - `NEXTAUTH_URL=https://uvai.io`
   - refreshed `NEXTAUTH_SECRET` production value from local setup
2. Redeployed production: `dpl_5aJrakKN9CL7pKjB9Ut141KsUzwc` (READY)
3. Explicitly aliased `uvai.io` + `www.uvai.io` to that deployment

## Grounded verification after fix

### OAuth start (interactive)
- `POST /api/auth/signin/google` → **302** to `https://accounts.google.com/o/oauth2/v2/auth`
- Includes `client_id=162123088773-…apps.googleusercontent.com`
- `redirect_uri=https://uvai.io/api/auth/callback/google`
- **No longer** redirects to `?error=OAuthSignin` from missing client_id

### Customer-facing views (HTTP 200, not Vercel SSO wall)
- `/`, `/login`, `/dashboard`, `/app` → Sign In (auth gate) — expected unauthenticated
- `/pricing`, `/features`, `/privacy`, `/terms`, `/studio`, `/playground` → product pages 200

### Billing path still green
- webhook missing sig → 400 (configured)
- renew → checkout session 200

## Remaining risk (human)

Google Cloud Console for OAuth client `insight-intent` / `162123088773-…` must list authorized:
- Redirect URI: `https://uvai.io/api/auth/callback/google`
- Origin: `https://uvai.io`

If missing, Google will show `redirect_uri_mismatch` after our fix (different error than OAuthSignin).

## Tools used
- Vercel MCP: `web_fetch_vercel_url`, `get_runtime_logs`, `list_deployments`
- Vercel REST API: env create/update, redeploy, domain alias
- Cookie-aware HTTP client for OAuth POST + redirect inspection
- Chrome DevTools MCP: **not connected** in this session (not available via search_tool)

## Verdict
- Site is **not** platform-blocked on custom domain `uvai.io`
- Customer auth was **broken** by missing Google OAuth env; now **unblocked to Google**
- Full Google account picker / successful login still requires correct Google Console redirect URIs + user interaction

## Follow-up measurement (post-alias)

After aliasing `uvai.io` → `dpl_5aJrakKN9CL7pKjB9Ut141KsUzwc`:

| Check | Result |
|---|---|
| POST `/api/auth/signin/google` | **302 → accounts.google.com** (client_id present) |
| Google response | **Error 400 `redirect_uri_mismatch`** |
| Customer views `/pricing` etc. | **200**, dpl=`dpl_5aJrak…`, not SSO-blocked |
| Billing webhook / renew | still green |

### Human step required (Google Console)

Open OAuth client for project **insight-intent** (client `162123088773-…`):

https://console.cloud.google.com/auth/clients?project=insight-intent

Add:
- **Authorized JavaScript origins:** `https://uvai.io`
- **Authorized redirect URIs:** `https://uvai.io/api/auth/callback/google`

(Optional for local): `http://localhost:3000` + `http://localhost:3000/api/auth/callback/google`

Then hard-refresh https://uvai.io and retry **Sign in with Google**.

### Completeness vs user bar

| Bar | Status |
|---|---|
| API-only GATE-3 | Pass (prior) |
| Customer-facing views reachable | **Pass** (this session) |
| OAuth starts (no OAuthSignin) | **Pass** (this session) |
| Google accepts redirect | **Fail** — redirect_uri_mismatch |
| Full signed-in dashboard | **Not verified** (blocked on Google Console) |
| Chrome DevTools MCP | Not connected in this environment |

**Verdict: work incomplete until redirect URI is authorized and a browser login succeeds.**
