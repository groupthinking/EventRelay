# GitHub Actions CI/CD Implementation Plan
**Date:** December 22, 2024  
**Objective:** Automate MCP server and agent workflow testing  
**Timeline:** 3-4 weeks  
**Priority:** High

---

## Executive Summary

Implement comprehensive GitHub Actions automation for:
1. MCP server protocol testing
2. Agent workflow validation
3. Continuous integration checks
4. Automated deployment validation

**Expected Benefits:**
- Early detection of MCP protocol violations
- Automated regression testing for agent workflows
- Faster feedback loop for developers
- Improved code quality and reliability

---

## Phase 1: MCP Server Testing Framework (Week 1)

### Objective
Create robust testing infrastructure for MCP servers with JSON-RPC protocol validation

### Deliverables

#### 1.1 Test Framework Setup
**Files to Create:**
```
tests/mcp/
├── conftest.py                    # Pytest configuration and fixtures
├── helpers/
│   ├── __init__.py
│   ├── protocol_validator.py     # JSON-RPC protocol validation
│   ├── mcp_harness.py            # Test harness for MCP servers
│   └── mock_stdio.py             # Mock stdin/stdout for testing
└── test_servers/
    ├── test_github_mcp.py        # GitHub MCP server tests
    ├── test_workflow_mcp.py      # Workflow automation tests
    └── test_knowledge_mcp.py     # Knowledge management tests
```

#### 1.2 Protocol Validator (`protocol_validator.py`)
```python
"""JSON-RPC 2.0 protocol validator for MCP servers."""

class ProtocolValidator:
    """Validates MCP server JSON-RPC protocol compliance."""
    
    def validate_request(self, message: dict) -> tuple[bool, str]:
        """Validate JSON-RPC request format."""
        # Check required fields: jsonrpc, method, id
        # Validate version is "2.0"
        # Check params structure
        
    def validate_response(self, message: dict) -> tuple[bool, str]:
        """Validate JSON-RPC response format."""
        # Check required fields: jsonrpc, result/error, id
        # Validate error structure if present
        # Ensure no stdout pollution
```

#### 1.3 MCP Test Harness (`mcp_harness.py`)
```python
"""Test harness for MCP server process management."""

class MCPServerHarness:
    """Manages MCP server lifecycle for testing."""
    
    async def start_server(self, server_path: str) -> Process:
        """Start MCP server and verify initialization."""
        
    async def send_request(self, method: str, params: dict) -> dict:
        """Send JSON-RPC request and get response."""
        
    async def stop_server(self) -> None:
        """Gracefully shutdown MCP server."""
        
    def get_stdout_pollution(self) -> list[str]:
        """Detect non-protocol output on stdout."""
```

#### 1.4 Test Cases

**Basic Protocol Tests:**
```python
@pytest.mark.asyncio
async def test_server_initialization(mcp_harness):
    """Test server starts and responds to ping."""
    server = await mcp_harness.start_server("mcp-servers/github/server.js")
    response = await mcp_harness.send_request("ping", {})
    assert response["result"] == "pong"

@pytest.mark.asyncio
async def test_no_stdout_pollution(mcp_harness):
    """Verify stdout only contains JSON-RPC messages."""
    server = await mcp_harness.start_server("mcp-servers/github/server.js")
    pollution = mcp_harness.get_stdout_pollution()
    assert len(pollution) == 0, f"Found stdout pollution: {pollution}"

@pytest.mark.asyncio  
async def test_error_handling(mcp_harness):
    """Test proper JSON-RPC error responses."""
    server = await mcp_harness.start_server("mcp-servers/github/server.js")
    response = await mcp_harness.send_request("invalid_method", {})
    assert "error" in response
    assert response["error"]["code"] == -32601  # Method not found
```

**Integration Tests:**
```python
@pytest.mark.asyncio
async def test_github_list_repos(mcp_harness, mock_github_api):
    """Test GitHub MCP server lists repositories."""
    server = await mcp_harness.start_server("mcp-servers/github/server.js")
    response = await mcp_harness.send_request("list_repos", {"owner": "test"})
    assert response["result"]["repos"] is not None

@pytest.mark.asyncio
async def test_concurrent_requests(mcp_harness):
    """Test server handles concurrent requests."""
    server = await mcp_harness.start_server("mcp-servers/github/server.js")
    tasks = [
        mcp_harness.send_request("ping", {}) 
        for _ in range(10)
    ]
    responses = await asyncio.gather(*tasks)
    assert all(r["result"] == "pong" for r in responses)
```

### Success Criteria
- [ ] All 24 MCP servers can be started programmatically
- [ ] Protocol validator detects all common violations
- [ ] Test harness supports concurrent testing
- [ ] Zero stdout pollution detected in all servers
- [ ] 90%+ code coverage for test framework

