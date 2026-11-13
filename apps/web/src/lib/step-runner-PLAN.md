# TASK: Studio Deliverables → synchronized Step Runner (Runbook)

## 0. Intent vs execution (read-only audit, 2026-10-17)

**Market intent (locked in AGENTS.md):** paste a YouTube URL → hashed Video Pack → *action / ship*, not transcription. The user should not parse a wall of text to build what they watched.

**What the code does today (verified by reading source + live GETs):**

| Surface | Source | Finding |
| --- | --- | --- |
| `/api/video/pack` | `video-pack.ts`, `video-pack-extractor.ts` | Live GET for `pBsT6v-ciO8` and `auJzb1D-fag` returned 200 with transcript segments (`start_s/end_s`), `chapters[start,end]`, `requirements` (`REQ-01…`), `action_items` (`ACT-01…`), `stack.tools[].check`, `code_snippets`, keyframes with stills, `grounded_spec` citations (`startSeconds/endSeconds/quote`). |
| Deliverables pane | `StudioIdeOutput.tsx` | Seven static tabs. SOP steps render as a numbered list with **no timestamps, no seek, no per-step content, no verification**. Nothing in the pane drives the player. |
| Player sync | `use-youtube-player.ts`, `GroundedSpecReview.tsx` | `seekTo` exists and is wired only to the Spec tab citations. `currentTime`/`isPlaying` are polled but no consumer uses them. `seekTo` always auto-plays (no cue-only mode). |
| Chat grounding | `chat-pack-grounding.ts`, `api/chat/route.ts` | Whole-pack system prompt (12k-char transcript + SOP + visuals + actions). No step scoping. |
| Client pack shape | `emit-video-pack.ts` | `verifyIdentityPack` drops `code_snippets`, so the browser never sees snippets the extractor produced. |
| Timestamps on steps | extractor prompt | `requirements` / `action_items` carry **no time fields**. Only chapters, segments, visuals, keyframes and grounded-spec citations are time-anchored. The emitted App Builder mini-app already derives SOP seek times honestly from chapters/visuals (`deriveSopTimestampFromPackFields`). |

**Verdict:** extraction matches intent (structured, time-anchored evidence exists). The Studio presentation does **not**: the pack is shown as reference text, so the "active execution copilot" promise is unmet. Intent ≠ execution at the Deliverables layer, not at the pipeline layer.

**Parallel agents (checked 2026-10-17 16:40 UTC):** #2436 (`cursor/studio-playflow-ide-rewire-b008`) and #2437 (`cursor/studio-ship-this-playflow-5011`) both edit `StudioIdeOutput.tsx` (Tools/Intent tabs, new props) and the `OneLoopStudio.tsx` toolbar. Neither touches the player hook, chat grounding, the pack schema, or adds a Runbook tab. This cut stays additive (new files, one new tab, new optional props) to keep the eventual merge mechanical.

