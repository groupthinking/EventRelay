# Video → GTM Revenue Architecture v3.0
## Complete End-to-End Pipeline Design — Video In → Deployed Site Out
## Date: March 20, 2026 (Updated from v2.0 March 13, 2026)
## Author: Lead Engineer + viralnowsales

---

## What Changed in v3.0

| Area | v2.0 | v3.0 |
|------|------|------|
| Pipeline end point | PDF + manual deploy | Vercel auto-deploy + live domain |
| Phases | 0-6 (INGEST→OPERATE conceptual) | 0-7 (INGEST→OPERATE implemented) |
| Deployment | Cloudflare Pages / manual | Vercel connector + CLI + GitHub auto-deploy |
| Domain | "Transfer to Cloudflare" recommendation | Full DNS flow: Cloudflare CNAME → Vercel |
| Agent Operations | Described roles only | Implemented cron configs (MONITOR/GROWTH/REVENUE) |
| Content Repurposing | MERCURY described | MERCURY + website builder integrated |
| Skill version | v2.0 | v3.0 with reference files |

---

## Part 1: What We Built (v1.0) — Takeaways

### What Worked
1. **4-agent ATLAS→PRISM→FORGE→SENTINEL pattern** — clean separation of concerns, each agent does one job well
2. **Parallel transcription** (4 × 20-min segments) — cut 81 min of audio processing to ~5 min
3. **Parallel Phase 1 + Phase 2** (ATLAS + PRISM) — PRISM starts researching known entities from metadata while ATLAS is still extracting
4. **SENTINEL as QA gate** — caught 9 real errors that would have shipped. Non-negotiable in any pipeline
5. **[VERIFY] flag protocol** — prevents hallucination propagation
6. **Session learning log** — `/master_prompt_learning/` captures corrections for next run

### What Was Enhanced in v2.0
1. **Speaker attribution pre-check** — SENTINEL-LITE pass before FORGE
2. **Visual extraction layer** — Gemini 3.1 Pro for on-screen text/code
3. **Parallel FORGE** — 3 writers by chapter group, then merge
4. **Manifest intelligence** — PRISM v2 with affiliate links + pricing
5. **MERCURY agent** — Content repurposing specialist

### What v3.0 Adds
1. **Vercel deployment automation** — Connector API or CLI, zero manual steps
2. **Domain connection flow** — Cloudflare DNS → Vercel with exact CNAME configs
3. **Vercel Functions** — Serverless email capture, analytics, webhooks
4. **GitHub integration** — Push to `groupthinking` org → Vercel auto-deploys
5. **Agent operations implementation** — Real `schedule_cron` configs, not just descriptions
6. **Connected services matrix** — Vercel ↔ GitHub ↔ SendGrid ↔ Cloudflare ↔ HubSpot

---

## Part 2: Full Pipeline Architecture (v3.0)

