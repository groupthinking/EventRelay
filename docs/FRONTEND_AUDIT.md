# Frontend Audit — apps/web

**Date:** 2026-02-08
**Purpose:** Identify ALL mock/hardcoded data, broken routes, and non-functional code.

---

## Summary

The frontend (`apps/web`) is largely a **static shell with hardcoded mock data**. The only real backend integration is:

1. `POST /api/video` → proxies to backend `/api/v1/transcript-action` ✅ **REAL**
2. `GET /api/dashboard` → proxies to backend `/stats` ✅ **REAL** (but backend `/stats` doesn't exist, so it always returns fallback zeros)
3. `GET /api/video` → health check against backend ✅ **REAL**
4. Playground → sends real `fetch()` requests to backend endpoints ✅ **REAL**

Everything else is fake.

---

## File-by-File Breakdown

### 1. `page.tsx` (Homepage — 998 lines)

| Item                                                                                                   | Status          | Details                                  |
| ------------------------------------------------------------------------------------------------------ | --------------- | ---------------------------------------- |
| Video URL input → redirects to `/dashboard?video=`                                                     | ✅ Real         | Actually navigates                       |
| `AnimatedCounter` — "50K+ Videos Processed"                                                            | ❌ **FAKE**     | Hardcoded marketing numbers              |
| `AnimatedCounter` — "2.3s Avg Processing"                                                              | ❌ **FAKE**     | Hardcoded                                |
| `AnimatedCounter` — "7 AI Models"                                                                      | ❌ **FAKE**     | Hardcoded                                |
| `PipelineVisualization`                                                                                | ❌ **FAKE**     | Static visual, no real data              |
| `TestimonialCard` — "Sarah Kim", "James Mitchell", "Alex Rodriguez"                                    | ❌ **FAKE**     | Fabricated testimonials with fake people |
| Company logos — "TechFlow", "DevScale", "MediaPro", "StartupAI", "CloudNine"                           | ❌ **FAKE**     | Fabricated companies                     |
| Feature descriptions                                                                                   | ⚠️ Marketing    | Aspirational, not current state          |
| Footer links — `/docs`, `/pricing`, `/blog`, `/changelog`, `/support`, `/status`, `/about`, `/privacy` | ❌ **BROKEN**   | Pages don't exist, will 404              |
| API code preview example                                                                               | ⚠️ Aspirational | `uvai.video.analyze()` SDK doesn't exist |
| "Join thousands of teams..."                                                                           | ❌ **FAKE**     | No users exist                           |

### 2. `dashboard/page.tsx` (Dashboard — 805 lines)

| Item                                             | Status        | Details                                                        |
| ------------------------------------------------ | ------------- | -------------------------------------------------------------- |
| Video URL input → calls `POST /api/video`        | ✅ Real       | Actually calls backend                                         |
| `handleAddVideo` progress simulation             | ⚠️ Partial    | Fake progress bar (5% increments), real API call underneath    |
| Metrics fetch from `/api/dashboard`              | ✅ Real call  | But returns zeros because backend `/stats` doesn't exist       |
| 3 hardcoded mock videos in `useState`            | ❌ **FAKE**   | "React Hooks Deep Dive", "Q4 Strategy Meeting", "Product Demo" |
| Mock video insights (summaries, actions, topics) | ❌ **FAKE**   | All fabricated                                                 |
| Activity feed — 5 hardcoded activities           | ❌ **FAKE**   | Static `useState`, never updates                               |
| `AnalysisPanel` import (chat component)          | ❌ **BROKEN** | Calls `/api/chat` which doesn't exist                          |
| Backend system status badge ("System Online")    | ⚠️ Semi-real  | Shows green always, doesn't reflect actual backend state       |
| Video detail modal insights display              | ❌ **FAKE**   | Displays mock insights data                                    |

### 3. `playground/page.tsx` (API Playground — 354 lines)

| Item                                          | Status               | Details                                        |
| --------------------------------------------- | -------------------- | ---------------------------------------------- |
| Endpoint list                                 | ⚠️ Mixed             | Lists 7 endpoints, most DON'T EXIST on backend |
| `POST /execute_video`                         | ❌ **DOESN'T EXIST** | Backend has no such endpoint                   |
| `POST /analyze_video_v2`                      | ❌ **DOESN'T EXIST** | Backend has no such endpoint                   |
| `POST /analyze_video`                         | ❌ **DOESN'T EXIST** | Backend has no such endpoint                   |
| `POST /dogfood`                               | ❌ **DOESN'T EXIST** | Backend has no such endpoint                   |
| `POST /evolve`                                | ❌ **DOESN'T EXIST** | Backend has no such endpoint                   |
| `GET /stats`                                  | ❌ **DOESN'T EXIST** | Backend has no such endpoint                   |
| `GET /lessons`                                | ❌ **DOESN'T EXIST** | Backend has no such endpoint                   |
| Code examples reference `https://api.uvai.io` | ❌ **DOESN'T EXIST** | No production API deployed                     |
| "No authentication required" claim            | ⚠️ True for local    | But misleading                                 |
| `handleSendRequest` — actual fetch            | ✅ Real              | Sends real requests, they'll just fail         |

### 4. `components/AnalysisPanel.tsx` (Chat — 187 lines)

| Item                      | Status        | Details                                           |
| ------------------------- | ------------- | ------------------------------------------------- |
| Calls `POST /api/chat`    | ❌ **BROKEN** | No `/api/chat` route exists                       |
| Initial greeting message  | ❌ **FAKE**   | "I've analyzed this video" — no analysis happened |
| "Online" status indicator | ❌ **FAKE**   | Always shows green, not connected to anything     |

### 5. `components/ui/` (UI primitives)

| File                   | Status                                               |
| ---------------------- | ---------------------------------------------------- |
| `Badge.tsx`            | ✅ OK — Pure UI component                            |
| `Button.tsx`           | ✅ OK — Pure UI component                            |
| `Card.tsx`             | ✅ OK — Pure UI component                            |
| `Input.tsx`            | ✅ OK — Pure UI component                            |
| `SuggestedPrompts.tsx` | ⚠️ Hardcoded topic suggestions, but functional as UI |
| `index.ts`             | ✅ OK — Barrel export                                |

### 6. `api/route.ts` (Root API)

| Item                                         | Status    |
| -------------------------------------------- | --------- | ------------------------------ |
| Returns static JSON with name/version/status | ⚠️ Static | Not connected to anything real |

### 7. `api/dashboard/route.ts`

| Item                          | Status       |
| ----------------------------- | ------------ | ----------------------------------------------- |
| Fetches from backend `/stats` | ✅ Real call | But endpoint doesn't exist, falls back to zeros |

### 8. `api/video/route.ts`

| Item                                            | Status      |
| ----------------------------------------------- | ----------- | --------------------------------------------- |
| `POST` — proxies to `/api/v1/transcript-action` | ✅ **REAL** | This is the only truly functional integration |
| `GET` — health check                            | ✅ **REAL** | Checks backend health                         |

---

## Broken Links (Pages That Don't Exist)

These are linked from nav/footer but have no corresponding pages:

- `/docs`
- `/pricing`
- `/blog`
- `/changelog`
- `/support`
- `/status`
- `/about`
- `/privacy`

---

## What Actually Works End-to-End

1. **Homepage** → paste YouTube URL → redirects to dashboard
2. **Dashboard** → URL triggers `POST /api/video` → proxies to backend `/api/v1/transcript-action` → result displayed
3. **Playground** → can send requests to backend (but most listed endpoints don't exist)

That's it. Everything else is decoration.

---

## Action Items (Priority Order)

### P0 — Remove Fake/Misleading Content

1. Remove all 3 hardcoded mock videos from dashboard `useState`
2. Remove hardcoded activity feed
3. Remove fake testimonials (Sarah Kim, James Mitchell, Alex Rodriguez)
4. Remove fake company logos
5. Remove fake stats ("50K+ Videos Processed")
6. Remove broken nav/footer links to non-existent pages

### P1 — Fix Broken Integrations

7. Fix or remove AnalysisPanel (calls non-existent `/api/chat`)
8. Fix playground endpoint list to match REAL backend endpoints
9. Fix dashboard `/api/dashboard` to call a real backend endpoint (e.g., `/api/v1/health`)

### P2 — Make Dashboard Functional

10. Dashboard should start empty — no videos until user adds one
11. Activity feed should reflect real events from video processing
12. Metrics should show real numbers from successful processing

### P3 — Remove Dead Code

13. Remove links to pages that don't exist
14. Clean up homepage marketing copy to reflect actual capabilities
