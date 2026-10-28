# UVAI Website — Structural Inventory

Generated 2026-10-06. Map of the full `apps/web/` codebase for a from-scratch rebuild.
Source: Next.js 16 (App Router), React 19, TypeScript. Package name `eventrelay-web`.
Live at https://uvai.io (Vercel project `v0-uvai`).

---

## 1. Routes / Pages (`src/app/`)

| Path | File | What it renders / purpose |
|---|---|---|
| `/` | `page.tsx` (140 lines) | Landing page: Nav + Footer + `HomePasteForm` (YouTube URL → `/studio?video=`) + `HomeProCheckout` (Stripe Pro upsell) + offers list. Light card system. Uses `studio-cards.css`. |
| `/studio` | `studio/page.tsx` → `studio/StudioShell.tsx` → `components/OneLoopStudio.tsx` | **The product.** Three-pane IDE workbench: video pane, pack-grounded chat, action-extraction output (Events/Lingo/Tools/Intent/Signals/Spec/Transcript tabs). Toolbar: Run/Cancel, stored packs, Export, Build live. Suspense wrapper; reads `agentWorkflowUi` feature flag. |
| `/pricing` | `pricing/page.tsx` (223 lines) | Pricing page: Core vs Pro capability lists, Core/Pro/Enterprise comparison table, `ProCheckoutButton`, `ProRenewPanel`, `CheckoutSuccessActivator`. Locked prices: Pro $39/mo or $390/yr, Maintain $199/mo, Ship per-job quote. |
| `/login` | `login/page.tsx` + `GoogleSignInButton` | Google OAuth sign-in (NextAuth). Accepts `callbackUrl`, sanitized via `safeCallbackPath`. Dark card UI. |
| `/docs/api` | `docs/api/page.tsx` (126 lines) | Static API reference page listing public endpoints (transcribe, extract-events, chat, agents, video metadata). |
| `/privacy` | `privacy/page.tsx` | Static privacy policy (last updated May 25, 2026). |
| `/terms` | `terms/page.tsx` | Static terms of service. |
| `/dashboard` | `dashboard/page.tsx` | Legacy redirect → `/studio` (preserves query params). |
| `/dashboard/agents` | `dashboard/agents/page.tsx` | Legacy redirect → `/studio`. |
| `/app` | `app/page.tsx` | Legacy redirect → `/studio`. |
| `/features` | `features/page.tsx` | Redirect → `/`. |
| `/playground` | `playground/page.tsx` | Redirect → `/`. |
| `/prototype` | `prototype/page.tsx` (+ `prototype/layout.tsx`) | Legacy interactive-simulation route; redirects → `/studio` ("could be mistaken for a verified workflow"). |

Supporting app files:
- `layout.tsx` — root layout: fonts (Inter, JetBrains Mono, Space Grotesk via `next/font`), metadata/SEO, `StructuredData` (JSON-LD), `AuthSessionProvider` (next-auth), Vercel Analytics + Speed Insights (prod only), global mesh/noise background divs.
- `globals.css` — Tailwind v4 (`@import "tailwindcss"`), CSS custom props (`--color-void/ink/primary/...`), enterprise tokens import. **Note:** `body` is dark by default (`bg-surface-950`); the light card system is scoped under `.uvai-cards`.
- `global-error.tsx` — app-level error boundary.
- `opengraph-image.tsx` — OG image generator.
- `sitemap.ts` — sitemap for `/`, `/studio`, `/pricing`.
- `ContactForm.tsx` — contact form component (used on landing via `landing/ContactSection`).
- `layout.test.tsx` — layout test.

### Entry / boot chain
`src/app/layout.tsx` → `AuthSessionProvider` (next-auth `SessionProvider`) → page. `src/proxy.ts` (Next.js 16 proxy, formerly middleware) runs first: rate limiting (60 req/min general, 12/min AI) + login gating (enforces session on non-public `/api/*` when `NEXTAUTH_SECRET` is set; fails closed 503 in prod if misconfigured; `x-eventrelay-internal` header bypasses for server-to-server). Path policy lives in `src/lib/auth-paths.ts`. Feature flags via `@flags-sdk/vercel` in `src/flags.ts` (`custom-badge`, `agentWorkflowUi`).

---

## 2. API Routes (`src/app/api/`)