```
┌─────────────────────────────────────────────────────┐
│                    INPUT LAYER                        │
│  YouTube URL │ Podcast URL │ Transcript │ Upload      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              PHASE 0: INGEST                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Audio DL │  │ Video DL │  │ Metadata Fetch   │   │
│  │ + Split  │  │ (Gemini) │  │ (Title, Chapters)│   │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │                  │             │
│       ▼              ▼                  ▼             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │Transcribe│  │ Visual   │  │ Chapter          │   │
│  │(parallel)│  │ Extract  │  │ Anchors          │   │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       └──────────────┴─────────────────┘             │
│                      │                                │
│              full_context.json                        │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│           PHASE 1+2: EXTRACT + RESEARCH (PARALLEL)    │
│                                                       │
│  ┌────────────┐         ┌────────────┐               │
│  │   ATLAS    │         │   PRISM    │               │
│  │ Segment &  │         │ Research & │               │
│  │ Extract    │         │ Ground     │               │
│  │            │         │            │               │
│  │ → segments │         │ → verified │               │
│  │ → quotes   │         │   URLs     │               │
│  │ → tools    │         │ → affiliate│               │
│  │ → metrics  │         │   links    │               │
│  │ → [VERIFY] │         │ → pricing  │               │
│  └─────┬──────┘         └─────┬──────┘               │
│        │                      │                       │
│        └──────────┬───────────┘                       │
│                   ▼                                   │
│        ┌──────────────────┐                           │
│        │ SENTINEL-LITE    │  ← Quote attribution     │
│        │ (pre-check only) │     verification         │
│        └────────┬─────────┘                           │
│                 │                                     │
└─────────────────┼─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              PHASE 3: SYNTHESIS (PARALLEL)             │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ FORGE-A  │  │ FORGE-B  │  │ FORGE-C  │           │
│  │ Ch 1-4   │  │ Ch 5-8   │  │ Ch 9-11  │           │
│  │(Foundtn) │  │(Growth)  │  │(Scale +  │           │
│  │          │  │          │  │ Playbook)│           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       └──────────────┴─────────────┘                 │
│                      │                                │
│               ┌──────┴──────┐                        │
│               │    MERGE    │                        │
│               │ Consistency │                        │
│               │   Pass      │                        │
│               └──────┬──────┘                        │
│                      │                                │
└──────────────────────┼────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              PHASE 4: QA GATE                         │
│                                                       │
│  ┌──────────────────────────────────┐                │
│  │         SENTINEL-FULL            │                │
│  │  • Chapter coverage check        │                │
│  │  • Metrics spot-check (10+)      │                │
│  │  • Quote verification (15+)      │                │
│  │  • PRISM integration check       │                │
│  │  • [VERIFY] flag resolution      │                │
│  │  • No-invention check            │                │
│  │  • Cross-reference consistency   │                │
│  └──────────────┬───────────────────┘                │
│                 │                                     │
│          final_mirrored_guide.md                     │
│          sentinel_qa_report.md                       │
│                                                       │
└─────────────────┼─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│         PHASE 5: MERCURY — ASSET GENERATION (PARALLEL)│
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │   PDF    │  │ WEBSITE  │  │ MERCURY  │           │
│  │Generator │  │ Builder  │  │ Content  │           │
│  │          │  │          │  │ Repurpose│           │
│  │• Cover   │  │• Landing │  │          │           │
│  │• TOC     │  │• Guide   │  │• 25 posts│           │
│  │• Chapters│  │  pages   │  │• 7 emails│           │
│  │• Design  │  │• SEO     │  │• 10 cards│           │
│  │          │  │• CTA     │  │• 5 ads   │           │
│  │          │  │• Email   │  │• SEO meta│           │
│  │          │  │  capture │  │          │           │
│  │          │  │• Affilite│  │          │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │              │                 │
└───────┼──────────────┼──────────────┼─────────────────┘
        │              │              │
        ▼              ▼              ▼
┌─────────────────────────────────────────────────────┐
│       PHASE 6: DEPLOY — VERCEL + DOMAIN (NEW v3.0)   │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │           VERCEL DEPLOYMENT                   │    │
│  │                                               │    │
│  │  Step 1: Check Vercel connector               │    │
│  │    → DISCONNECTED? OAuth connect              │    │
│  │    → CONNECTED? Proceed to deploy             │    │
│  │                                               │    │
│  │  Step 2: Deploy                               │    │
│  │    → Option A: Vercel connector API (preferred)│   │
│  │    → Option B: GitHub push → auto-deploy       │   │
│  │    → Option C: vercel CLI                     │    │
│  │                                               │    │
│  │  Step 3: Connect domain                       │    │
│  │    → Cloudflare DNS: CNAME → cname.vercel-dns │    │
│  │    → Proxy: OFF (grey cloud)                  │    │
│  │    → Vercel auto-provisions SSL               │    │
│  │                                               │    │
│  │  Step 4: Environment variables                │    │
│  │    → SENDGRID_API_KEY                         │    │
│  │    → GA_MEASUREMENT_ID                        │    │
│  │    → AFFILIATE_PARTNER_ID                     │    │
│  │                                               │    │
│  │  Step 5: Verify                               │    │
│  │    → HTTPS, forms, affiliates, SEO, speed     │    │
│  │                                               │    │
│  │  Step 6: Post-deploy suggestions              │    │
│  │    → Custom domain, Vercel Functions,          │    │
│  │      Analytics, Edge Config, Preview Deploys  │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │           DOMAIN DNS FLOW                     │    │
│  │                                               │    │
│  │  GoDaddy → Cloudflare Registrar transfer      │    │
│  │  Cloudflare DNS → CNAME: cname.vercel-dns.com │    │
│  │  Vercel → SSL auto-provision (Let's Encrypt)  │    │
│  │                                               │    │
│  │  Shortcut: {{slug}}.vercel.app (free, instant)│    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │           MONETIZATION LAYERS                 │    │
│  │                                               │    │
│  │  Layer 1: Affiliate Revenue                   │    │
│  │    → Tool links in guide earn commission      │    │
│  │    → PRISM auto-injects affiliate URLs        │    │
│  │                                               │    │
│  │  Layer 2: Lead Generation                     │    │
│  │    → PDF download captures email              │    │
│  │    → Email sequence nurtures to paid offer    │    │
│  │    → Vercel Function handles capture API      │    │
│  │                                               │    │
│  │  Layer 3: Premium Content                     │    │
│  │    → Full guide = free teaser                 │    │
│  │    → Deeper implementation guides = paid      │    │
│  │    → 1:1 consulting CTA = high ticket         │    │
│  │                                               │    │
│  │  Layer 4: SEO + Ad Revenue                    │    │
│  │    → Chapter pages rank for long-tail queries │    │
│  │    → Display ads on high-traffic pages        │    │
│  │                                               │    │
│  │  Layer 5: Content Licensing                   │    │
│  │    → Sell guides to newsletters/aggregators   │    │
│  │    → White-label for other brands             │    │
│  └──────────────────────────────────────────────┘    │
│                                                       │
└───────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│     PHASE 7: AGENT OPERATIONS TEAM (IMPLEMENTED)     │
│     Post-Deploy Autonomous Management                │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ MONITOR  │  │ GROWTH   │  │ REVENUE  │           │
│  │ Agent    │  │ Agent    │  │ Agent    │           │
│  │          │  │          │  │          │           │
│  │• Uptime  │  │• SEO rank│  │• Affilite│           │
│  │• 404s    │  │• Traffic │  │  tracking│           │
│  │• Speed   │  │• Social  │  │• Email   │           │
│  │• SSL     │  │  posting │  │  convert │           │
│  │• Vercel  │  │• A/B test│  │• Revenue │           │
│  │  deploy  │  │• Content │  │  reports │           │
│  │  status  │  │  refresh │  │• Forecast│           │
│  └──────────┘  └──────────┘  └──────────┘           │
│                                                       │
│  Implementation: schedule_cron                       │
│  • MONITOR: 0 */4 * * * (every 4 hours)             │
│  • GROWTH:  0 14 * * *  (daily at 2pm UTC)          │
│  • REVENUE: 0 15 * * 1  (weekly Monday 3pm UTC)     │
│  • All: background=true, notify only on findings     │
│                                                       │
│  Connected Services:                                 │
│  Vercel ↔ GitHub (groupthinking, auto-deploy)        │
│  ├── SendGrid (email capture + drip)                 │
│  ├── HubSpot (CRM + lead management)                │
│  ├── Google Analytics (traffic + conversions)        │
│  ├── Google Search Console (SEO rankings)            │
│  ├── Cloudflare (DNS + CDN + security)               │
│  └── Bitly (short links for social posts)            │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## Part 3: Domain Strategy

### Recommended Domain Mapping

| Domain | Use Case | Hosting | DNS | Status |
|--------|----------|---------|-----|--------|
| `sell.solutions` | GTM landing for video guides | Vercel | Cloudflare | Transfer from GoDaddy |
| `myagentjob.com` | Agent ops dashboard | Vercel | GoDaddy/Cloudflare | Live |
| `uvai.io` | UVAI platform core | Vercel | Cloudflare | Active |
| `mcp.expose` | MCP tools | Vercel | Vercel DNS | Active |
| `myai.directory` | AI directory | Vercel | GoDaddy/Vercel | Active |
| `subboxx.com` | Subscription guides | Vercel | Cloudflare | Future |
| `vizul.ai` | Visual extraction | Vercel | Cloudflare | Future |

### Migration Path
```
Current: GoDaddy registrar → various hosting
Target:  Cloudflare registrar + DNS → Vercel hosting (all properties)

