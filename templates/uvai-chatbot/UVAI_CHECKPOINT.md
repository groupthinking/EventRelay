# UVAI integration checkpoint

Goal: use the real pinned Vercel Chatbot foundation for a verified video-to-guide workflow, preserving the full uploaded-video/audio/visual/evidence/follow-up/download goal.

Canonical issue: #2390. Branch: feat/uvai-chatbot-foundation-2390.
Upstream: vercel/chatbot c2f8235e1f3ea903ad8b7f61447c4f74164b5c58, Apache 2.0.

Actual import: source snapshot under templates/uvai-chatbot, outside the existing npm workspaces. Upstream CI/husky hooks are intentionally omitted. Existing production app and pack-store architecture remain unchanged.

Changed behavior: chat model tools are restricted to createVideoGuide/readVideoGuide; document writes accept text only. Guide tool calls the configured existing Video Pack service, validates source identity, timed audio and citation IDs, labels sampled/missing visual evidence, generates bounded JSON, saves an owned text artifact and returns measured token usage. Downloads enforce ownership. No payment tests.

Limits: YouTube URL intake only in this adapter. Uploaded-video intake is unfinished. No application replacement, provider-quality validation or live end-to-end success has been claimed. Citation validation proves references exist, not that model claims are faithful. Existing guides avoid repeat generation after extraction; concurrent duplicate generation still needs a database-backed reservation. Processing status requires retry/polling; no fabricated percentage. Source Video Pack service has shared public-video semantics; this adapter is not for private uploaded media. Account migration and source-player panel integration remain unfinished.

Verification: pinned pnpm install, npm run type-check and npm run build exited 0. Eight deterministic fixture evidence/security tests and six local production-server HTTP auth/routing checks passed. Inspect evidence/verification.json, build.log and runtime-smoke.json. Database migrations were skipped because POSTGRES_URL is absent; no DB success claim. Actual imported upstream file hashes and adapted paths are in evidence/template-import.json. Public cached pack inspection accepted 28 timed audio segments and zero frame-backed visual observations; evidence/cached-pack-inspection.json explicitly marks it cached, not live re-extraction or provider-quality proof.

Further narrowed behavior: generic uploads and guest-account creation are disabled. Only text artifact handlers are registered; Pyodide loading removed. New guide tool results render status, gaps, artifact preview and download link. Follow-up allows a bounded second model step after reading evidence, with tools disabled on that second step. Existing unused upstream modules are retained for provenance, not enabled tools.

Blockers: Vercel environment metadata inspection returned 403: "You don't have permission to list the project environment variable." No Vercel CLI executable exists here. Local POSTGRES_URL, AUTH_SECRET, AI_GATEWAY_API_KEY and UVAI_PACK_SERVICE_ORIGIN are absent. The HTTP smoke used an ephemeral authentication test secret, not a production credential. Live workflow/provider quality, browser review, owned uploaded media and deployment are NOT VERIFIED. Failed attempts and their corrections are preserved in the verification receipt.

Next: inspect fresh branch source and receipts; add durable guide generation reservation, source-player/evidence panel and job polling. Connect the selected foundation to owned video ingestion/evidence and run one permitted tutorial through actual providers, browser review/follow-up/download, recording citations, gaps, usage and costs. Do not merge or replace production before required gates and customer acceptance evidence pass.

One-time resumption timer configured for Oct 9, 2026 17:23:16 America/Chicago. This does not imply continuous execution after a turn ends.
