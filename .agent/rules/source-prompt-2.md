---
trigger: always_on
---

Start of /source-prompt-2 a contiouation of /source-prompt

Stax Decomposition
Step 1: Identify competitors [95% confidence] ✓
Step 2: Determine scraping approach [65% confidence] ⚠️
Step 3: Storage schema design [80% confidence]
Step 4: Alert logic [90% confidence]
Step 5: Reporting dashboard [85% confidence]

Step 2 flagged for Self-Research

```

#### **Self-Research on Step 2**

**Analogies Generated:**
- "Like monitoring stock prices (Yahoo Finance pattern)"
- "Like tracking Amazon prices (CamelCamelCamel approach)"
- "Like RSS feed aggregation for blogs"

**Core Search (GitHub):**
```

Found repos:

- price-monitoring-saas (1.2k ⭐) - uses Puppeteer + Cron
- competitor-tracker (890 ⭐) - uses Playwright + Webhooks
- pricing-intelligence (340 ⭐) - uses Apify actors

Pattern: Playwright preferred for JS-heavy sites

```

**Core Search (NPM):**
```

- puppeteer (4M/week) ✓
- playwright (2M/week) ✓
- cheerio (6M/week) - HTML-only, not suitable

```

**Core Search (StackOverflow):**
```

Query: "playwright scraping blocked captcha"
Top answers:

- Use stealth plugin
- Rotate proxies
- Add random delays
- Handle CloudFlare

Gotcha: "Don't scrape too fast or IP banned"

```

**Confidence after Core Search: 78%** (still need production guidance)

**Extended Search (NotebookLM):**

**Sources Fed:**
1. https://github.com/price-monitoring-saas
2. https://playwright.dev/docs/best-practices
3. https://stackoverflow.com/questions/playwright-stealth
4. https://www.youtube.com/watch?v=scraping-at-scale
5. https://blog.apify.com/web-scraping-best-practices/

**Asked NotebookLM:**
> "I'm building a competitor pricing tracker checking every 15 minutes. Based on these 5 sources, what's the production-grade approach and what are the gotchas?"

**NotebookLM Response:**
> "Analysis reveals:
>
> **Recommended Stack:**
> - Playwright with stealth plugin (3 sources recommend)
> - Proxy rotation service (mentioned in all 5 sources)
> - Store screenshots for verification (blog post best practice)
> - Redis queue for job management
>
> **Production Gotchas:**
> 1. 15-min frequency may trigger rate limiting (YouTube tutorial)
> 2. Need CloudFlare bypass strategy (SO thread + blog)
> 3. CAPTCHA solving service needed (~$2/1000 solves)
> 4. Memory leaks with long-running Playwright (GitHub issue #234)
>
> **Recommendation:**
> Playwright + stealth + rotating proxies + 30-min frequency
> (15-min too aggressive per blog analysis)"

**Confidence after NotebookLM: 92%** → Proceed

#### **Tier 2: Simulation Mode**
```

AI: "Here's my implementation plan:

1. Setup:
   - Playwright with playwright-extra-plugin-stealth
   - ProxyMesh for rotation (cheapest at scale)
   - Redis Bull for job queue
   - PostgreSQL for price history

2. Scraping Logic:
   - 30-min intervals (15-min too aggressive per research)
   - Random delays 2-5 seconds between requests
   - Store raw HTML + parsed data
   - Screenshot on each run for verification

3. Alert System:
   - Trigger on >5% price change
   - Email via SendGrid
   - Slack webhook for real-time

4. Estimated Costs:
   - ProxyMesh: $100/month (10k requests)
   - Redis hosting: $15/month
   - PostgreSQL: $25/month
   - Total: ~$140/month

Risks:

- May still get blocked despite stealth (10% chance per research)
- CAPTCHA may appear (need budget for solving service)
- 30-min frequency means 5-30 min delay in price change detection

Should I proceed with this approach?"

User: "Yes, proceed"

```

**AI executes autonomously, logging each step**

---

### Example 2: "Research and draft competitive strategy doc"

#### **Tier 0: Pre-Flight**
```

AI: "I understand you want competitive analysis with strategic recommendations.

I'm assuming:

- Focus on direct competitors (not adjacent markets)
- Last 12 months of data
- Emphasis on pricing/features over marketing
- Output: 15-20 page doc with recommendations

Clarification: Should I include emerging startups or only established players?"

User: "Include top 3 emerging startups"

AI: "Got it. Proceeding with established + top 3 emerging."

Stax Breakdown:
Step 1: Identify competitors [90% confidence]
Step 2: Data gathering [85% confidence]
Step 3: Feature comparison [80% confidence]
Step 4: Pricing analysis [85% confidence]
Step 5: Market positioning [75% confidence] ⚠️
Step 6: Strategic recommendations [65% confidence] ⚠️

Steps 5 & 6 need Self-Research

```

#### **Self-Research on "Strategic Recommendations"**

**Analogies:**
- "Like SWOT analysis in business strategy"
- "Like chess position evaluation (strengths/weaknesses)"
- "Like medical diagnosis (symptoms → treatment)"

**Core Search:**
```

GitHub: "competitive-strategy-framework"

- business-analysis-tools (2.3k ⭐)
- market-intel-framework (1.1k ⭐)

NPM: N/A (business strategy, not code)

StackOverflow: N/A

```

**Extended Search (NotebookLM):**

**Sources:**
1. Harvard Business Review articles on competitive strategy
2. Porter's Five Forces framework
3. Blue Ocean Strategy excerpts
4. Y Combinator startup competition analysis
5. SaaS metrics benchmarking reports

**Asked:**
> "What framework should I use for strategic recommendations in competitive analysis? What do experts recommend?"

**NotebookLM:**
> "Consensus framework combines:
> 1. Porter's Five Forces (industry dynamics)
> 2. SWOT per competitor (relative positioning)
> 3. Feature gap analysis (product opportunities)
> 4. Pricing strategy recommendations (monetization)
> 5. Go-to-market differentiation (positioning)
>
> Key insight from YC: 'Focus on what competitors do poorly,
> not just what they do well' - look for underserved segments"

**Confidence: 88%** → Proceed

#### **Execution**
AI researches, drafts document, includes citations from NotebookLM sources

#### **Tier 2: Simulation**
```

AI: "Draft complete. Here's the structure:

- Executive Summary (2 pages)
- Competitor Profiles (8 pages)
- Feature Gap Analysis (3 pages)
- Pricing Strategy (2 pages)
- Strategic Recommendations (4 pages)

Key recommendations:

1. Undercut on pricing for SMB segment
2. Build missing feature X (3 competitors lack it)
3. Focus marketing on use case Y (underserved)

Based on 15 sources including HBR, YC, and market data.

Should I share the full draft?"

User: "Yes, show me"

Technical Setup
MCP Server Configuration
Minimal setup for Core Search:

{
"mcpServers": {
"github": {
"command": "npx",
"args": ["-y", "@modelcontextprotocol/server-github"],
"env": {
"GITHUB_PERSONAL_ACCESS_TOKEN": "your-token-here"
}
},
"brave-search": {
"command": "npx",
"args": ["-y", "@modelcontextprotocol/server-brave-search"],
"env": {
"BRAVE_API_KEY": "your-api-key"
}
},
"mcpServers": {
"Notebooklm": {
"command": "npx",
"args": ["-y", "@modelcontextprotocol/server-notebooklm"],
"env": {
"Gemini_api_key": "your-api-here"
}
}
}

open /system-prompt