### Timeline
- Days 1-2: Protocol validator and test harness
- Days 3-4: Basic protocol tests for all servers
- Day 5: Integration tests for critical servers

---

## Phase 2: Agent Workflow Testing (Week 2)

### Objective
Create end-to-end tests for agent workflows and orchestration

### Deliverables

#### 2.1 Workflow Test Structure
```
tests/agents/
├── conftest.py                    # Agent test fixtures
├── mocks/
│   ├── mock_youtube_api.py       # Mock YouTube API
│   ├── mock_openai_api.py        # Mock OpenAI API
│   ├── mock_gemini_api.py        # Mock Gemini API
│   └── test_data/                 # Test fixtures
│       ├── sample_video_data.json
│       └── sample_transcripts.json
└── workflows/
    ├── test_video_processing.py   # Video processing workflow
    ├── test_agent_coordination.py # Multi-agent coordination
    └── test_mcp_bridge.py         # MCP bridge communication
```

#### 2.2 Mock Infrastructure
```python
"""Mock external APIs for deterministic testing."""

class MockYouTubeAPI:
    """Mock YouTube Data API v3."""
    
    def get_video_details(self, video_id: str) -> dict:
        """Return fixture data for video."""
        return load_fixture(f"videos/{video_id}.json")
    
    def get_transcript(self, video_id: str) -> list[dict]:
        """Return fixture transcript."""
        return load_fixture(f"transcripts/{video_id}.json")

class MockOpenAI:
    """Mock OpenAI API for deterministic testing."""
    
    def chat_completions_create(self, **kwargs) -> dict:
        """Return deterministic response based on input."""
        prompt_hash = hash(kwargs["messages"])
        return load_cached_response(prompt_hash)
```

#### 2.3 Workflow Test Cases

**Video Processing Workflow:**
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_video_processing_e2e(mock_apis, test_video_id):
    """Test complete video processing workflow."""
    
    # Initialize workflow
    workflow = VideoProcessingWorkflow(mock_apis)
    
    # Process video
    result = await workflow.process_video(test_video_id)
    
    # Verify results
    assert result["status"] == "success"
    assert result["transcript"] is not None
    assert result["summary"] is not None
    assert result["markdown"] is not None

@pytest.mark.asyncio
async def test_error_recovery(mock_apis):
    """Test workflow recovers from API errors."""
    mock_apis.youtube.fail_next_request()
    
    workflow = VideoProcessingWorkflow(mock_apis)
    result = await workflow.process_video("test_video")
    
    # Should retry and succeed
    assert result["status"] == "success"
    assert result["retry_count"] > 0
```

**Agent Coordination:**
```python
@pytest.mark.asyncio
async def test_multi_agent_coordination(agent_orchestrator):
    """Test agents coordinate via MCP bridge."""
    
    # Start workflow requiring multiple agents
    result = await agent_orchestrator.execute_workflow({
        "workflow_type": "video_to_app",
        "video_id": "test_video"
    })
    
    # Verify agent coordination
    assert result["agents_used"] >= 3
    assert result["mcp_messages_exchanged"] > 10
    assert result["status"] == "success"
```

### Success Criteria
- [ ] All critical workflows have E2E tests
- [ ] Mock infrastructure covers all external APIs
- [ ] Tests run deterministically (no flakiness)
- [ ] Test execution time < 5 minutes
- [ ] 80%+ code coverage for workflows

### Timeline
- Days 1-2: Mock infrastructure setup
- Days 3-4: Video processing workflow tests
- Day 5: Agent coordination and MCP bridge tests

---

## Phase 3: GitHub Actions Integration (Week 3)

### Objective
Implement CI/CD pipeline with automated testing

### Deliverables

#### 3.1 Main CI Workflow (`.github/workflows/ci.yml`)
```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    name: Lint Code
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run Ruff
        run: |
          pip install ruff
          ruff check .
      
      - name: Run MyPy
        run: |
          pip install mypy
          mypy src/

  test-backend:
    name: Backend Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          cd projects/EventRelay
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests with coverage
        run: |
          cd projects/EventRelay
          pytest --cov=src --cov-report=xml --cov-report=term
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: backend

  test-mcp-servers:
    name: MCP Server Tests
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [22]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
          cache-dependency-path: 'mcp-servers/package-lock.json'
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd mcp-servers
          npm ci
          cd ..
          pip install -r requirements-test.txt
      
      - name: Run MCP protocol tests
        run: |
          pytest tests/mcp/ -v --cov=mcp-servers
      
      - name: Check for stdout pollution
        run: |
          pytest tests/mcp/ -v -k "pollution"

  test-frontend:
    name: Frontend Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
          cache-dependency-path: 'projects/EventRelay/frontend/package-lock.json'
      
      - name: Install dependencies
        run: |
          cd projects/EventRelay/frontend
          npm ci --legacy-peer-deps
      
      - name: Run tests
        run: |
          cd projects/EventRelay/frontend
          npm test -- --coverage
      
      - name: Build
        run: |
          cd projects/EventRelay/frontend
          npm run build

  test-workflows:
    name: Agent Workflow Tests
    runs-on: ubuntu-latest
    needs: [test-backend, test-mcp-servers]
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup environment
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run workflow integration tests
        run: |
          pytest tests/agents/ -v --maxfail=5
        env:
          YOUTUBE_API_KEY: ${{ secrets.TEST_YOUTUBE_API_KEY }}
          OPENAI_API_KEY: mock_key
          GEMINI_API_KEY: mock_key
