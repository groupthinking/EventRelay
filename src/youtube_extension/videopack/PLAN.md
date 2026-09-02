# TASK: UVAI Step 2 — paste-URL emits a hashed Video Pack

## 1. Goal & Scope
* **Objective:** Pasting a YouTube URL (or calling the existing pack API) produces a real VideoPack v0 with a stable hash/version tied to that video ID. Retries of the same URL reuse the same pack; a different video ID gets a different hash.
* **Context:** Step 1 (Workflow Pro checkout) is done. `src/youtube_extension/videopack` already defines VideoPackV0 + `stable_hash`. Live `POST /api/v1/video/pack` is a shell: new UUID, `datetime.now()`, no `source_hash`, no persist. The uvai.io paste path (`processVideo`) never calls it.
* **Scope:**
  * Use existing VideoPackV0. Do not invent a second pack format.
  * Hash = SHA-256 of compact canonical JSON `{"version":"v0","video_id":"<id>"}` stored on `provenance.source_hash`.
  * Persist under `storage/video_packs/<video_id>/pack.json` via existing `write_pack` / `read_pack`.
  * Wire FastAPI `POST /api/v1/video/pack` and the existing uvai.io paste surface (`POST /api/video/pack` + `processVideo`).
  * Tests: same video ID → same hash; different video ID → different hash; URL variants collapse to one video ID.
* **Out of scope:** Qwen/Qwen3.8-27B extract, vLLM, Origin wasm, new public brand, FORGE/slingshot/ClipToAction.

## 2. Execution Plan
- [x] Confirm existing videopack schema/hash and the live paste-URL gap
- [x] Lock failing hash-stability tests (Python identity/store + Next.js route)
- [x] Implement identity hash, get-or-create store, and wire both APIs
- [x] Attach the returned pack citation on dashboard `processVideo`
- [x] Verify tests; open PR against main (issue create returned 403)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Paste or `POST` of a YouTube URL returns VideoPack v0 whose `provenance.source_hash` is stable for that video ID and different for another video ID. A second request for the same ID reuses the stored pack.
* **Verification Method:**
  * `PYTHONPATH=src pytest tests/unit/test_videopack_identity.py tests/unit/test_videopack_store.py -v`
  * `cd apps/web && npx vitest run src/lib/__tests__/video-pack.test.ts src/app/api/video/pack src/store/__tests__/dashboard-store.test.ts`
* **Proof Artifact:** Python 102 passed (`test_videopack_*`); frontend 47 passed (video-pack + `/api/video/pack` + dashboard-store). Live hashes: `auJzb1D-fag` → `2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea`; `jNQXAC9IVRw` → `97150a5c21eef3d12a4543ce2108ca28fd6f829db1da120d7e75655ab471f97d`.

## 4. Post-Task Reflection
* **What was done:** Wired existing VideoPackV0 so paste-URL / `POST /api/v1/video/pack` / `POST /api/video/pack` emit a v0 identity pack with a stable `provenance.source_hash` and persist/reuse by video ID.
* **Why it was needed:** The library existed; the live path synthesized a new unhashed pack on every call and the uvai.io paste path never called it.
* **How it was tested:** TDD hash-stability tests (same ID / URL variants / different ID), store reuse on `pack.json`, Next.js route tests, dashboard `processVideo` attaches the citation. GitHub `issue_write` returned 403 so no `Closes #` issue could be opened from this agent.
