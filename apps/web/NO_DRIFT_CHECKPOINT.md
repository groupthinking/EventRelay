# NO-DRIFT Checkpoint — UVAI Rebuild
**Activated:** 2026-10-07 22:30 CDT
**Schedule:** Hourly for 24 hours (checkpoints 01–24)

## /goal: Build UVAI's first verified video-to-output workflow.

## Original Goal (one sentence)
Build UVAI's first verified video-to-output workflow: a user uploads a video or supplies a URL, UVAI processes it into timestamped guides/specs/prototypes, and the user reviews, chats, and downloads real artifacts.

## Scope
- **In scope:** Complete vertical slice: upload/URL → store → extract evidence → generate timestamped guide → display beside video → download. Then extend to specs and prototypes.
- **Out of scope (per spec):** Marketplaces, agent swarms, mobile apps, broad autonomous integrations. Arbitrary website support. Bypassing source access restrictions.

## Acceptance Criteria
1. Successful video ingestion (upload + URL) — VERIFIED by real upload test
2. Actual audio and visual processing — VERIFIED by inspecting pipeline output
3. Timestamp-grounded outputs — VERIFIED by clicking timestamps
4. Clickable evidence navigation — VERIFIED by manual click test
5. Follow-up questions using source evidence — VERIFIED by grounded chat test
6. Downloadable artifacts — VERIFIED by downloading real files
7. Safe generation and preview of web prototype — VERIFIED by isolated execution
8. Honest handling of unsupported inputs and failed jobs — VERIFIED by failure test

## Current Evidence (activation)
- **ASSERTED:** UVAI exists at uvai.io with Studio, landing, pricing pages
- **ASSERTED:** Studio processes YouTube URLs into Video Packs
- **NOT VERIFIED:** Whether the current implementation meets the acceptance criteria above
- **NOT VERIFIED:** Whether upload path works (spec prioritizes upload as dependable first path)
- **NOT VERIFIED:** Whether prototype generation is safe and isolated

## Decisions and Assumptions
- **Decision:** Treat existing code as unverified. Verify each acceptance criterion from scratch.
- **Decision:** Prioritize upload path per spec (more dependable than URL scraping)
- **Assumption:** Current Vercel deployment (v0-uvai) is the target. Will verify.
- **Assumption:** Existing Stripe billing ($39/mo Pro) stays. Will verify entitlements.

## Changed Files
(none yet — activation checkpoint)

## Verification Evidence
(none yet — activation checkpoint)

## Blockers
- None yet. Starting verification.

## Next Executable Action
Inspect the current codebase: verify what exists for upload, processing pipeline, and output generation. Map existing code to acceptance criteria.

---
## Checkpoint Format (for hourly runs)

Checkpoint: XX/24 | Time:
Goal:
Evidence since last checkpoint:
Drift detected and correction:
Next action:
Blocker or decision needed:

Step | VERIFIED / IN PROGRESS / NOT STARTED | Evidence