```

#### 3.2 Deployment Workflow (`.github/workflows/deploy-staging.yml`)
```yaml
name: Deploy to Staging

on:
  push:
    branches: [develop]
  workflow_dispatch:

jobs:
  deploy:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [test-all]  # From ci.yml
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: |
          cd projects/EventRelay
          docker build -f Dockerfile.production -t eventrelay:staging .
      
      - name: Run health checks
        run: |
          docker run -d -p 8000:8000 eventrelay:staging
          sleep 5
          curl -f http://localhost:8000/health
          curl -f http://localhost:8000/ready
      
      - name: Deploy to staging
        run: |
          # Deployment commands here
          echo "Deploying to staging environment"
```

### Success Criteria
- [ ] All tests run on every PR
- [ ] Build status badges on README
- [ ] Coverage reports published
- [ ] Deployment automation working
- [ ] CI pipeline completes in < 10 minutes

### Timeline
- Days 1-2: Setup GitHub Actions workflows
- Days 3-4: Configure coverage and badges
- Day 5: Test and refine pipeline

---

## Phase 4: Documentation & Refinement (Week 4)

### Deliverables

#### 4.1 Documentation Updates
- [ ] Update README.md with CI status badges
- [ ] Create TESTING.md with test guidelines
- [ ] Document mock data creation process
- [ ] Add runbook for CI failures

#### 4.2 Performance Optimization
- [ ] Cache dependencies effectively
- [ ] Parallelize independent tests
- [ ] Reduce test execution time
- [ ] Optimize Docker builds

#### 4.3 Quality Gates
- [ ] Minimum 80% code coverage required
- [ ] No critical security issues
- [ ] All linting checks pass
- [ ] Build size limits enforced

---

## Success Metrics

### Code Quality
- Test Coverage: >80% (target: 85%)
- Linting Pass Rate: 100%
- Type Checking Pass Rate: >95%

### CI/CD Performance
- Pipeline Execution Time: <10 minutes
- Test Reliability: >99% (flakiness <1%)
- Deployment Success Rate: >95%

### Developer Experience
- PR Feedback Time: <15 minutes
- False Positive Rate: <5%
- Documentation Clarity: 4.5/5 rating

---

## Risk Mitigation

### Identified Risks

1. **Test Flakiness**
   - Mitigation: Use deterministic mocks, retry logic
   - Fallback: Isolate flaky tests, investigate separately

2. **Long Test Execution**
   - Mitigation: Parallelize, cache, optimize
   - Fallback: Split into fast/slow test suites

3. **External API Dependencies**
   - Mitigation: Mock all external calls
   - Fallback: Use recorded responses (VCR.py)

4. **Secrets Management**
   - Mitigation: Use GitHub Secrets, rotate regularly
   - Fallback: Environment-specific keys

---

## Resource Requirements

### Infrastructure
- GitHub Actions minutes: ~1000/month
- Codecov account (free tier)
- Optional: Datadog for monitoring

### Team Time
- Developer: 2-3 weeks implementation
- Code reviews: 1-2 days
- Testing & refinement: 3-5 days

---

## Next Steps

### Immediate (This Week)
1. Create test framework structure
2. Implement protocol validator
3. Write basic MCP server tests
4. Set up initial GitHub Actions workflow

### Short-term (Weeks 2-3)
1. Complete agent workflow tests
2. Add coverage reporting
3. Integrate with CI/CD
4. Deploy to staging

### Long-term (Month 2+)
1. Add performance benchmarks
2. Implement security scanning
3. Add visual regression testing
4. Create deployment automation

---

**Created:** December 22, 2024  
**Owner:** Engineering Team  
**Status:** Ready for Implementation  
**Priority:** High