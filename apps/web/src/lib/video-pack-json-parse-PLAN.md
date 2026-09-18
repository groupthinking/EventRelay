# TASK: Truncate-safe Video Pack spec JSON parse

## 1. Goal & Scope
* **Objective:** GET/pack extract no longer 503s when Gemini 3.8 Flash returns truncated/unparseable spec JSON mid-string (Eggs / `vuLPccrooHU`, position ~8050).
* **Context:** `parseSpecJson` tries `JSON.parse` then slices first `{` to last `}`. A last `}` inside an unterminated string (code braces in `full_text`) still throws `Unterminated string in JSON at position 8050`, persisted as a 503.
* **Scope:**
  * `apps/web/src/lib/video-pack-extractor.ts` — repair/truncate-safe parse + clearer unrecoverable error
  * `apps/web/src/lib/__tests__/video-pack-extractor.test.ts` — mid-string ~8050 class + fail-closed garbage
 * *Initial check:* Extend existing parser. Do not touch App Builder emit, trail-velvet, or studio.deploy G.A.T.E. Do not invent pack fields, secrets, or STT.

## 2. Execution Plan
- [x] Lock failing Vitest for unterminated string at position ~8050 (braces inside the cut string)
- [x] Repair: close truncated strings, drop incomplete keys, close open containers — keep only Gemini-emitted prefix
- [x] Clearer error with parse position when unrecoverable; identity-only after repair still fail-closed
- [x] Run focused Vitest; open PR (do not merge)

## 3. Definition of Done (Success Verification)
* **Expected Outcome:** Salvageable truncated spec JSON yields a spec from the real prefix (no invented concepts/stack). Unrecoverable JSON throws `unparseable spec JSON at position N` (truncated mid-string when applicable). Eggs-class ~8050 no longer 503s on parse.
* **Verification Method:** `cd apps/web && npm run test -- src/lib/__tests__/video-pack-extractor.test.ts`
* **Proof Artifact:** 15 passed (1 file) on GREEN after RED (`Unterminated string in JSON at position 8015` from the old last-`}` slice).

## 4. Post-Task Reflection
* **What was done:** `parseSpecJson` now repairs Gemini-truncated objects (close cut strings, drop valueless keys, close open containers) and emits a position-bearing truncated-mid-string error when the payload is not a spec object.
* **Why it was needed:** Eggs/`vuLPccrooHU` GET/pack 503'd because last-`}` salvage still failed when that brace lived inside an unterminated `full_text` string at position 8050.
* **How it was tested:** Vitest RED then GREEN on `video-pack-extractor.test.ts` — 8050-class salvage, prefix-only fields, unrecoverable position error, identity-only cite still fail-closed.