### Video Pack pipeline (core product)
| Method | Path | Purpose |
|---|---|---|
| POST, GET | `/api/video/pack` | **Core.** Hash-identified Video Pack emit/retrieve. Delegates to `lib/video-pack.ts`. Pack store = Upstash Redis REST only. |
| GET | `/api/video/pack/frames/:videoId/:t` | Keyframe image for a pack at timestamp `t`. |
| POST, GET | `/api/video/assemble` | Assemble app-builder output from a pack (`lib/assemble-app-builder-route`). |
| POST, GET | `/api/video/sandbox` | Sandboxed app-builder execution (`lib/app-builder-sandbox-route`). |
| POST | `/api/video/generate` | Video generation w/ Upstash durable rate limiting. |
| GET | `/api/video/search` | Search video packs. |
| POST, GET | `/api/video` | **Deprecated** legacy register/list endpoint. No in-repo callers; kept for external consumers. |

### Workflow (durable runs via Workflow DevKit)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workflows/video-to-actions` | Start durable video→transcript→actions run; returns `runId`. |
| GET | `/api/workflows/video-to-actions/:runId` | Poll run status + result. |
| POST | `/api/workflows/studio-deploy` | Start Studio deploy run (G.A.T.E.-gated). |
| GET | `/api/workflows/studio-deploy/:runId` | Poll deploy run status. |

### Studio chat (agentic, pack-grounded)
All delegate to handlers in `src/lib/studio/routes.ts`. `runtime = 'nodejs'`, `force-dynamic`.
| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/api/studio/chats` | List chats / create chat. |
| GET, POST, DELETE* | `/api/studio/chats/:chatId` | Chat CRUD (`*`verify; route.ts exists). |
| GET, POST | `/api/studio/chats/:chatId/messages` | List / send messages. |
| POST | `/api/studio/chats/:chatId/resolve` | Resolve a pending message. |
| POST | `/api/studio/chats/:chatId/resume` | Resume a stopped chat. |
| POST | `/api/studio/chats/:chatId/stop` | Stop generation. |
| GET, POST | `/api/studio/chats/:chatId/files` | Chat file attachments. |
| GET | `/api/studio/chats/:chatId/files/download` | Download attachment. |

### Chat (legacy/simple)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/chat` | Conversational query over an analyzed video. Pack-grounded (`chat-pack-grounding`), Pro entitlement + free daily quota enforcement, routes to AI Gateway/Grok. |

### Transcription & extraction
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/transcribe` | Multi-strategy transcript: YouTube captions (backend) → Gemini fallback → OpenAI w/ web search → Whisper STT. |
| POST | `/api/extract-events` | Extract typed events from a transcript. |

### G.A.T.E. (Origin hardgate — non-bypassable)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/gate/transitions` | Evaluate a state transition → exactly one of `PASS \| HOLD \| REJECT \| ESCALATE`. Owner + origin checks. |
| POST | `/api/gate/probe-live` | Probe a deployment's live URL; feeds gate evidence. |

### Billing (Stripe — locked prices)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/billing/checkout` | Create Pro checkout session. Turnstile bot-check required. Email → Stripe `customer_email` only. |
| POST | `/api/billing/webhook` | Stripe webhook (subscription events). |
| GET | `/api/billing/status` | Current entitlement status. |
| POST | `/api/billing/activate` | Activate Pro after successful checkout (entitlement recovery). |
| POST | `/api/billing/renew` | Renew/refresh Pro entitlement. |

### Export
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspace/export` | Zip workspace files for download. **Pro-gated** (`requireProFeatureAccess`); anonymous users get 402 → Stripe checkout. Path-traversal-safe filename normalization. |

### Agents (legacy FastAPI backend proxy)
| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/api/agents/actions` | Advertises executable tools for the action agent. |
| GET, POST | `/api/agents/dispatch` | Availability probe for the external agent backend. |
| GET | `/api/agents/status` | Poll agent execution status (proxies FastAPI). |

### Misc
| Method | Path | Purpose |
|---|---|---|
| GET, HEAD | `/api` | Health check / service descriptor. |
| GET | `/api/docs` | API docs data. |
| POST, PUT | `/api/search` | Cross-video full-text/semantic search (Upstash Search). |
| GET | `/api/jobs/:jobId` | Proxy backend async video job status. |
| GET, POST | `/api/realtime/session` | OpenAI realtime session bootstrap (upstream errors sanitized server-side). |
| GET | `/api/training/status` | Fine-tuning dataset status (examples collected, threshold progress). |
| POST | `/api/training/trigger` | Trigger Gemini fine-tuning on Vertex AI (`check` mode default). |
| GET, PUT | `/api/v1/preferences` | User preferences. |
| GET | `/api/v1/refinery/dataset` | Refinery dataset access. |
| POST, GET, DELETE* | `/api/v1/video/assemble`, `/api/v1/video/pack`, `/api/v1/video/sandbox` | Compatibility aliases for canonical `/api/video/*` routes (AUDIT-005). |
| — | `/api/auth/[...nextauth]` | NextAuth handler (Google OAuth). |

