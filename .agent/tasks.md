# Production Readiness & Verify Task List

- [-] **Phase 1: Discovery & Analysis** <!-- id: 1 -->
  - [-] Map repository structure and identify key components (Backend, Frontend, Infra). <!-- id: 2 -->
  - [-] Analyze build system and dependencies (`pyproject.toml`, `package.json`, `Dockerfile`). <!-- id: 3 -->
  - [-] Identify external services and configuration requirements. <!-- id: 4 -->
- [-] **Phase 2: Bootstrap & Local Run** <!-- id: 5 -->
  - [-] Attempt standard installation and startup. <!-- id: 6 -->
  - [-] Document failures and required fixes. <!-- id: 7 -->
- [-] **Phase 3: Deep Dive (Security, Data, Obs)** <!-- id: 8 -->
  - [-] Scan for security vulnerabilities and hardcoded secrets. <!-- id: 9 -->
  - [-] Verify database migrations and data layer health. <!-- id: 10 -->
  - [-] Evaluate logging, metrics, and observability. <!-- id: 11 -->
- [-] **Phase 4: Synthesis & Reporting** <!-- id: 12 -->
  - [-] Compile "It runs" checklist. <!-- id: 13 -->
  - [-] Identify Blockers and Production Gaps. <!-- id: 14 -->
  - [-] Create detailed Implementation Plan. <!-- id: 15 -->
- [-] **Phase 5: Verification** <!-- id: 16 -->
  - [-] Create reproduction script/test case for critical paths. <!-- id: 17 -->
  - [-] Execute verification to ensure reliability. <!-- id: 18 -->
