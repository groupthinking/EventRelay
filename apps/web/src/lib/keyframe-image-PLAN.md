# TASK: B2 keyframe image_path honesty (PARTIAL, no invented URLs)

## 1. Goal & Scope
* **Objective:** Stop successful Video Packs from looking complete when every keyframe `image_path` is null. Either persist a durable captured image URL, or fail closed with honest PARTIAL provenance. Never invent paths.
* **Context:** Prod GET 200 for `QjZ5ohr7sGA` and `7-2mQGjcuc4` returns 17/17 keyframes with `image_path: null`. Extractor prompt asks Gemini for `keyframes: [{ t_s, desc }]` only; parse copies `image_path` from Gemini JSON that never supplies a captured asset. Vercel pack path has no frame-capture/upload store (Upstash REST is JSON-only; `@vercel/blob` is not wired).
* **Scope:**
  * `apps/web/src/lib/video-pack-extractor.ts` — do not ask Gemini for `image_path`; strip any invented Gemini path
  * `apps/web/src/lib/video-pack.ts` — persist + GET-time PARTIAL annotation (`metrics.keyframes_images`, provenance note)
  * Focused Vitest for extractor + pack GET
 * *Initial check:* Reuse extractor + `applyExtractedSpec` + GET `recordToResponse`. Do not add Blob/S3, App Builder emit, architecture/code_snippets, or studio.deploy.

## 2. Execution Plan
- [x] Lock failing tests (Gemini invented path stripped; desc-only → PARTIAL; GET overlay for stored null paths)
- [x] Prompt + parse fail-closed; annotate persist + GET
- [x] Verify focused Vitest; document prod re-verify (GET overlay, no re-extract required)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Keyframes keep `t_s` + `desc`. `image_path` stays null unless a durable capture exists (none today). Pack metrics `keyframes_images=partial` and provenance notes say why. Envelope stays `status: success` so emit-video-pack still verifies. Identity `source_hash` unchanged.
* **Verification Method:** `cd apps/web && npx vitest run src/lib/__tests__/video-pack-extractor.test.ts src/app/api/video/pack/__tests__/route.test.ts`
* **Proof Artifact:** `cd apps/web && vitest run src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/video-pack.test.ts src/lib/__tests__/video-pack-store.test.ts src/lib/__tests__/emit-video-pack.test.ts src/app/api/video/pack src/app/api/v1/video/pack` → 6 files, 63 passed, 1 skipped.

## 4. Post-Task Reflection
* **What was done:** Confirmed no frame-capture/upload on the Vercel pack path. Stopped copying Gemini `image_path`. GET/persist now annotate `metrics.keyframes_images=partial` with a provenance note. Envelope stays `success`.
* **Why it was needed:** Prod packs QjZ5ohr7sGA and 7-2mQGjcuc4 returned 17/17 null `image_path` with no honesty marker.
* **How it was tested:** RED then GREEN Vitest for prompt, invented-URL strip, applyExtractedSpec PARTIAL, GET overlay. Surrounding pack suite 63 passed.