---

## 3. Components (`src/components/`)

### Product: Studio (the workbench)
- `OneLoopStudio.tsx` (1446 lines, 34 testids) — **main Studio component.** URL paste → run → three panes (video / chat / output with Events, Lingo, Tools, Intent, Signals, Spec, Transcript tabs) → toolbar (Run/Cancel, stored packs, Export, Build live). G.A.T.E. receipt rendering for deploy. Heavy lib coupling (see §4).
- `studio/StudioIdeShell.tsx` — IDE shell layout (panes, splitters).
- `studio/StudioIdeChat.tsx` — chat pane (pack-grounded, hits `/api/chat`).
- `studio/StudioIdeOutput.tsx` — output pane with the 7 extraction tabs.
- `GroundedSpecReview.tsx` — grounded spec review UI (Spec tab content).
- `StudioAuthNavLink.tsx` — nav link that adapts to auth state.

### Landing / marketing
- `Nav.tsx` — global nav (`tone: 'dark' | 'light'`, links Home/Studio/Pricing, mobile menu).
- `Footer.tsx` — global footer.
- `home/HomePasteForm.tsx` — landing URL paste → validates YouTube URL → `router.push('/studio?video=')`.
- `home/HomeProCheckout.tsx` — "Get Pro" checkout island (Turnstile + Stripe).
- `landing/` — **orphaned, zero imports** (deletion candidate): `HeroSection`, `BentoFeatures`, `WorkflowSection`, `TemplatesSection`, `DeveloperSection`, `ContactSection`, `LandingNav`, `LandingFooter`.

### Billing
- `billing/ProCheckoutButton.tsx`, `billing/ProRenewPanel.tsx`, `billing/CheckoutSuccessActivator.tsx`, `billing/BillingStatusBanner.tsx`.

### Dashboard (legacy skins — mostly redirect to Studio now)
- `dashboard/DashboardCanvasView.tsx`, `dashboard/DashboardSplitView.tsx`, `dashboard/VideoCanvasStage.tsx`, `dashboard/panels.tsx`.
- Top-level: `AgentDashboard.tsx`, `AgentFlowVisualizer.tsx`, `OrchestratorRail.tsx`, `AnalysisPanel.tsx`, `EventList.tsx`, `ResultsViewer.tsx`, `TranscriptViewer.tsx`, `InteractiveTranscript.tsx`, `PipelineProgress.tsx`, `TracePanel.tsx`, `ConsensusIndicator.tsx`, `PreferencesPanel.tsx`, `FeedbackWidget.tsx`, `video-generator.tsx`, `StructuredData.tsx` (JSON-LD), `AuthSessionProvider.tsx`.

### UI primitives (`ui/`)
Radix-based + custom: `Button`, `Card`, `Input`, `Badge`, `alert`, `empty`, `field`, `label`, `separator`, `tabs`, `textarea`, `resizable` (react-resizable-panels wrapper), `SuggestedPrompts`, `index.ts` barrel. Styled via `components.json` (shadcn convention).

### Tests
`components/__tests__/`: `OneLoopStudio.gate.test.tsx`, `OneLoopStudio.build-live.test.tsx`, `OneLoopStudio.job-strip.test.tsx`, `OneLoopStudio.three-panel.test.tsx`, `GroundedSpecReview.test.tsx`, `StudioAuthNavLink.test.tsx`; `home/`: `HomePasteForm.test.tsx`, `HomeProCheckout.test.tsx`; `ui/resizable.test.tsx`.

---

## 4. Library (`src/lib/`) — key files

96 test files under `lib/__tests__` + `lib/studio/__tests__`. Major modules:

