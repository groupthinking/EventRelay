# TASK: residual after #1907 — public frame GET + honest stills fallback

## 1. Goal & Scope
* **Objective:** Prod pack for ≥1 of `QjZ5ohr7sGA` / `XYMcBrFSJ4c` / `CWUy2zynCqc` shows non-null keyframe `image_path` values that GET as real `image/jpeg`, and `metrics.keyframes_images` is honest green (`ok` when every keyframe has a durable captured path).
* **Context:** #1907 (`d9845154`) wired storyboard capture + Blob/app-served persist + GET hydrate. Residual on uvai.io (2026-09-12): all keyframe `image_path` null, `keyframes_images=partial`; `GET /api/video/pack/frames/QjZ5ohr7sGA/1` is 401 because `auth-paths.ts` only public-lists exact `/api/video/pack`. YouTube innertube/player from datacenter/Vercel-class IPs returns "This video is unavailable" / no storyboards. Public numbered still JPGs (`img.youtube.com/vi/{id}/hq1.jpg`…`hq3.jpg` and `/1.jpg`…`/3.jpg`) return `image/jpeg` bytes from the same network.
* **Scope:**
  * `apps/web/src/lib/auth-paths.ts` — public prefix for `/api/video/pack/frames`; identity-pack AI-budget exemption
  * `apps/web/src/lib/keyframe-frame-capture.ts` — storyboard primary; stills-bytes fallback; never store ytimg URLs
  * `apps/web/src/lib/keyframe-image-path.ts` — deny `img.youtube.com`; PARTIAL/OK notes name storyboard vs stills
  * Focused Vitest (auth-paths, capture fallback, honesty)
  * *Initial check:* Reuse #1907 hydrate/persist/frame route. Do not invent architecture/code_snippets. Live-URL / G.A.T.E. stays PARKED.

## 2. Execution Plan
- [x] Confirm storyboard still fails and numbered stills return JPEG bytes
- [x] Lock failing tests (public frames path, stills fallback, honesty notes)
- [x] Implement prefix + stills-bytes fallback + provenance
- [x] Verify focused Vitest; document uvai.io re-verify after merge

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Anonymous `curl` to `/api/video/pack/frames/{videoId}/{t}` is not 401. GET hydrate still upgrades cached packs in place. When storyboard misses, numbered stills are downloaded as JPEG bytes and persisted via Blob or app-served path. `image_path` is never a bare `i.ytimg.com` / `img.youtube.com` / hqdefault / maxresdefault string. `keyframes_images=ok` only when every keyframe has a durable captured path; provenance says storyboard vs stills.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/auth-paths.test.ts src/lib/__tests__/keyframe-frame-capture.test.ts src/lib/__tests__/video-pack-extractor.test.ts src/app/api/video/pack/__tests__/route.test.ts src/app/api/video/pack/frames`
* **Proof Artifact:** `cd apps/web && npx vitest run src/lib/__tests__/auth-paths.test.ts src/lib/__tests__/keyframe-frame-capture.test.ts src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/video-pack.test.ts src/lib/__tests__/video-pack-store.test.ts src/lib/__tests__/emit-video-pack.test.ts src/lib/__tests__/emit-json-canvas.test.ts src/app/api/video/pack src/app/api/v1/video/pack` → 10 files, 118 passed, 1 skipped. Live stills for `QjZ5ohr7sGA` hq1/hq2/hq3: HTTP 200 `image/jpeg`, 480×360, JPEG magic after re-encode. Player/storyboard from this network: playability ERROR "This video is unavailable", no storyboards.

## 4. Post-Task Reflection
* **What was done:** Public-listed `/api/video/pack/frames` (and exempted it from the AI budget). Storyboard stays primary; when it misses, numbered YouTube stills are downloaded as JPEG bytes, re-encoded, and persisted via Blob or `/api/video/pack/frames/{id}/{t}`. Sanitize now also rejects `img.youtube.com`. Provenance distinguishes storyboard vs stills; `keyframes_images=ok` only when every keyframe has a durable captured path.
* **Why it was needed:** #1907 hydrate correctly left nulls because innertube/storyboard is blocked from Vercel-class IPs, and anonymous frame GET 401'd because auth only allowlisted exact `/api/video/pack`.
* **How it was tested:** Focused Vitest (public path, stills fallback, honesty, GET hydrate-in-place). Live still fetch + jpeg-js re-encode for `QjZ5ohr7sGA`. Live-URL / G.A.T.E. not touched.
