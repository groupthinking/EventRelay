# UVAI integration checkpoint

Goal: use the real pinned Vercel Chatbot foundation for a verified video-to-guide workflow, preserving the full uploaded-video/audio/visual/evidence/follow-up/download goal.

Canonical issue: #2390. Branch: feat/uvai-chatbot-foundation-2390.
Upstream: vercel/chatbot c2f8235e1f3ea903ad8b7f61447c4f74164b5c58, Apache 2.0.

Actual import: source snapshot under templates/uvai-chatbot, outside the existing npm workspaces. Upstream CI/husky hooks are intentionally omitted. Existing production app and pack-store architecture remain unchanged.

Changed behavior: chat model tools are restricted to createVideoGuide/readVideoGuide; document writes accept text only. Guide tool calls the configured existing Video Pack service, validates source identity, timed audio and citation IDs, labels sampled/missing visual evidence, generates bounded JSON, saves an owned text artifact and returns measured token usage. Downloads enforce ownership. No payment tests.

Limits: YouTube URL intake only in this adapter. Uploaded-video intake is unfinished. No application replacement, provider-quality validation or live end-to-end success has been claimed. Citation validation proves references exist, not that model claims are faithful. Existing guides avoid repeat generation after extraction; concurrent duplicate generation still needs a database-backed reservation. Processing status requires retry/polling; no fabricated percentage. Source Video Pack service has shared public-video semantics; this adapter is not for private uploaded media. Account migration and source-player panel integration remain unfinished.

Verification: run npm run test:video-guide for deterministic fixture/security tests (not live AI). Run the pinned pnpm install, TypeScript and build checks. Check receipts in this directory for actual results.

Blockers: Vercel metadata inspection returned 403: forbidden, "You don't have permission to list the project environment variable." No Vercel CLI executable exists here. No local provider/database configuration has been demonstrated. First npm install failed ERESOLVE: @vercel/otel peer @opentelemetry/api-logs <0.200.0 conflicts with template 0.200.0. Pinned pnpm install is the next dependency verification path.

Next: finish dependency/type/build verification and focused route authorization/failure tests. Add durable guide generation reservation and job polling. Connect the selected foundation to owned video ingestion/evidence and run one permitted tutorial through actual providers, browser review/follow-up/download, recording citations, gaps, usage and costs. Do not merge or replace production before required gates and customer acceptance evidence pass.

One-time resumption timer configured for Oct 9, 2026 17:23:16 America/Chicago. This does not imply continuous execution after a turn ends.
