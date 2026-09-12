# TASK: frame-capture — real keyframe image_path (FULL)

## 1. Goal & Scope
* **Objective:** Persist real captured frame images on Video Pack keyframes so GET on prod can show non-null `image_path` and honest-green `metrics.keyframes_images` when those images exist. Stay PARTIAL when capture fails. Never invent Gemini URLs or stamp `hqdefault` / `maxresdefault` as a frame at `t_s`.
* **Context:** B2 (#1903 / `7dfdd3efe`) failed closed: extractor asks for `{ t_s, desc }` only; `sanitizeKeyframeImagePath` always returns null; GET overlays `keyframes_images=partial`. Prod `QjZ5ohr7sGA` is 17/17 null. CoS UNPARK wants FULL for at least one of `QjZ5ohr7sGA` / `XYMcBrFSJ4c` / `CWUy2zynCqc`. Live-URL / G.A.T.E. stays parked. No invented architecture / code_snippets.
* **Root cause:** The Vercel pack path has no frame-capture/upload. Upstash REST is JSON-only. `@vercel/blob` was unwired. GET honesty currently *strips* any future captured URL because sanitize is unconditionally null.
* **Capture/upload path:** After extract (and on GET for existing ready packs): for each keyframe `t_s`, capture JPEG bytes from a YouTube storyboard tile at that time (actual extracted video frame, not a custom thumb). Persist via Vercel Blob when `BLOB_READ_WRITE_TOKEN` is set; otherwise cache bytes in the existing Upstash REST store (or process memory) and serve `/api/video/pack/frames/{videoId}/{t_s}`. Only then write `image_path`. If capture fails, leave null and keep PARTIAL.
* **Scope:**
  * `apps/web/src/lib/keyframe-image-path.ts` — durable-path allowlist + honesty (`partial` | `ok`)
  * `apps/web/src/lib/keyframe-frame-capture.ts` — storyboard capture, persist, hydrate
  * `apps/web/src/lib/video-pack.ts` — hydrate on persist + GET; keep invented URLs stripped
  * `apps/web/src/app/api/video/pack/frames/[videoId]/[t]/route.ts` — app-served JPEG
  * `apps/web/src/lib/emit-json-canvas.ts` + sandbox — file node only when a durable captured path is present
  * Focused Vitest
 * *Initial check:* Reuse extractor (still no Gemini `image_path`), `applyExtractedSpec`, GET `recordToResponse`, Upstash pack store. Do not add a second product store. Do not touch studio.deploy.

## 2. Execution Plan
- [x] Lock failing tests (durable path kept; thumbs/Gemini still stripped; hydrate writes path; GET overlays `ok`; capture miss stays PARTIAL; canvas file node only when path present)
- [x] Implement allowlist + capture/persist/hydrate + frame route
- [x] Verify focused Vitest; document uvai.io re-verify (GET hydrate, no architecture invent)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Keyframes keep `t_s` + `desc`. `image_path` is a Blob or app-served URL only after JPEG bytes were captured. `metrics.keyframes_images` is `ok` when every keyframe has a durable path, otherwise `partial`. Identity `source_hash` unchanged. Envelope stays `success`.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/keyframe-frame-capture.test.ts src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/emit-json-canvas.test.ts src/app/api/video/pack/__tests__/route.test.ts src/app/api/video/pack/frames`
* **Proof Artifact:** `cd apps/web && vitest run src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/video-pack.test.ts src/lib/__tests__/video-pack-store.test.ts src/lib/__tests__/emit-video-pack.test.ts src/lib/__tests__/emit-json-canvas.test.ts src/lib/__tests__/keyframe-frame-capture.test.ts src/app/api/video/pack src/app/api/v1/video/pack` → 9 files, 84 passed, 1 skipped.

## 4. Post-Task Reflection
* **What was done:** Wired a real capture/upload path. Sanitize now keeps Blob + `/api/video/pack/frames/{id}/{t_s}` only. GET/persist hydrate existing packs by capturing storyboard tiles at `t_s`, persisting to Blob or serving the JPEG from the new frame route. `keyframes_images` is `ok` when every keyframe has a durable path; otherwise PARTIAL stays honest. Canvas emits a file node only when that path is present.
* **Why it was needed:** B2 left prod packs honest-but-empty (`QjZ5ohr7sGA` 17/17 null). CoS UNPARK wants FULL without inventing thumbs or Gemini URLs.
* **How it was tested:** RED then GREEN Vitest for allowlist, hydrate, GET overlay, storyboard crop of a real JPEG sprite, frame route 200/404, and canvas file-node emit. Surrounding pack suite 84 passed.
