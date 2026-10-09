# Pinned template import

Repository: https://github.com/vercel/chatbot
Commit: c2f8235e1f3ea903ad8b7f61447c4f74164b5c58
License: Apache 2.0; upstream LICENSE retained.

This directory is an actual source import, not a recreated stylesheet. It is isolated from the current apps/web deployment. Upstream .github workflows and .husky hooks were not imported.

UVAI adapters: lib/uvai/video-guide.ts; lib/ai/tools/create-video-guide.ts; app/(chat)/api/video-guide/download/route.ts. Chat tools, greeting, document kind validation and package name/scripts were narrowed for UVAI. Original source paths and package lock are retained for reproducible inspection.

Run corepack pnpm install --frozen-lockfile --ignore-scripts, then npm run test:video-guide and npm run type-check. The template requires its original database/auth/AI runtime configuration. Configure UVAI_PACK_SERVICE_ORIGIN to the trusted HTTPS origin of your existing pack extraction service. UVAI_PACK_SERVICE_TOKEN is optional server-side service authentication; never expose it to the browser. Only permitted public YouTube sources are supported in this initial adapter. No uploads, previews or deployment claims.

Security adaptations: Auth.js 5.0.0-beta.32, Next 16.3.8 and patched dependencies intentionally replace vulnerable inherited versions; this preserves the upstream source pin, not the original dependency bytes. Inspect evidence/template-import.json and resume-audit.json. The source-player and PostgreSQL admission controls are UVAI additions; local tests do not establish live model quality.