## 1. Goal & Scope
* **Objective:** Turn the Deliverables pane from a static reference into a 1-of-N step runner whose steps are temporally anchored to the video, with a Step 0 prerequisites checklist, a Full Runbook Markdown mode, and chat grounded to the active step.
* **Context:** Pollen Robotics Reachy Mini assembly guide as the UX benchmark. Zero-Sim rule: never invent evidence — a step with no pack-derived anchor shows `null` and disables seek instead of guessing.
* **Scope:**
  * `apps/web/src/lib/runbook-steps.ts` — new pure compiler: pack (+ linked SOP) → `Runbook { prerequisites, steps[] }`, markdown renderer, time → step lookup, hash helpers.
  * `apps/web/src/lib/video-pack-types.ts`, `video-pack.ts`, `video-pack-extractor.ts` — optional `start_s/end_s` on requirements and action items (prompt + parser). No `VIDEO_PACK_STRUCTURE_SCHEMA_VERSION` bump (would force paid re-extraction of every stored pack).
  * `apps/web/src/lib/emit-video-pack.ts` — pass `code_snippets` through to the client citation.
  * `apps/web/src/lib/use-youtube-player.ts` — `seekTo(seconds, { autoplay })` cue-only option (default unchanged).
  * `apps/web/src/lib/chat-pack-grounding.ts`, `api/chat/route.ts` — validated `step` context → windowed transcript + step block in the system prompt.
  * `apps/web/src/components/studio/StepRunner.tsx`, `StudioRunbookPane.tsx` — stepper, step card, prerequisites, markdown mode.
  * `apps/web/src/components/studio/StudioIdeOutput.tsx` — new `Runbook` tab (first, default when present) via one optional prop.
  * `apps/web/src/components/studio/StudioIdeChat.tsx` — optional `stepContext` chip + body field.
  * `apps/web/src/components/OneLoopStudio.tsx` — compile runbook, wire player, progress persistence, chat re-grounding.
  * `apps/web/src/store/dashboard-types.ts` — optional `runbookProgress` on `Video`.
  * `apps/web/src/lib/action-surface.ts` — `RUNBOOK.md` in the ship package.
 * *Initial check:* `sopStepsFromPack` / `deriveSopTimestampFromPackFields` (emit-app-builder-sandbox.ts) already derive honest SOP seek times; the token helpers are exported and reused rather than duplicated. `renderDeployMarkdown` is the markdown precedent. No new dependencies.

### Hypotheses considered
1. **Prompt-only:** ask Gemini for `timestamp_range` on every requirement and rely on it. Rejected as the sole path: stored packs would need a paid re-extract, and model-reported ranges still need an honest fallback.
2. **Client-only derivation:** anchor steps from chapters/segments/visuals/grounded-spec citations already on the pack. Works for every stored pack today; coarse (chapter-level) when text overlap is weak.
3. **Both (chosen):** additive optional `start_s/end_s` in the extractor for new packs, plus deterministic derivation with explicit `anchor` provenance for everything else. Unanchored steps stay `timestamp_range: null`.

## 2. Execution Plan
- [x] RED: `runbook-steps.test.ts` on the real `pBsT6v-ciO8` pack slice (ids, anchors, kinds, verification, prerequisites, markdown, time lookup, hash). First run: 13/16 passed; the 3 failures were the range-extension rule producing `[268, 290.5]` for REQ-03 (segments 35–36 continue the outreach step) — verified against the segment text and pinned.
- [x] GREEN: `runbook-steps.ts` (16/16).
- [x] Schema: optional `start_s/end_s` (types, zod, parser, both prompts) + `code_snippets` passthrough; tests.
- [x] Player hook: `seekTo(seconds, { autoplay })`; jsdom hook test with stubbed IFrame API.
- [x] Chat: `parseChatStepContext` (zod, strict, bounded) + windowed prompt; grounding + route tests (400 `step_context_invalid` / `step_context_requires_pack`).
- [x] UI: `StepRunner`, `StudioRunbookPane`, Runbook tab (first, default when present), chat chip; 9 jsdom tests.
- [x] Wire `OneLoopStudio`; `RUNBOOK.md` export; `Video.runbookProgress`; 5 integration tests.
- [x] Verify: focused Vitest, `tsc --noEmit`, eslint on touched files, full web suite, `next build`, live route round-trip, headed browser walkthrough.

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** With a stored pack selected, Deliverables opens on **Runbook → Step-by-Step Runner**. Step 0 is a prerequisites checklist from `stack.tools`/stack checks. `Next` advances `Step n of N`, scrolls the runner to top, writes `#step-n`, seeks the player to the step's anchored start (cue-only when autoplay is off, pauses at range end when on), and the chat chip reads "Grounded to Step n". Steps without pack evidence show "No verified timestamp" and never seek. `Full Runbook Markdown` shows/copies/downloads `RUNBOOK.md`.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/runbook-steps.test.ts src/components/studio/__tests__/StepRunner.test.tsx src/components/__tests__/OneLoopStudio.runbook.test.tsx src/lib/__tests__/chat-pack-grounding.test.ts src/app/api/__tests__/chat-pack-grounding-route.test.ts src/lib/__tests__/use-youtube-player.test.ts src/lib/__tests__/emit-video-pack.test.ts src/lib/__tests__/video-pack-structure.test.ts src/lib/__tests__/action-surface.test.ts`
  * `npx tsc --noEmit` · `npx eslint <touched files>` · `npx vitest run` (full web suite)
