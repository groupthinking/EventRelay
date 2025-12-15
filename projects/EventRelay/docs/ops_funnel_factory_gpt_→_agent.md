# OPS: Funnel Factory — GPT → Agent.AI → HF Spaces (Deployment Spec)

**Objective:** Automate a full loop that detects demand (GPT Store + Agent.AI), finds/forks a Hugging Face Space that fits, rebrands, deploys, wraps with Agent.AI & a thin GPT front, and funnels to a Stripe‑monetized website. Includes telemetry, duplication control, and MoM trend tracking.

---

## 0) System Overview

**Flow:**
1) **Crawler** → scrape GPT Store categories/search + Agent.AI categories → ranked demand signals
2) **Selector** → map demand to HF Spaces (license filter, quality score)
3) **Forker/Branding** → clone repo, inject brand, features, telemetry
4) **Deployer** → Hugging Face Space or Vercel/Fly.io for the app
5) **Agent Wrapper** → Agent.AI endpoints that front the app
6) **GPT Wrapper** → minimal GPT page w/ clear CTA, links w/ UTM
7) **Site/Funnel** → Next.js + Stripe Payment Element + auth + analytics
8) **Metrics** → warehouse + dashboards (MoM by category, CTR, LP CR, checkout CR)
9) **Orchestrator** → MCP playbooks to rinse/repeat

---

## 1) Repo Layout

```
/ops
  ├─ Makefile
  ├─ .env.prepopulated
  ├─ docker-compose.yml
  ├─ scripts/
  │   ├─ bootstrap.sh
  │   ├─ seed_demo.sh
  │   └─ vercel_deploy.sh
  ├─ crawler/
  │   ├─ playwright.config.ts
  │   ├─ gpt_store_crawler.ts
  │   └─ agentai_catalog.ts
  ├─ selector/
  │   ├─ hf_search.py
  │   └─ scorer.py
  ├─ forker/
  │   ├─ clone_and_brand.py
  │   └─ license_check.py
  ├─ deploy/
  │   ├─ deploy_hf.py
  │   ├─ deploy_vercel.py
  │   └─ deploy_flyio.py
  ├─ agentai_wrapper/
  │   ├─ main.py (FastAPI)
  │   └─ client.py
  ├─ gpt_wrapper/
  │   ├─ listing.md (title/desc/keywords templating)
  │   └─ actions.json (if used)
  ├─ site/
  │   ├─ next.config.js
  │   ├─ src/pages/index.tsx
  │   ├─ src/pages/checkout.tsx
  │   ├─ src/lib/stripe.ts
  │   ├─ src/lib/utms.ts
  │   └─ public/brand/*
  ├─ mcp/
  │   ├─ tools.yaml
  │   └─ playbooks/
  │       ├─ clone_deploy.yaml
  │       └─ score_rotate.yaml
  └─ analytics/
      ├─ ddl.sql
      ├─ etl.py
      └─ dashboards.md
```

---

## 2) .env.prepopulated (template)

```
# Core Keys
OPENAI_API_KEY=your_openai_api_key
AGENTAI_API_KEY=your_agentai_api_key
HUGGINGFACE_TOKEN=your_hf_token
STRIPE_API_KEY=sk_live_or_test
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_or_test

# Analytics / Telemetry
POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
PLAUSIBLE_DOMAIN=

# Hosting / Deploy
VERCEL_TOKEN=
VERCEL_PROJECT_ID=
FLY_API_TOKEN=
HF_ORG=your_hf_org
WEB_BASE_URL=https://yourdomain.com

# Data Warehouse
WAREHOUSE_URL=postgres://user:pass@host:5432/db
BIGQUERY_PROJECT_ID=
BIGQUERY_DATASET=funnel_factory

# Crawler
CRAWL_RATE_LIMIT_MS=1500
CRAWL_USER_AGENT=FunnelFactoryBot/1.0 (+contact@yourdomain.com)

# MCP
MCP_REGISTRY_URL=
MCP_AUTH_TOKEN=
```

> **Note:** commit with `.env.prepopulated`; never commit real `.env`.

---

## 3) Crawler (Playwright + Node)

**Purpose:** Extract GPT Store categories/search listings (title, author, short_url, category chips, updated_at) and Agent.AI catalog pages. Persist **raw HTML snapshots** + **parsed JSON** to storage.

**Key practices:** polite rate limits, rotating UAs, retry w/ backoff, snapshot before parse for future‑proofing.

