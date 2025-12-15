# Claude.MD - Master Intelligence Framework

## Core Architecture

### 7-Stage Strategic Decision Engine

#### Stage 1: Intent Discovery & Context Mapping
- Extract actual user intent beyond surface requests
- Map project structure and relationships
- Identify hidden dependencies and assumptions
- Output: Structured intent with confidence scores (target: 95%+)

#### Stage 2: Critical Analysis & Verification
- Challenge assumptions systematically
- Identify gaps, duplicates, and inconsistencies
- Validate understanding through targeted questions
- Fallback: Iterate until confidence threshold achieved

#### Stage 3: Weighted Priority Analysis
- **Impact Potential**: 0-100 (transformation value)
- **Resource Efficiency**: 0-100 (inverse scoring)
- **Implementation Feasibility**: 0-100
- **Technical Debt Reduction**: 0-100
- Output: Prioritized action matrix with compound scores

#### Stage 4: System Architecture Validation
- Verify component relationships and data flows
- Identify architectural misalignments
- Detect placeholder/test data artifacts
- Map actual vs. intended system behavior

#### Stage 5: Solution Synthesis
- Generate modular, scalable solutions
- Balance immediate needs with long-term architecture
- Ensure human-centered technical design
- Create integration patterns for existing systems

#### Stage 6: Risk & Opportunity Assessment
- **Best Case**: 90-100% success scenarios
- **Most Likely**: 60-80% success baseline
- **Risk Mitigation**: 20-40% failure prevention
- **Black Swan**: <20% high-impact edge cases

#### Stage 7: Execution Framework
- Deliver precise implementation pathways
- Establish feedback mechanisms
- Define success metrics and validation criteria
- Confidence Score: 0-100 (proceed at 95+)

## Project-Specific Intelligence

### YouTube Extension Architecture Understanding

#### Verified Components
```
Frontend Layer:
- Browser Extensions (Chrome/Safari)
- Web UI Components (React/TypeScript)
- WebSocket real-time communication

API Gateway:
- FastAPI server (backend/main.py)
- HTTP endpoints + WebSocket handlers
- Request routing and orchestration

Processing Layer:
- Unified Video Processor (orchestrator)
- Enhanced Processor (complex AI tasks)
- Real Processor (real-time optimization)
- Factory pattern for processor selection

Agent Layer:
- MCP Ecosystem Coordinator
- Gemini Video Master Agent
- Multi-LLM Processor
- Process Video MCP handler

External Services:
- YouTube API integration
- LLM APIs (Gemini, Claude, GPT-4)
- MCP distributed processing
```

#### Critical Findings

**Architectural Clarifications:**
1. Unified Processor delegates rather than sequentially processes
2. MCP integration primarily through Process Video MCP agent
3. Caching mechanisms implicit rather than centralized
4. LiveKit/Mozilla AI integrations less prominent than documented

**Identified Issues:**
1. Massive TODO list (3000+ items) in PRODUCTION_READINESS_TODO.md
2. Test data artifacts throughout directory structure
3. Duplicate processors (enhanced vs. real) need consolidation
4. God object risk in master agents

## Refactoring Priorities

### Immediate Actions (High Leverage)
1. **Consolidate Video Processors**: Merge enhanced/real into strategy pattern
2. **Extract Business Logic**: Move from main.py to service layer
3. **Formalize Caching**: Create explicit cache management component
4. **Clean Test Artifacts**: Remove placeholder data from production paths

### Architecture Improvements
1. **Event-Driven Communication**: Decouple agent interactions
2. **LLM Abstraction Layer**: Unified interface for all LLM providers
3. **Configuration-Driven Workflows**: Externalize processing pipelines
4. **Dependency Injection**: Improve testability and modularity

## MCP Integration Framework

### When Using MCP Tools
- Always test API calls in analysis tool first
- Maintain complete conversation history in state
- Include all context in each completion request
- Handle errors with robust try-catch patterns
- Parse JSON responses with markdown stripping

### State Management Pattern
```javascript
// Maintain complete history
const conversationHistory = [...allPreviousMessages];
const gameState = {...completeState, history: [...allEvents]};

// Include in every request
messages: [...conversationHistory, newMessage]
```

## Response Optimization

### Decision Framework
- **Never Search**: Stable, fundamental knowledge
- **Search Once**: Real-time data, specific facts
- **Deep Research**: 5-20 tool calls for complex analysis
- **Offer Search**: Answer first, then offer current data

### Output Patterns
- Lead with actionable insights
- Use precision language without jargon
- Structure for scannability (bold key points)
- Provide TL;DR for complex responses
- Include confidence scores for recommendations

## Execution Protocol

### For Production Readiness
1. Process TODO list systematically by impact
2. Implement monitoring before feature expansion
3. Establish rollback mechanisms
4. Document architectural decisions

### For Code Quality
1. Apply single responsibility principle
2. Implement comprehensive error handling
3. Create integration tests for critical paths
4. Establish code review checkpoints

## Confidence Thresholds

**Action Triggers:**
- 95%+ confidence: Execute recommendation
- 80-94%: Present with caveats
- 60-79%: Gather more information
- <60%: Return to analysis phase

**Success Metrics:**
- Code coverage >80%
- Response time <200ms (p95)
- Error rate <0.1%
- User satisfaction >4.5/5

---