Steps per domain:
1. Unlock domain in GoDaddy
2. Get EPP/auth code
3. Transfer to Cloudflare Registrar (~$8-10/yr vs $15-20)
4. Add CNAME: @ → cname.vercel-dns.com (proxy OFF)
5. Add domain in Vercel project settings
6. Verify: SSL auto-provisions, site loads at custom domain
```

---

## Part 4: Vercel CLI & Plugin Setup

### For Perplexity Computer Workflows
```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Install Perplexity plugin
npx plugins add vercel/vercel-plugin

# Deploy project
cd deploy && vercel

# Set environment variables
vercel env add SENDGRID_API_KEY production
vercel env add GA_MEASUREMENT_ID production
```

### For Other AI Coding Agents
```bash
# Cline, Windsurf, GitHub Copilot, etc.
npx skills add vercel-labs/agent-skills

# This gives the agent:
# - vercel deploy
# - vercel env management
# - vercel domain configuration
# - vercel function deployment
```

### vercel.json (Static Site Template)
```json
{
  "version": 2,
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" }
      ]
    }
  ]
}
```

### vercel.json (Static + Serverless Functions)
```json
{
  "version": 2,
  "builds": [
    { "src": "**/*.html", "use": "@vercel/static" },
    { "src": "api/**/*.js", "use": "@vercel/node" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/$1" },
    { "src": "/(.*)", "dest": "/$1" }
  ]
}
```

---

## Part 5: Agent Operational Team Roles (Implemented)

### MONITOR Agent (Cron: every 4 hours)
- Health check: site up, SSL valid, no 404s
- Performance: page load <3s, Core Web Vitals pass
- Vercel deployment status: check for failed builds
- Error detection: broken links, missing images, API failures
- Alert: only notify on issues (no "all clear" noise)

### GROWTH Agent (Cron: daily)
- Post 1 social media piece from MERCURY's content bank
- Check SEO rankings for target keywords (Google Search Console)
- Monitor backlink growth
- A/B test headlines on landing page (Vercel Edge Config)
- Refresh stale content (update PRISM research quarterly)
- Track: new video uploads from source channel → auto-trigger pipeline

### REVENUE Agent (Cron: weekly Monday)
- Pull affiliate earnings from connected programs
- Calculate: email signups → conversion rate → revenue per subscriber
- Report: which guide pages drive most affiliate clicks
- Optimize: rotate underperforming CTAs
- Forecast: project monthly revenue based on traffic trends

### Scaling: Multiple Video Guides
```
Video 1 → sell.solutions/whop-guide   → MONITOR-1, GROWTH-1, REVENUE-1
Video 2 → sell.solutions/saas-guide   → MONITOR-2, GROWTH-2, REVENUE-2
Video 3 → uvai.io/guides/ai-tools     → MONITOR-3, GROWTH-3, REVENUE-3

Weekly: All REVENUE agents → consolidated report → best-performing guide → next video topic
```

---

## Part 6: Rules & Prompting Takeaways

### Non-Negotiable Rules
1. **SENTINEL is mandatory.** Never ship content without a QA gate agent.
2. **[VERIFY] flag protocol.** Any uncertainty gets flagged, not guessed.
3. **Speaker attribution check.** For multi-speaker content, verify 10+ quotes before writing.
4. **Parallel where possible.** ATLAS + PRISM in parallel saves 30-40% time.
5. **Session learning logs.** Every pipeline run saves corrections to `/master_prompt_learning/`.
6. **No fabricated URLs.** PRISM marks [UNVERIFIED] if it can't find a source.
7. **Deploy verification.** Never mark "done" until HTTPS, forms, affiliates, and SEO are verified.
8. **Agent ops = background crons.** MONITOR/GROWTH/REVENUE run autonomously, notify only on findings.

### Prompting Patterns
1. **The "Snow Me Under" Pattern**: Dump ALL source material to AI → synthesize understanding → build
2. **The Sequential Feedback Pattern**: Fix ALL feedback from person 1 before talking to person 2
3. **The Role + Mission + Constraints + Output Format Pattern**: Produced 95%+ accuracy across all 4 agents
4. **The TLDR Action Pattern**: Every response ends with an executable next step
5. **The Deploy-Verify-Operate Pattern** (NEW v3.0): Build → push → deploy → domain → verify → cron ops → autonomous revenue