* **Proof Artifact (2026-10-17, head of `cursor/studio-step-runner-3c1b`):**
  * Focused Vitest (listed above): all green — `runbook-steps` 16, `StepRunner` 9, `OneLoopStudio.runbook` 5, grounding 11, route 6, hook 3, plus extractor/emit/structure/action-surface additions.
  * Full web suite: **173 files, 1563 passed, 28 skipped** (all pre-existing opt-ins: Redis-gated G.A.T.E. cases, one live clip probe).
  * `npx tsc --noEmit` exit 0 · `npx eslint` on every touched file exit 0 · `npx next build` exit 0.
  * Live route round-trip (one-off test outside the repo, real `POST /api/chat`, memory pack store seeded with the live pack, real Vercel AI Gateway call): HTTP 200 in 1086 ms, answer *"The speaker says, 'Step one: search up SeaDance 2.5, find any provider,' at 4:07–4:14 in the video."* — the step's anchored range and quote from the windowed transcript.
  * Headed Chrome walkthrough on the production build with the live pack seeded in localStorage: Runbook tab default; Step 0 lists 3 tools; Next → `#step-1`, `4:07–4:14 · Transcript segment`, chat chip "Grounded to Step 1 of 7", keyframe `/api/video/pack/frames/pBsT6v-ciO8/249`; Step 3 shows `interface SpecAdPitch`; completion persisted to `runbookProgress`; RUNBOOK.md view + `download="RUNBOOK.md"`; Troubleshoot focused the composer with "Paste the error or ask about Step 3…". Recording: `studio-step-runner-walkthrough.mp4`.
  * Not verifiable in this VM (environment, not code): the YouTube embed returned **Error 153** on `http://localhost` (embed requires an https referer; CSP already allows youtube.com; production is https), and the production-mode `src/proxy.ts` guard returned 503 "distributed rate limiting is not configured" because no Upstash credentials exist here. Live Gemini extraction of the new optional `start_s/end_s` fields was not exercised (no `GOOGLE_API_KEY`); the parser path is unit-tested.

## 4. Post-Task Reflection
* **What was done:** Added a pure runbook compiler that anchors pack requirements / action items (or the linked SOP) to the video timeline from pack evidence only, with provenance per step and `null` when none exists; a Step Runner (stepper, Step 0 prerequisites, per-step action card, cue/clip playback, hash + scroll, local completion notes) and a RUNBOOK.md reference mode inside Deliverables; step-scoped chat grounding end to end (client chip → validated `step` field → windowed system prompt); optional extractor time ranges and client-visible code snippets; `RUNBOOK.md` in Export.
* **Why it was needed:** The pipeline already produced time-anchored evidence, but the Deliverables pane showed it as static text, so the "active execution copilot" intent was unmet at the presentation layer (§0). The runner closes that gap without inventing evidence and without forcing a paid re-extract of stored packs.
* **How it was tested:** RED→GREEN Vitest on the live `pBsT6v-ciO8` pack slice, jsdom component/integration tests, type-check, lint, production build, one real gateway round-trip through the real route, and a recorded headed-browser walkthrough of the production build.

## 5. Review update (2026-10-28)

The test fixture now uses a freshly fetched, source-bound saved pack for `auJzb1D-fag`, in line with the repository fixture rule. The earlier `pBsT6v-ciO8` results above record the original implementation test and remain historical evidence. Review fixes also bind chat prompts to the server-compiled step, reset chat history on step changes, preserve initial step links, restore grounded acceptance checks with explicit timing, bound step IDs, retain actions with malformed optional timing, and reset clip pause state when seeking again. The current full web suite passed: 174 files, 1571 tests passed, 28 skipped; lint, type check, and production build passed locally. Hosted checks and reviewer state remain separate gates.
