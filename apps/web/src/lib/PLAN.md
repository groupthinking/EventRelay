# TASK: Video Pack formation (architecture, artifacts, grounded stack.tools)

## 1. Goal & Scope
* **Objective:** Raise UVAI Video Pack extract toward Gemini-8 formation quality: architecture pipeline, artifact shapes, and stack tools grounded in the video. Stack checks come only from `stack.tools[]`. No forced Shopify CLI gate on Cloudflare/x402 sources. No chat code dumps.
* **Context:** Live pack for `MNNfat_QP0E` emits insight/SOP plus an unrelated Shopify CLI check. Checks are compiled from `linked-sop.ts` catalog/`STACK_CHECKS`, not pack evidence. CoS/Hayden authorized this cut.
* **Scope:**
  * `apps/web/src/lib/video-pack-extractor.ts` — prompt + parse architecture/artifacts/stack
  * `apps/web/src/lib/video-pack.ts` — persist those fields; identity hash unchanged
  * `apps/web/src/lib/emit-video-pack.ts` — pass formation through the citation
  * `apps/web/src/lib/linked-sop.ts` — stack checks only from pack tools
  * `apps/web/src/components/OneLoopStudio.tsx` + `dashboard-store.ts` — bind UI to pack tools
  * Tests: MNNfat-style fixture, check generation, UI binding
 * *Initial check:* Extend Video Pack v0. Do not add Primer, quiz/chat, Redis/Upstash, G.A.T.E., Stripe, or `/dashboard` teleports. Model stays `google/gemini-3.8-flash`.

## 2. Execution Plan
- [x] Lock failing tests (schema + MNNfat fixture + checks + UI binding)
- [x] Extend extractor prompt, Zod/types, and applyExtractedSpec
- [x] Generate stack checks only from `stack.tools[]`
- [x] Bind studio on `/` to pack formation (architecture, artifacts, checks)
- [x] Verify focused Vitest + identity goldens; hashed persist contract
- [ ] Ready PR (GitHub issue_write 403 — no `Closes #<n>` available)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Cloudflare/x402 evidence yields Cloudflare/x402 tools and checks, never Shopify CLI. Pack includes architecture stages and artifact shapes (path/purpose/interface). `source_hash` goldens unchanged. Studio checks unlock on `/`.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/video-pack-extractor.test.ts src/lib/__tests__/video-pack.test.ts src/lib/__tests__/linked-sop.test.ts src/lib/__tests__/official-templates.test.ts src/lib/__tests__/emit-video-pack.test.ts src/lib/__tests__/studio-pipeline-status.test.ts src/lib/__tests__/video-pack-store.test.ts src/lib/__tests__/action-surface.test.ts src/store/__tests__/dashboard-store.test.ts src/app/api/video/pack src/app/api/v1/video/pack`
  * Identity goldens: `auJzb1D-fag`, `jNQXAC9IVRw`
* **Proof Artifact:** 11 files, 92 passed. Live GET `https://uvai.io/api/video/pack?video_id=MNNfat_QP0E` and GET `?source_hash=c63de3de992d40b4ba2147ef441324f2bda8030a7b63dc260b1fa33bdcf1b666` both 200 with the same identity hash. Current live pack has Cloudflare/x402/MCP concepts, no Shopify, but `architecture`/`stack.tools`/`artifacts` are empty until re-extract after merge.

## 4. Post-Task Reflection
* **What was done:** Extended Video Pack v0 extract with Zod-parsed `architecture`, `artifacts[]`, and `stack.tools[]`. Stack checks now come only from pack tools. Studio on `/` renders formation and unlocks those checks in place.
* **Why it was needed:** Industry checks were compiled from catalog + topics, so a Cloudflare/x402 video could still get a forced Shopify CLI gate. Gemini-8 altitude needs grounded tools, pipeline stages, and artifact shapes without chat code dumps.
* **How it was tested:** RED then GREEN Vitest for extractor, SOP checks, emit citation, studio binding, identity goldens, and pack store persist. Live hashed GET confirmed the MNNfat identity contract.
