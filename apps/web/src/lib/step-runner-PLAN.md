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
- [ ] RED: `runbook-steps.test.ts` on a fixture trimmed from the real `pBsT6v-ciO8` pack (ids, anchors, kinds, verification, prerequisites, markdown, time lookup, hash).
- [ ] GREEN: `runbook-steps.ts`.
- [ ] Schema: optional `start_s/end_s` (types, zod, parser, prompt) + `code_snippets` passthrough; tests.
- [ ] Player hook: cue-only seek option; test.
- [ ] Chat: step context validation + windowed prompt; grounding + route tests.
- [ ] UI: `StepRunner`, `StudioRunbookPane`, Runbook tab, chat chip; jsdom tests (Next seeks, hash, autoplay toggle, prerequisites, markdown mode, troubleshoot).
- [ ] Wire `OneLoopStudio`; `RUNBOOK.md` export; progress persistence.
- [ ] Verify: focused Vitest, `tsc --noEmit`, eslint on touched files, full web suite.

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** With a stored pack selected, Deliverables opens on **Runbook → Step-by-Step Runner**. Step 0 is a prerequisites checklist from `stack.tools`/stack checks. `Next` advances `Step n of N`, scrolls the runner to top, writes `#step-n`, seeks the player to the step's anchored start (cue-only when autoplay is off, pauses at range end when on), and the chat chip reads "Grounded to Step n". Steps without pack evidence show "No verified timestamp" and never seek. `Full Runbook Markdown` shows/copies/downloads `RUNBOOK.md`.
* **Verification Method:**
  * `cd apps/web && npx vitest run src/lib/__tests__/runbook-steps.test.ts src/components/studio/__tests__/StepRunner.test.tsx src/components/__tests__/OneLoopStudio.runbook.test.tsx src/lib/__tests__/chat-pack-grounding.test.ts src/app/api/__tests__/chat-pack-grounding-route.test.ts src/lib/__tests__/use-youtube-player.test.ts src/lib/__tests__/emit-video-pack.test.ts src/lib/__tests__/video-pack-structure.test.ts src/lib/__tests__/action-surface.test.ts`
  * `npx tsc --noEmit` · `npx eslint <touched files>` · `npx vitest run` (full web suite)
* **Proof Artifact:** (filled in §4 on completion)

## 4. Post-Task Reflection
* **What was done:**
* **Why it was needed:**
* **How it was tested:**