**`crawler/gpt_store_crawler.ts` (excerpt):**
```ts
import { chromium } from 'playwright';
import fs from 'fs/promises';

async function crawlCategory(category: string) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ userAgent: process.env.CRAWL_USER_AGENT });
  await page.goto(`https://chat.openai.com/gpts?category=${encodeURIComponent(category)}`);
  // paginate
  const items: any[] = [];
  while (true) {
    const cards = await page.$$('[data-testid="gpt-card"]');
    for (const c of cards) {
      const title = await c.$eval('.title', el => el.textContent?.trim());
      const author = await c.$eval('.author', el => el.textContent?.trim());
      const href = await c.$eval('a', (a: any) => a.href);
      const updated = await c.$eval('.updated', el => el.textContent?.trim()).catch(() => null);
      items.push({ title, author, href, category, updated });
    }
    const next = await page.$('button[aria-label="Next"]');
    if (!next) break;
    await next.click();
    await page.waitForTimeout(Number(process.env.CRAWL_RATE_LIMIT_MS || 1500));
  }
  await browser.close();
  return items;
}

(async () => {
  const categories = ['Productivity','Programming','Research','Writing','Education','Lifestyle','DALL·E'];
  const all: any[] = [];
  for (const cat of categories) {
    const rows = await crawlCategory(cat);
    all.push(...rows);
  }
  await fs.writeFile('out/gpt_store.json', JSON.stringify(all, null, 2));
})();
```

**Agent.AI catalog crawler** mirrors the above; store to `out/agentai.json`.

---

## 4) Selector (HF Spaces search + scoring)

**Inputs:** demand phrases from crawler; **Filters:** license ∈ {MIT, Apache-2.0, BSD-3}, last update ≤ 90d, stars/downloads.

**`selector/hf_search.py` (excerpt):**
```python
from huggingface_hub import HfApi

api = HfApi(token=os.getenv('HUGGINGFACE_TOKEN'))

LICENSE_OK = {"mit","apache-2.0","bsd-3-clause"}

def search_spaces(query: str, limit=20):
    results = api.list_spaces(search=query, sort="lastModified", direction=-1)
    picked = []
    for sp in results:
        lic = (sp.cardData or {}).get('license','').lower()
        if lic in LICENSE_OK:
            picked.append({
              'id': sp.id, 'sdk': sp.sdk, 'likes': sp.likes,
              'updated': sp.lastModified, 'license': lic
            })
        if len(picked) >= limit:
            break
    return picked
```

**`selector/scorer.py` (logic):**
- score = w1·license + w2·recency + w3·likes + w4·keyword_match + w5·demo_simplicity
- choose top‑N per demand phrase

---

## 5) Forker & Branding

**`forker/clone_and_brand.py` (excerpt):**
```python
import os, subprocess, shutil, json

BRAND_NAME = os.getenv('BRAND_NAME','YourBrand')

def clone(repo_id: str):
    url = f"https://huggingface.co/spaces/{repo_id}"
    target = f"workspaces/{repo_id.replace('/', '_')}"
    subprocess.run(["git","clone",url,target], check=True)
    return target

def inject_brand(path: str):
    # swap logo, colors, footer CTA
    shutil.copyfile('assets/logo.svg', f"{path}/public/logo.svg")
    # add telemetry snippet, env wiring, feature flags

```

**License guard (optional):** `forker/license_check.py` aborts on GPL/Non‑commercial.

---

## 6) Deployment Options

**A) Hugging Face Spaces**
- Pros: fastest path; built‑in GPU; one‑click public.
- `deploy/deploy_hf.py` → uses `HfApi.create_or_update_space`.

**B) Vercel**
- Pros: edge, custom domain, SSR (Next.js). Use `scripts/vercel_deploy.sh` with `VERCEL_TOKEN`.

**C) Fly.io**
- Pros: global Docker runtime; easy scaling. `deploy_flyio.py` builds and releases.

> Start with HF for speed; migrate winners to Vercel/Fly for control.

---

## 7) Agent.AI Wrapper (FastAPI)

**`agentai_wrapper/main.py` (excerpt):**
```python
from fastapi import FastAPI
import requests, os

AGENTAI_BASE = os.getenv('AGENTAI_BASE_URL','https://api-lr.agent.ai/v1')
API_KEY = os.getenv('AGENTAI_API_KEY')

app = FastAPI()

@app.post('/agentai/invoke_llm')
def invoke_llm(payload: dict):
    r = requests.post(f"{AGENTAI_BASE}/llm/invoke", json=payload, headers={"Authorization": f"Bearer {API_KEY}"})
    return r.json()

@app.post('/agentai/invoke_agent')
def invoke_agent(payload: dict):
    r = requests.post(f"{AGENTAI_BASE}/agents/invoke", json=payload, headers={"Authorization": f"Bearer {API_KEY}"})
    return r.json()

@app.post('/action/rest_call')
def rest_call(payload: dict):
    r = requests.post(f"{AGENTAI_BASE}/action/rest_call", json=payload, headers={"Authorization": f"Bearer {API_KEY}"})
    return r.json()
