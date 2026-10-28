# UVAI Studio — Functional Inventory

Source-of-truth spec for a from-scratch rebuild of the Studio page.
Derived from a line-by-line read (2026-10-07) of:

- `apps/web/src/components/OneLoopStudio.tsx` (1446 lines) — main Studio component, owns all toolbar actions and state
- `apps/web/src/components/studio/StudioIdeShell.tsx` (178 lines) — three-pane layout shell
- `apps/web/src/components/studio/StudioIdeChat.tsx` (194 lines) — center chat pane
- `apps/web/src/components/studio/StudioIdeOutput.tsx` (307 lines) — right output pane

**Read-only inventory — no source files were modified to produce this.**

---

## 1. Page overview

Route: `/studio` (canonical path constant `CANONICAL_STUDIO_PATH`).
Layout, top to bottom:

1. **Global nav** (`Nav`, light tone) with `StudioAuthNavLink` in the right slot (sign-in/account link).
2. **IDE toolbar** (full width, inside `StudioIdeShell`): URL form + stored-pack selector + action buttons + preflight hint + status line + optional G.A.T.E. receipt card.
3. **Three panes**, side by side, resizable:
   - **Left — Video**: YouTube player embed + Video Pack identity card (hash + source URL).
   - **Center — Chat**: pack-grounded chat with composer.
   - **Right — Output**: seven-tab action-extraction output (Events, Lingo, Tools, Intent, Signals, Spec, Transcript).
4. **Fixed toast** (bottom center): export success/error notifications, auto-dismiss after 4s.
5. **Build-live result banner** (bottom strip): success card with "Ready" chip, job title, YouTube video id, reason code, artifact link, and "Unlock Workflow Pro" CTA.
6. **Build-live failure banner** (bottom strip): red alert with title, message, reason code, and recovery action buttons.

Visual language: light card system (white cards on soft blue-gray `#f2f5f9`), per `apps/web/DESIGN_LANGUAGE.md`. Class hooks: `uvai-card`, `uvai-btn`, `uvai-input`, `uvai-section-label`, `uvai-empty`, `uvai-chat-user`, `uvai-chat-assistant`, `uvai-doc-row`, `uvai-metric`, `uvai-pane-header`, `uvai-toolbar`, `uvai-splitter`. Stylesheet: `@/styles/studio-cards.css` (imported by the shell).

### Shell behavior (`StudioIdeShell`)

- Left (video) pane default width 380px, right (output) pane 420px; center chat is fluid.
- Both side panes resizable via drag splitters; min 240px, max 560px; widths set as CSS vars `--ide-left-w` / `--ide-right-w` on the shell root.
- Widths persist **per session in memory only** (React state; lost on reload).
- Left pane collapses with a `‹` button in its header; a "Show video" button appears in the chat pane header to restore it.
- Right pane collapses with a `›` button in its header; a narrow "Output" rail button restores it.
- Chat pane has no collapse.

---

## 2. User-facing features, step by step

### The core loop

