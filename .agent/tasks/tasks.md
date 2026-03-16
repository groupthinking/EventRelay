# UVAI Market Readiness Tasks

> Updated: 2026-03-16 | Priority: Ship demo → Monetize → Build moat

## Sprint 0: Course Correction (COMPLETED) <!-- id: 100 -->
- [x] Reality audit of entire codebase <!-- id: 101 -->
- [x] Research MCP landscape (gcloud-mcp, Cloudflare, Apigee, HN discussion) <!-- id: 102 -->
- [x] Verify Cloud Run backend is live (`uvai-backend-gpwz4wb5na-uc.a.run.app`) <!-- id: 103 -->
- [x] Verify frontend builds cleanly (Next.js, 14 routes, zero errors) <!-- id: 104 -->
- [x] Clean repo bloat (remove log files, add Chrome profiles to .gitignore) <!-- id: 105 -->
- [x] Push 3 pending commits to origin/main <!-- id: 106 -->
- [x] Create course-correction plan with market analysis <!-- id: 107 -->

## Sprint 1: Ship the Demo (This Week) <!-- id: 1 -->
- [x] Verify backend health endpoint works on Cloud Run <!-- id: 1a -->
- [ ] **Redeploy backend with latest code** (3 commits behind) <!-- id: 1b -->
- [ ] **Deploy frontend to Vercel** with `BACKEND_URL` env wired <!-- id: 1c -->
- [ ] Verify end-to-end: paste YouTube URL → see analysis in browser <!-- id: 1d -->
- [ ] Delete dead agent files (grok4, llama, a2a_remediation) <!-- id: 1e -->
- [ ] Remove Chrome profile directories from git history (1.1GB) <!-- id: 1f -->

## Sprint 2: Monetize (Next Week) <!-- id: 2 -->
- [ ] Wire NextAuth with Google OAuth (dependency already installed) <!-- id: 2a -->
- [ ] Set up Stripe Checkout ($19/month plan) <!-- id: 2b -->
- [ ] Build "My Analyses" persistence layer (Supabase) <!-- id: 2c -->
- [ ] Add usage limits (5 free analyses/month) <!-- id: 2d -->
- [ ] Wire pricing page to actual checkout flow <!-- id: 2e -->

## Sprint 3: Defensible Moat (Week 3) <!-- id: 3 -->
- [ ] Build UVAI Remote MCP Server (expose `analyze_video` tool) <!-- id: 3a -->
- [ ] Integrate Google Developer Knowledge MCP <!-- id: 3b -->
- [ ] Build evaluation benchmark (autoresearch pattern, 50 test videos) <!-- id: 3c -->
- [ ] Implement progressive tool discovery (O(1) context loading) <!-- id: 3d -->

## Sprint 4: Enterprise (Week 4) <!-- id: 4 -->
- [ ] API key management for enterprise users <!-- id: 4a -->
- [ ] Team workspaces <!-- id: 4b -->
- [ ] SSO integration <!-- id: 4c -->
- [ ] SLA documentation <!-- id: 4d -->

---

### Legacy Tasks (Cloud Consolidation)
- [ ] Update `.env` with Supabase Connection String <!-- id: 10 -->
- [ ] Externalize RabbitMQ/Redis (CloudAMQP/Upstash) <!-- id: 11 -->
- [ ] Verify Backend connection to Cloud DB <!-- id: 18 -->
- [ ] Verify Frontend connection to API <!-- id: 19 -->