```

> Add retries, timeouts, and circuit breaker.

---

## 8) GPT Wrapper (listing templates)

**`gpt_wrapper/listing.md` variables:**
- `{{TITLE}}` exact‑match keyword + benefit
- `{{ONE_LINE}}` value prop
- `{{DESC}}` 4 bullets: what it does, free limits, Pro unlocks, privacy note
- CTA links include UTM: `?src=gptstore&cat={{CAT}}&kw={{KW}}`

**Option:** Actions JSON to call your `agentai_wrapper` endpoints if eligible.

---

## 9) Website / Funnel (Next.js + Stripe)

**Key:** inline **Payment Element**, Apple Pay/Google Pay, minimal fields.

**`site/src/pages/checkout.tsx` (excerpt):**
```tsx
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';

function CheckoutForm(){
  const stripe = useStripe();
  const elements = useElements();
  const onSubmit = async (e)=>{
    e.preventDefault();
    await stripe?.confirmPayment({ elements, confirmParams: { return_url: process.env.NEXT_PUBLIC_RETURN_URL } });
  };
  return (<form onSubmit={onSubmit}><PaymentElement /><button>Pay</button></form>);
}
```

**UTM capture:** `site/src/lib/utms.ts` stores query params → cookie → associates to Stripe `metadata` on session create.

**Plans (default):** Free → $9 Starter (export/API) → $29 Pro (batch/history) → $99 Team (3 seats/SSO stub).

---

## 10) MCP Integration

**`mcp/tools.yaml` (excerpt):**
```yaml
- name: demand.crawl
  cmd: node crawler/gpt_store_crawler.js
- name: agentai.invoke
  http:
    url: http://agentai-wrapper:8001/agentai/invoke_agent
    method: POST
- name: hf.search
  cmd: python selector/hf_search.py --q "{{query}}"
- name: app.deploy.vercel
  cmd: bash scripts/vercel_deploy.sh {{repo_path}}
- name: site.launch
  cmd: node site/scripts/launch.js
```

**Playbooks:**
- `clone_deploy.yaml`: demand → search → fork → deploy → wrap → publish
- `score_rotate.yaml`: monitor metrics → scale winners → kill losers

---

## 11) Data & Dashboards

**Warehouse tables:**
- `gpt_listings(day, title, author, category, updated_at, short_url)`
- `agentai_listings(day, title, category, updated_at, url)`
- `sessions(day, utm_src, utm_cat, utm_kw, page, device)`
- `checkouts(day, status, amount, method, utm_src, utm_kw)`

**Metrics:**
- **Δ-growth (category)**: `count_today - count_7days_ago` / `count_7days_ago`
- **MoM share**: category_count / total_count
- **LP CR**: checkouts_initiated / landing_visits
- **Checkout CR**: success / initiated
- **Duplicate ratio**: duplicates / total listings (title+author fuzzy match)

**Metabase views:**
1) **Demand MoM by Category** (stacked area + anomaly flags)
2) **Funnel** (Visits → Clicks from GPT/Agent → LP → Checkout → Paid)
3) **Revenue by Domain** (ARPU by category/domain; payment method mix)

**Example SQL (Postgres):**
```sql
SELECT day, category,
       COUNT(*) AS count,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (PARTITION BY day), 2) AS share_pct
FROM gpt_listings
GROUP BY day, category
ORDER BY day, share_pct DESC;
```

---

## 12) Makefile Targets

```
bootstrap: ## install deps, create buckets, init DB
crawl: ## run crawlers, write to analytics/raw
select: ## run HF search + scoring
fork: ## clone + brand selected repo
ship-hf: ## deploy to Hugging Face Space
ship-vercel: ## deploy to Vercel
wrap-agent: ## start Agent.AI wrapper
site-dev: ## run Next.js site locally
etl: ## load raw → warehouse
dash: ## render/update dashboards
```

---

## 13) Runbook (Day‑1 to First Live)

1) `make bootstrap`
2) Set keys in `.env`
3) `make crawl` → inspect `analytics/raw/*.json`
4) `make select` → pick top candidates
5) `make fork` → edit theme, text, limits
6) `make ship-hf` (or `ship-vercel`)
7) `make wrap-agent` → verify endpoints
8) Configure `gpt_wrapper/listing.md` → publish GPT listing
9) `make site-dev` → connect CTA to deployed app
10) `make etl && make dash` → confirm dashboards

---

## 14) Guardrails

- Respect robots, rate‑limit crawls, snapshot HTML before parse
- License filter: prefer MIT/Apache/BSD; log others for manual review
- No scraping behind auth; no UI automation of Store actions
- Clear disclosures in GPT/Agent descriptions; privacy policy on site

---

## 15) SLA & Scaling

- **App:** autoscale instances (HF GPU/CPU, or Vercel regions)
- **Data:** daily ETL; anomaly alerts on >3σ spikes in category deltas
- **Ops:** kill/scale rotation runs nightly; alert on checkout CR dips >20%

---

## 16) Deliverables (What you’ll see live)

- Working pipeline from demand → deployed app → agent & GPT wrapper → monetized site
- Dashboards: MoM by category, funnel performance, revenue by domain
- Playbooks to replicate the loop for new categories in hours