**Studio pipeline**
- `studio-workflow.ts` (550) — client helpers: `startVideoToActions`/`pollVideoToActions`, `startStudioDeploy`/`pollStudioDeploy`, live-URL probe.
- `studio-pipeline-status.ts` (666) — status labels, run-quality, deploy hints/receipts, export filenames, transcript stage text — most UI copy for Studio states.
- `studio-workbench-panes.ts` — pane ids, tab definitions, outline↔pane mapping, dedupe helpers.
- `studio-handoff.ts` — URL param handoff (`?video=`) → Studio auto-start; pack auto-select.
- `studio-shell-storage.ts` — Studio shell persistence.
- `use-youtube-player.ts` — YouTube IFrame player hook.
- `chat-pack-grounding.ts` — binds chat to a pack's evidence.
- `pack-build-live-client.ts` / `pack-build-live.ts` — Build-live flow.
- `official-templates.ts` — template picking, deploy hold reasons, stack checks.
- `linked-sop.ts` — SOP steps linked against events; stack check compilation.

**Video Pack (core domain)**
- `video-pack.ts` — pack route handlers (identity pack emit/get).
- `emit-video-pack.ts` — pack emission, hashing, citations.
- `video-pack-types.ts` — pack schema types.
- `video-pack-store.ts` — Upstash REST persistence.
- `video-pack-extractor.ts` + `video-pack-extract-{jev,merge,reason,segments}.ts` — extraction pipeline stages.
- `video-pack-shard-planner.ts`, `video-pack-consolidator.ts`, `video-pack-clip-probe.ts`, `keyframe-frame-capture.ts`, `keyframe-image-path.ts`.
- `youtube-captions.ts`, `youtube-metadata.ts`, `transcription-service.ts`, `gemini-video-analyzer.ts`, `gemini-client.ts`, `gemini-models.ts`, `gemini-embedding.ts`.

**G.A.T.E. / Zero-Sim (locked, non-bypassable)**
- `gate-transition.ts` — the contract: `evaluateStudioDeployTransition`, receipt views, `PASS|HOLD|REJECT|ESCALATE`.
- `origin-gate.ts` / `origin-gate-store.ts` — origin gate decision + Redis store.
- `analysis-evidence.ts` — evidence assessment (`real|unverified|unreal`).

**Chat/AI**
- `studio/` — agentic chat subsystem: `routes.ts` (API handlers), `chat-store.ts`, `provider.ts`, `generation.ts`, `generation-stream`, `controls.ts`, `interactions.ts`, `pack-context.ts`, `security.ts`, `errors.ts`.
- `ai-gateway.ts`, `vercel-ai-gateway.ts`, `ai-gateway-rag.ts` — model routing (Gemini 3.8 Flash via Vercel AI Gateway per AGENTS.md).
- `action-agent.ts`, `action-lifecycle.ts`, `action-surface.ts`, `action-tools.ts`, `agent-pipeline.ts`, `agent-types.ts`.

**Billing**
- `billing/` — `stripe-checkout.ts` (session creation), `checkout-config.ts` (locked prices/names), `entitlement-store.ts` + `entitlement-file-store.ts`, `pro-feature-gate.ts` (`requireProFeatureAccess`), `chat-quota.ts`, `paid-tier-model.ts`, `turnstile.ts` (Cloudflare bot check), `billing-context.ts`, `subscription-events.ts`, `kaizen-trace.ts`, plus Jev/Grok lead-scoring clients.

**Auth**
- `auth.ts` — NextAuth options (Google provider; `server-only`).
- `auth-jwt.ts` — JWT session verification for proxy.
- `auth-paths.ts` — canonical paths, public-route policy, `safeCallbackPath`.

**State**
- `src/store/dashboard-store.ts` (632) — **Zustand + persist.** Videos, pack records, `processVideo` (durable run → complete only on verified evidence + quality gate), chat, selection.
- `src/store/action-agent-store.ts`, `src/store/dashboard-types.ts`.

**Infra/misc**
- `ssrf-guard.ts` — URL fetch allowlisting.
- `zip-store.ts` — export zip assembly.
- `timestamp.ts` — `formatSeconds`, `parseTimestampToSeconds`, `extractYouTubeId`.
- `site.ts`, `constants.ts` (contact email etc.), `utils.ts` (`clsx`+`tailwind-merge` `cn`).
- `search-indexer.ts`, `upstash-search.ts`, `embedding-store.ts`.
- `video-url-request.ts`, `hosted-spec-paths.ts`, `compiled-spec-host.ts`, `live-deployment-probe.ts`.
- `world-v
...[truncated 3119 chars]