1. **Paste a YouTube URL** into the toolbar input (placeholder pre-filled with the sample fixture `https://www.youtube.com/watch?v=auJzb1D-fag`).
2. Optionally press **Sample** to fill the fixture URL instantly (disabled while busy).
3. Press **Run** (or hit Enter — it's a form submit). While a run is in flight, Run becomes **Cancel**.
4. Status line shows live progress: `Working · Ns — <stage>. <ETA>` where stage/ETA are computed from elapsed seconds, store progress %, and pack presence.
5. The YouTube player loads in the left pane; a loading/error overlay covers it until the IFrame API reports ready.
6. When analysis completes, the status line shows the outcome message and the right output pane populates with the seven tabs.
7. **Chat** with the pack in the center pane (input enabled once a video/pack exists).
8. **Stored packs** dropdown appears after ≥1 pack exists; switching reopens a pack instantly without re-running analysis.
9. **Export** downloads the workspace ZIP (paywalled — see §10).
10. **Build live** verifies the pack and opens/serves the hosted app (see §11).
11. **Check preflight** runs the gated deploy check (see §12) — NOTE: marked for deletion/redevelopment per product direction; see §17.

### Video player

- Powered by `useYouTubePlayer(videoId)` (IFrame API). Destructured as `containerRef`, `ready`, `failed`, `seekTo`.
- `videoId` is derived from the URL input first, then the selected video's URL.
- `playerEpoch` state remounts the player container (`key={videoId}-{epoch}`) on retry.
- Overlay states (computed by `studioPlayerPhase` / `studioPlayerOverlay`):
  - No video id → placeholder card: "Paste a link above. The video plays here while we pull the transcript."
  - Loading → light overlay with status text.
  - Error → overlay with **Retry player** (bumps `playerEpoch`) and **Open on YouTube** (external link).
- The grounded-spec review (`GroundedSpecReview`) can seek the player: `onSeek` is wired only when the selected pack's `video_id` matches the currently loaded `videoId`.

### Pack identity card (left pane, below player)

Shown when `selected.videoPack` exists:
- Label "Video pack"
- Truncated source hash: first 12 chars + `…` (amber, mono)
- Truncated source URL (gray, mono)

### Chat pane

- Header: "Chat" section label (+ "Show video" restore button when left pane collapsed).
- Empty state: "Ask about this pack" / "Grounded in the pack — events, lingo, tools, intent. No invented answers." when a video exists; "Run a video to start chatting" / "Paste a YouTube URL above and hit Run." when none.
- Messages render as user (right-styled) and assistant bubbles; auto-scroll to bottom on new messages.
- "Thinking…" placeholder while a request is in flight.
- Composer: text input + Send button. Input disabled until a video exists and while not sending. Send disabled when draft is empty.
- Quota banner (amber): "Daily free limit reached. Upgrade to Pro for unlimited chat." with `/pricing` link, shown after a 402 with `upgradeRequired`.
- Error banner (red): inline API error text.
- **Conversation resets** whenever `videoId` or `packId` changes (pack switch, new run). Chat history does NOT survive the Stripe return trip; pack results do.

### Output pane — seven tabs

Tab bar (role=tablist): **Events, Lingo, Tools, Intent, Signals, Spec, Transcript**. Active tab highlighted amber. Tabs shown regardless of content; each tab has its own empty state.

| Tab | Source | Renders |
|---|---|---|
| Events | `video.events[]` (`ExtractedEvent`) | Card per event: type chip (amber pill + dot), timestamp (mono), title, description |
| Lingo | `video.insights.topics[]` | One card: "Domain terms" label + term pills |
| Tools | `pack.stack.tools[]` (deduped names) + `video.insights.linkedSop.steps[]` | "Named tools" card (wrench icon + mono names, 2-col grid) + "SOP steps" card (numbered doc rows) |
| Intent | `pack.action_items[]` | Card per action item with left amber border + arrow icon, title, description |
| Signals | `pack.visual_context` + `pack.keyframes[]` | "Visual summary" card + 2-col keyframe grid (thumbnail or timestamp placeholder + caption) |
| Spec | `specReview` prop (`GroundedSpecReview`) | The grounded spec review component, or "No grounded spec on this pack." |
| Transcript | `video.transcript` | Full transcript in a card (pre-wrap); failure message if the run failed; "Nothing yet." otherwise |

Pane-level empty state (any tab except Transcript, when no pack/events/insights): "Run a video and the extracted actions land here — Events, lingo, tools, intent, signals — as structured cards."

---

## 3. Toolbar buttons — complete catalog

The toolbar is a flex-wrap container inside the IDE shell (`data-testid="studio-ide-toolbar"`). Order left to right:

### URL form (`data-testid="studio-ide-url-form"`)

| Control | testid | Trigger | Behavior |
|---|---|---|---|
| URL input (`#youtube-url`) | — | typing | Controlled `url` state; mono font; placeholder = fixture URL |
| Sample | — | click | Sets input to `https://www.youtube.com/watch?v=auJzb1D-fag`; disabled while busy |
| Run | `studio-ide-run` | form submit (click or Enter) | `runAnalysis(url)`; disabled implicitly by swap |
| Cancel | `studio-ide-cancel` | click | Aborts `runAbortRef` controller; status → "Cancelling analysis…" then "Analysis cancelled." |

Invalid URL → status message "Need a valid YouTube URL." (no run starts).

### Stored packs (`data-testid="studio-ide-packs"`) — only rendered when ≥1 video has a `videoPack`

| Control | testid | Trigger | Behavior |
|---|---|---|---|
| Combobox "Stored packs" | `#stored-pack` | change | `selectVideo(id or null)` — instant reopen, no re-analysis |
| Delete pack `✕` | `studio-ide-delete-pack` | click | `removeVideo(selected.id)` — removes the pack row; only shown when the selection has a pack; disabled while busy |

### Pack actions toolbar (`role="toolbar"`, `aria-label="Pack actions"`)

| Button | testid | Enabled when | Trigger | Behavior |
|---|---|---|---|---|
| Export | `studio-ide-export` | `hasPayload` (see §10) | click | `exportPkg()` — builds ship package, downloads ZIP or redirects to Pro checkout |
| Build live | `studio-build-live-button` | `canAttemptBuildLive` (valid YouTube id in input or selection) and not `buildBusy` | click | `buildLive()` — verifies pack, shows success/failure banner |
| Check preflight | `studio-deploy-button` | `hasPayload`, not `deployBusy`, and no `holdReason` | click | `deploy()` — gated deploy preflight, shows G.A.T.E. receipt card; **401/403 → redirect to `/login?callbackUrl=/studio`** |

Below the buttons:
- **Preflight hint** (`#studio-preflight-hint`): `studioDeployEnabledHint(scoped)` — describes what preflight will do or why it's unavailable.
- **Status line** (`data-testid="studio-ide-status"`, `role="status"`): live run status text (see §2).
- **G.A.T.E. receipt card** (`data-testid="studio-gate-receipt"`, `role="status"`): shown after a deploy attempt — decision chip (PASS/HOLD/REJECT/ESCALATE with color coding), reason, receipt id + hash + version, transition id + retention, and the verified live URL link when PASS. Version note: v2 receipts = "Server decision. Later stages require separate Loop approval."; anything else = "Local diagnostic only — not an authorization receipt."

---

## 4. State management

### Zustand store (`@/store/dashboard-store`) — persisted

`useDashboardStore` holds the **video rows** (`videos: Video[]`, `selectedVideoId`). Selectors used: `processVideo`, `selectVideo`, `updateVideo`, `removeVideo`, `selectedVideoId`, `videos`. Persisted via zustand `persist` middleware to **localStorage** (custom storage wrapper; `dashboardPersistenceSucceeded()` reports whether persistence is available).

`Video` row fields (from `@/store/dashboard-types`):
- Identity: `id`, `title`, `url`, `status` (`processing`|`complete`|`failed`), `progress`, `pipelineMode` (backend SSE | Gemini | legacy /api/video | offline handoff), `thumbnail`, `duration`, `processedAt`
- Content: `transcript`, `events[]` (`ExtractedEvent`: id, type, title, description, timestamp, confidence), `agents[]`, `pipelineResult`, `insights` (topics, summary, actions, linkedSop, project_scaffold)
- Job: `jobId`, `statusUrl`, `runId`
- **Pack**: `videoPack?: VideoPackCitation` — the hashed Video Pack identity (`videoId`, `sourceUrl`, `sourceHash`, `packId`, `pack` = full visual pack object)
- Spec review: `specReviewAcknowledgment`
- Provenance/quality: `provenance`, `quality`
- Failure: `failure: { stage, message, retryable, failedAt }`

### Local React state in `OneLoopStudio`

| State | Purpose |
|---|---|
| `url` | URL input value |
| `busy` | Analysis run in flight |
| `elapsed` | Seconds counter while `transcriptWorking` (250ms interval) |
| `message` | Status line text |
| `actBusy` | Act (video-to-actions) in flight |
| `deployBusy` | Deploy preflight in flight |
| `runAbortRef` | `AbortController` for canceling analysis |
| `workflowActions` | `VideoToActionsResult` after Act completes |
| `actRunId` | Act run id |
| `usedSameRun` | Whether Act reused this run's transcript/events |
| `deployRunId` | Deploy run id |
| `deployReceiptUrl` / `deployReceiptVideoId` | Verified deploy live URL + owning video |
| `buildBusy` | Build-live in flight |
| `packLiveReceiptUrl/VideoId/YoutubeId/ReasonCode` | Build-live success receipt fields |
| `gateReceipt` | `StudioGateReceiptView` shown in the receipt card |
| `completedChecks` / `approvedSpecIds` | Deploy hold / spec approval — **wired to nothing; always reset to `[]`** (see §17) |
| `openingPrs` | GitHub PR flow busy flag — **no UI trigger** (see §17) |
| `playerEpoch` | Player remount counter for retry |
| `exportToast` | `{tone, text}` toast; auto-clears after 4000ms |
| `buildLiveFailure` | `PackBuildLiveFailureDetails` for the failure banner |
| `autoStartedKey` / `autoSelectedPackRef` | One-shot guards for URL auto-start and pack auto-select |
| `requestedPane` | Pane deep-link override (from outline section clicks) |
| `transcriptExpanded` | Transcript expand toggle — **reset but never set true in current render** (see §17) |

### Selection-scoped derivations (recomputed per selected video)

- `selected` — the active `Video` row.
- `scopedDeployReceipt`, `scopedPackLiveUrl`, `scopedPackBuildLiveSuccess` — receipt scoping helpers: a receipt only shows when its `receiptVideoId` matches `selectedVideoId` (prevents stale receipts bleeding across packs).
- `packFormation` — `studioPackFormation(selected.videoPack)`: architecture, artifacts, tools, checks.
- `linkedSop` — compiled SOP from transcript + events + insight actions + pack tools, via `compileLinkedSop` + `applyPackStackChecks`; falls back to stored `insights.linkedSop`.
- On `selectedVideoId` change, all run-scoped state resets (receipts, gate receipt, failures, pane, transcript expansion).

---

## 5. API calls

| Caller | Endpoint | Method | When |
|---|---|---|---|
| `tryExtractEvents` | `/api/extract-events` | POST `{transcript, videoTitle, videoUrl}` | Inside `act()` when transcript ≥ `MIN_ACT_TRANSCRIPT_CHARS` and no events yet. **Session-gated enrich: 401/403 → returns null, Act still proceeds.** 45s timeout. |
| `StudioIdeChat.send` | `/api/chat` | POST `{query, history (last 10), video_id?, pack_id?}` | Every chat send. **402 + `upgradeRequired` → quota banner (free tier = 5 msgs/day).** Other errors → inline error banner + error assistant message. |
| `downloadScaffoldPackage` | `/api/workspace/export` | POST (ship package payload) | `exportPkg()`. Retries while `!ok && status >= 500`. **402 + `checkoutUrl` → toast "Workspace ZIP exports require Pro. Redirecting to checkout…" then `window.location.href = checkoutUrl` (Stripe).** |
| `startStudioDeploy` | `/api/workflows/studio-deploy` | POST `{url}` | `deploy()` (Check preflight). |
| `pollStudioDeploy` | status URL from start response | GET (poll) | `deploy()` after start. |
| `probeStudioDeployLiveUrl` | `/api/gate/probe-live` | POST | `deploy()` when a `live_url` candidate exists — HTTP probe fed into the G.A.T.E. evaluation. |
| `startVideoToActions` | `/api/workflows/video-to-actions` | POST (act input payload) | `act()` — **no UI button in current render** (see §17). |
| `pollVideoToActions` | `/api/workflows/video-to-actions/<runId>` | GET (24 attempts × 2s) | `act()` after start. |
| `verifyPackBuildLive` | (client lib `pack-build-live-client`) | — | `buildLive()` — verifies hosted pack by `videoId` + `sourceHash` against `window.location.origin`. |
| `processVideo` (store) | backend SSE / Gemini / legacy `/api/video` | — | `runAnalysis()` — pipeline mode recorded on the row. |

---

## 6. Data flows

### URL paste → analysis → pack → output

1. User pastes URL → `runAnalysis(raw)` → `resolveStudioHandoff(raw)` validates/extracts `{watchUrl, videoId}`. Invalid → "Need a valid YouTube URL."
2. Any in-flight run is aborted first (`runAbortRef.current?.abort()`).
3. `setUrl(watchUrl)`, new `AbortController`, `busy=true`, Act state cleared, status "Fetching transcript…".
4. A 250ms interval polls the store for a row matching the URL and auto-selects it as soon as it appears.
5. `processVideo(watchUrl, {signal})` runs the pipeline (transcript acquisition → event extraction → pack emission → persistence). Aborted → "Analysis cancelled."
6. On success: `selectVideo(id)`; readiness = transcript ≥ 40 chars OR ≥1 event. Failed → `video.failure.message`. Status line gets `studioPasteOutcomeMessage({hasUsableTranscript, packCitation})`.
7. Derived memos (`packFormation`, `linkedSop`, shell chapters/SOP) recompute; output tabs populate; chat enables (`videoId`/`packId` flow to `StudioIdeChat`).

### Pack → output tabs

`selected.videoPack.pack` (the visual pack: chapters, action_items, stack.tools, visual_context, keyframes, requirements, transcript) + `selected.events` + `selected.insights` feed `StudioIdeOutput`. See §2 table.

### Chat

`StudioIdeChat` receives `videoId` + `packId`; sends `{query, history, video_id, pack_id}` to `/api/chat`; assistant answers are pack-grounded server-side. History resets on pack change.

### Act (video-to-actions) — currently triggerless

`act()` builds input via `buildSameRunActInput({url, videoTitle, transcript, events + SOP steps as events})`, optionally enriches events via `/api/extract-events`, starts + polls the workflow, stores `workflowActions`. Intended to surface an "Actions" workbench pane (`hasActionsPane = showAgentWorkflowUi && (actRunId || workflowActions)`), but **no button calls `act()` in the current render** (see §17).

### Export

`exportPkg()`:
1. Filename from `studioExportFilename(safeProjectName(title))`.
2. Actions assembled via `actionsFromStudioRun({insightActions, events, workflowActions})`.
3. Emptiness guard: no actions, scaffold, SOP steps, architecture, artifacts, or tools → error toast "empty".
4. `buildStudioShipPackage({projectName, actions, projectScaffold, linkedSop, videoPack, transcript, sopSteps})`.
5. `downloadScaffoldPackage(pkg)` → POST `/api/workspace/export`.
   - 402 + checkoutUrl → error toast + redirect to Stripe checkout (Pro $39/mo).
   - Other failure → error toast.
   - Success → success toast; if an official template matched, message names the cloned template + SOP + DEPLOY.md.

### Build live

`buildLive()`:
1. Resolve pack video id from `selected.videoPack.videoId` or the URL; missing → failure banner "stored pack missing" + recovery actions.
2. No stored `videoPack` → failure banner `HOSTED_PACK_NOT_FOUND`.
3. `verifyPackBuildLive({videoId, sourceHash, origin})`:
   - `ok` → success receipt state → **success banner**: "Ready" chip, job title + subtitle, YouTube video id, reason code, "Open `<artifactPath>`" link, "Unlock Workflow Pro" (`/#get-pro`) CTA.
   - not ok → `packBuildLiveFailureDetails({reasonCode, message, videoId, origin})` → **failure banner** with recovery actions:
     - `open_hosted` → opens hosted URL in new tab
     - `rerun_analysis` → re-runs `runAnalysis` on the current URL
     - `scroll_pack` → smooth-scrolls to `[data-testid="video-pack"]`
4. Receipts are selection-scoped; switching packs hides them.

### Deploy / Check preflight (gated)

`deploy()`:
1. Requires valid YouTube id; `holdReason` (from `deployHoldReason(linkedSop, completedChecks, 'anonymous')`) blocks with its message.
2. `startStudioDeploy({url})` → 401/403 → **redirect to `/login?callbackUrl=/studio`** (the anonymous sign-in wall).
3. Server-provided `gate` → receipt card shows it immediately.
4. Else poll the run; probe any `live_url` candidate; evaluate `evaluateStudioDeployTransition({...})` → `StudioGateReceiptView`.
5. Receipt card shows decision chip + reason + receipt id/hash/version + transition + retention; verified live URL (only when PASS) is linkified.
6. All state updates are guarded against selection change mid-flight (`attemptVideoId` check).

---

## 7. G.A.T.E. integration points

- Gated transition: Studio `studio.deploy` (`proposed` → `live`). Contract: `apps/web/src/lib/gate-transition.ts`; spec: `docs/gate-transition-contract.md`.
- Decisions: exactly `PASS | HOLD | REJECT | ESCALATE` (chip colors: emerald / amber / red / violet).
- `deploy()` evaluates via `evaluateStudioDeployTransition({transitionId, runId, jobId, liveUrl, runStatus, kind, backendReason, deploymentHttpProbe, authority: {actor: 'anonymous'}})`.
- Receipt card (`data-testid="studio-gate-receipt"`) surfaces: `studio-gate-decision`, `studio-gate-reason`, `studio-gate-receipt-id`, `studio-gate-receipt-hash`, version, transition id, retention flag, and `studio-gate-live-url` (PASS only).
- Rule: **no live success claim unless G.A.T.E. PASSes a verified `https://` hostname URL** (`studioVerifiedLiveUrl`).
- `holdReason` (pre-deploy hold from SOP/completed checks) disables the Check preflight button — currently always evaluates with empty `completedChecks`.

---

## 8. Chat system (detail)

Component: `StudioIdeChat` — fully self-contained, props: `videoId`, `packId`, `disabled`.
- Local state: `messages[]` (`{id, role, content}`), `draft`, `sending`, `quotaHit`, `error`.
- Sends last 10 messages as history. `video_id`/`pack_id` included when present for server-side grounding.
- 402 + `upgradeRequired` → quota banner with `/pricing` upgrade link; assistant message carries the quota text.
- Disabled until a video exists (`canChat = videoId && !disabled`) and while parent `busy`.
- Conversation resets on `videoId`/`packId` change — history does not persist across packs or page returns.

---

## 9. Pack management

- **Store**: rows in `useDashboardStore.videos`; pack identity on `video.videoPack` (`videoId`, `sourceUrl`, `sourceHash`, `packId`, full `pack`).
- **Selector**: "Stored packs" combobox lists only videos with a `videoPack`; `selectVideo` switches instantly, no re-analysis.
- **Auto-select**: once after rehydration, if no selection and no `?video=` handoff, the newest row with pack identity is auto-selected (display-only; never starts extraction).
- **Delete**: `✕` button calls `removeVideo(selected.id)`; disabled while busy.
- **Persistence**: localStorage via zustand persist; pack results survive reload and the Stripe return trip.

---

## 10. Export flow + paywall

- Button: **Export** (`studio-ide-export`), enabled by `hasPayload` = any of: transcript, events, architecture, artifacts, tools, linked SOP steps, project scaffold.
- Empty payload → error toast, no network call.
- POST `/api/workspace/export` → on 402 with `checkoutUrl`, error toast "Workspace ZIP exports require Pro. Redirecting to checkout…" then full-page redirect to Stripe Checkout for **Workflow Pro ($39/mo)**. No payment/account is created by the Studio.
- Success → browser download of the ZIP (scaffold package: actions, project scaffold, SOP, video pack, transcript) + success toast naming the template when an official template matched ("Exported `<clone>` plus SOP and DEPLOY.md. `<filename>`").

---

## 11. Build live flow

- Button: **Build live** (`studio-build-live-button`), enabled when a valid YouTube id is present in the input or selection (works **anonymously**).
- Verifies the stored pack (`videoId` + `sourceHash`) against the origin; success → bottom success banner with artifact link + Pro upsell CTA; failure → red banner with recovery actions (open hosted / re-run analysis / scroll to pack).
- This is the anonymous deploy path; it does not go through G.A.T.E. or require sign-in.

---

## 12. Deploy / Check preflight flow (flagged for deletion)

- Button: **Check preflight** (`studio-deploy-button`) → `deploy()`.
- Currently the only path that hits the G.A.T.E. `studio.deploy` transition.
- Anonymous users get **redirected to Google sign-in** (`/login?callbackUrl=/studio`) — inconsistent with Build live, which deploys anonymously. This is the "preflight sign-in" issue.
- Per product direction (2026-10-07): if it doesn't make sense, delete it; the deploy/preflight area needs full redevelopment. The rebuild should treat this button/flow as **removed pending redesign**, not as a feature to preserve.

---

## 13. URL params, handoff logic, auto-start

- Accepted params: `?video=<youtube-url-or-id>`, `?url=…`, `?v=<id>` (+ sibling form `?video=<watch-base>&v=<id>`). Parsed by `studioQueryFromSearchParams`.
- `applyStudioQueryAutoStart`: on mount/search-param change, a valid query **auto-starts analysis once per video id** (module-level guard via `autoStartedKey` ref; guard released on true unmount via `resetStudioQueryAutoStart` so re-paste/retry can auto-start again). Invalid query → input filled with raw text + `studioInvalidHandoffMessage`.
- Used by the landing page: Home paste form submits to `/studio?video=<url>` (`submitHomePaste`).
- **No keyboard shortcuts** anywhere in the Studio (no keydown handlers in any of the four files). Enter submits the URL form (native form behavior).

---

## 14. Error states and empty states

| Situation | Surface |
|---|---|
| Invalid YouTube URL on Run | Status line: "Need a valid YouTube URL." |
| Analysis cancelled | Status line: "Analysis cancelled." (via Cancel button → AbortController) |
| Analysis failed | Status line: `video.failure.message` or "Analysis failed."; Transcript tab shows the failure message; retry affordance computed by `studioCanRetryTranscript` |
| Working | Status line: `Working · Ns — <stage>. <ETA>`; elapsed resets when work stops |
| Export with nothing to export | Error toast (kind: empty) |
| Export without Pro | Error toast + redirect to Stripe checkout |
| Export other failure | Error toast with message |
| Build live, no pack | Red failure banner + recovery actions |
| Build live, pack missing on host | Red failure banner `HOSTED_PACK_NOT_FOUND` + recovery actions |
| Build live exception | Red failure banner with error text |
| Deploy 401/403 | Redirect to `/login?callbackUrl=/studio` |
| Deploy gate decision | Receipt card with PASS/HOLD/REJECT/ESCALATE chip + reason |
| Chat 402 quota | Amber quota banner + `/pricing` link |
| Chat other error | Red inline banner + assistant error message |
| Player fails to load | Overlay with Retry player + Open on YouTube |
| No video yet | Player placeholder; chat empty state; output pane empty state |
| No pack selected for chat | Chat composer disabled, "Run a video first" |
| Empty output tabs | Per-tab empty notes; pane-level empty state for non-transcript tabs |

---

## 15. Single-pane workbench model (layout-only, inside output)

When `selected.videoPack.pack` exists (`resultReadyShell`), the output area conceptually shows one "pane" at a time (Cursor-style) driven by `studioWorkbenchTabs` / `studioResolveActivePane` / `requestedPane`. In the current `StudioIdeOutput` render, the seven extraction tabs are always visible and `PackWorkbench`/`GroundedSpecReview` wiring lives in props — the workbench-tab plumbing (`requestedPane`, `selectShellPane`, `paneVisible`) is computed in `OneLoopStudio` and partially threaded. A rebuild should decide whether the workbench tabs and the seven extraction tabs are one system or two.

---

## 16. Dead / unwired code (do not blindly port)

These exist in `OneLoopStudio.tsx` but are **never rendered or triggered** in the current UI. The rebuild should treat each as an explicit product decision (restore, redesign, or drop) rather than carrying them over silently:

1. **`PackWorkbench`** (line ~202) — "From this pack" section with Export pack button, Architecture (summary, stages, mermaid diagram), and Artifacts list. Defined, never rendered.
2. **`StudioJobStripDestination`** (line ~275) — job-strip link renderer. Defined, never rendered.
3. **`openApprovedSpecsPrs`** (line ~976) — opens/updates GitHub PRs for approved SOP specs via `openGitHubPrsForApprovedSpecs` server action, branch `spec/<video>-<step>`. **No button calls it.** Related state `approvedSpecIds` / `openingPrs` is write-only.
4. **`act()`** (video-to-actions) — full implementation (event enrich, start, 24×2s poll, `workflowActions`, `usedSameRun`), plus the `hasActionsPane` workbench gate — **no UI trigger exists**.
5. **`completedChecks`** — only ever reset to `[]`; nothing populates it, so `deployHoldReason` always evaluates the empty case.
6. **`Empty` / `Field` / `FieldGroup` / `FieldLabel` / `FieldDescription`** (ui components) — imported, never rendered.
7. **Lucide icons `Play`, `Rocket`, `Hammer`, `GitPullRequest`, `Download`** — imported; only `Download` is used (inside dead `PackWorkbench`).
8. **`transcriptExpanded`** — state exists and resets on selection change, but nothing sets it true in the current render.

---

## 17. Rebuild notes / open product decisions

- **"Check preflight" button**: product direction is to delete it and fully redevelop the deploy area. Do not preserve the current preflight+sign-in-redirect behavior.
- **Deploy vs Build live**: two overlapping deploy paths with contradictory auth behavior (preflight demands sign-in; Build live is anonymous). The rebuild needs one coherent story.
- **Decide the fate of §16 items**: PackWorkbench (architecture/artifacts view), Act (video-to-actions), GitHub PR flow, and SOP check-offs are implemented but unreachable — restore as designed features or cut deliberately.
- **Workbench vs extraction tabs**: reconcile the single-pane workbench model (§15) with the seven always-visible extraction tabs.
- **Receipt scoping**: success/failure/gate receipts are scoped to `selectedVideoId` and cleared on pack switch — preserve this anti-stale behavior.
- **Chat quota**: free tier = 5 AI messages/day, 402 + `upgradeRequired` → Pro upsell to `/pricing`.
- **Export paywall**: 402 → Stripe Checkout for Workflow Pro ($39/mo). Preserve the "results persist, redirect, results still there" behavior.
- **Auto-start**: `?video=` deep link auto-runs analysis once per video id; guard against double-start (StrictMode) is load-bearing.
- **Test fixtures**: use `auJzb1D-fag`; never `dQw4w9WgXcQ` (repo convention).
- **G.A.T.E.**: stays exactly `PASS | HOLD | REJECT | ESCALATE`, non-bypassable; gated transition is `studio.deploy` (`proposed` → `live`).
- **Pack store**: Upstash REST only (`KV_REST_API_*` / `UPSTASH_REDIS_REST_*`); no TCP Redis clients.
- **Pricing (locked)**: Workflow Pro $39/mo or $390/yr; Maintain $199/mo per live product; Ship per-job quote.

## 18. testid catalog (for rebuild verification)

`studio-ide-shell`, `studio-ide-toolbar`, `studio-ide-url-form`, `studio-ide-run`, `studio-ide-cancel`, `studio-ide-packs`, `studio-ide-delete-pack`, `studio-ide-export`, `studio-build-live-button`, `studio-deploy-button`, `studio-ide-status`, `studio-preflight-hint` (id), `studio-gate-receipt`, `studio-gate-decision`, `studio-gate-reason`, `studio-gate-receipt-id`, `studio-gate-receipt-hash`, `studio-gate-live-url`, `studio-ide-video-pane`, `studio-ide-chat-pane`, `studio-ide-output-pane`, `studio-ide-splitter-left`, `studio-ide-splitter-right`, `studio-player`, `studio-player-overlay`, `studio-player-retry`, `studio-ide-chat`, `studio-ide-chat-messages`, `studio-ide-chat-composer`, `studio-ide-chat-input`, `studio-ide-chat-send`, `chat-msg-user`, `chat-msg-assistant`, `studio-ide-output`, `studio-ide-output-tab-events|lingo|tools|intent|signals|spec|transcript`, `studio-ide-output-events|lingo|tools|intent|signals|spec`, `studio-transcript-body`, `studio-export-toast`, `studio-pack-build-live-result`, `studio-pack-build-live-state`, `studio-pack-build-live-video-id`, `studio-pack-build-live-reason-code`, `studio-pack-build-live-artifact-link`, `studio-pack-build-live-pro-cta`, `studio-build-live-failure`, `studio-build-live-recovery-open-hosted|rerun_analysis|scroll_pack`, `studio-job-video-id`, `studio-job-self-link` (dead), `pack-workbench`, `pack-architecture`, `pack-artifacts` (dead).
