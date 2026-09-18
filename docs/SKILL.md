# Event-Driven Pipeline Skill

## Description
Design and implementation patterns for data → action pipelines with event-driven architecture, enabling autonomous workflows across the UVAI ecosystem.

## When to Use This Skill
- Building data ingestion → processing → action workflows
- Creating reactive systems that respond to events
- Implementing async communication between UVAI components
- Designing scalable, decoupled architectures
- Setting up monitoring and alerting systems

## Core Pipeline Principles

### Data → Action Flow
```
Capture → Emit Event → Process → Transform → Trigger Action → Measure Outcome
```

### Event-Driven Architecture Rules
1. **Loose Coupling**: Components communicate via events, not direct calls
2. **Async Processing**: Events processed asynchronously for scalability
3. **Event Sourcing**: All state changes captured as events
4. **Idempotency**: Handlers process same event multiple times safely
5. **Measurability**: Every pipeline stage produces metrics

## Event Structure

### Standard Event Schema
```typescript
interface UVAIEvent {
  eventId: string;           // Unique identifier
  eventType: string;         // data.captured, task.completed, etc.
  timestamp: number;         // Unix timestamp in ms
  source: string;            // Component that emitted event
  correlationId?: string;    // For tracking related events
  payload: any;              // Event-specific data
  metadata: {
    version: string;
    schemaVersion: string;
    priority?: 'low' | 'normal' | 'high' | 'critical';
  };
}
```

### Event Naming Convention
```
<domain>.<entity>.<action>

Examples:
- youtube.video.captured
- mcp.server.connected
- executor.task.failed
- pipeline.stage.completed
- user.action.detected
```

## Pipeline Architecture Patterns

### 1. Simple Linear Pipeline
```typescript
// YouTube video → transcription → analysis → storage
const pipeline = new Pipeline()
  .stage('capture', captureYouTubeVideo)
  .stage('transcribe', transcribeVideo)
  .stage('analyze', analyzeContent)
  .stage('store', saveToDatabase)
  .onError(handlePipelineError)
  .onComplete(emitCompletionEvent);

await pipeline.execute(videoUrl);
```

### 2. Fan-Out Pattern
```typescript
// One event triggers multiple parallel actions
eventBus.on('data.captured', async (event) => {
  await Promise.all([
    processForAnalysis(event),
    storeInDatabase(event),
    notifySubscribers(event),
    updateMetrics(event)
  ]);
});
```

### 3. Fan-In Pattern
```typescript
// Multiple events trigger single action when all complete
const aggregator = new EventAggregator([
  'source1.data.ready',
  'source2.data.ready',
  'source3.data.ready'
]);

aggregator.whenAll(async (events) => {
  const combined = combineData(events);
  await processAggregatedData(combined);
});
```

### 4. Event Filtering & Routing
```typescript
// Route events to appropriate handlers based on criteria
eventBus
  .filter((e) => e.metadata.priority === 'critical')
  .subscribe(handleCriticalEvent);

eventBus
  .filter((e) => e.eventType.startsWith('youtube.'))
  .subscribe(handleYouTubeEvents);

eventBus
  .filter((e) => e.payload.value > threshold)
  .subscribe(handleHighValueEvents);
```

### 5. Event Transformation Chain
```typescript
// Transform events through multiple stages
const transformChain = eventBus
  .map(enrichWithMetadata)
  .filter(validateEvent)
  .map(normalizeFormat)
  .map(addCorrelationId)
  .subscribe(processTransformedEvent);
```

## Implementation with Anthropic Tools

### Event Bus with MCP Connector
```typescript
class UVAIEventBus {
  private mcpConnector: MCPConnector;

  async emit(event: UVAIEvent): Promise<void> {
    // Use MCP connector to broadcast to all subscribers
    await this.mcpConnector.broadcast('uvai.events', event);

    // Store in files API for event sourcing
    await filesAPI.append('event-log.jsonl', event);

    // Update metrics
    this.metrics.eventsEmitted++;
  }

  subscribe(
    eventType: string,
    handler: (event: UVAIEvent) => Promise<void>
  ): void {
    // Use MCP connector to receive events
    this.mcpConnector.on(eventType, async (event) => {
      try {
        await handler(event);
        this.metrics.eventsProcessed++;
      } catch (error) {
        await this.handleEventError(event, error);
      }
    });
  }
}
```

### Pipeline Orchestration with Sequential-Thinking
```typescript
class PipelineOrchestrator {
  async executePipeline(
    pipeline: Pipeline,
    input: any
  ): Promise<PipelineResult> {
    // Use sequential-thinking for pipeline planning
    const plan = await sequentialThinking({
      thought: 'Plan pipeline execution strategy',
      context: {
        stages: pipeline.stages,
        input: input,
        dependencies: pipeline.dependencies
      }
    });

    // Execute stages based on plan
    return await this.executeWithPlan(pipeline, plan);
  }
}
```

### Event Verification with Code Execution
```typescript
async verifyEventHandler(
  handler: EventHandler,
  sampleEvent: UVAIEvent
): Promise<boolean> {
  // Use code execution tool to test handler
  try {
    await codeExecution(() => handler(sampleEvent));
    return true;
  } catch (error) {
    console.error('Handler verification failed:', error);
    return false;
  }
}
```

### Event Sourcing with Files API
```typescript
class EventStore {
  async append(event: UVAIEvent): Promise<void> {
    // Store all events for replay capability
    await filesAPI.append('events.jsonl', JSON.stringify(event) + '\n');

    // Update indexes for fast querying
    await this.updateIndexes(event);
  }

  async replay(
    fromTimestamp: number,
    handler: (event: UVAIEvent) => Promise<void>
  ): Promise<void> {
    const events = await filesAPI.read('events.jsonl');
    const filtered = events
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line))
      .filter(e => e.timestamp >= fromTimestamp);

    for (const event of filtered) {
      await handler(event);
    }
  }
}
```

## Common Pipeline Patterns

### YouTube Video Processing Pipeline
```typescript
// Capture → Transcribe → Analyze → Extract Insights → Store → Notify
eventBus.on('youtube.video.discovered', async (event) => {
  const video = event.payload;

  // Stage 1: Download
  const downloaded = await downloadVideo(video.url);
  await eventBus.emit({
    eventType: 'youtube.video.downloaded',
    payload: downloaded
  });
});

eventBus.on('youtube.video.downloaded', async (event) => {
  // Stage 2: Transcribe
  const transcription = await transcribeVideo(event.payload);
  await eventBus.emit({
    eventType: 'youtube.video.transcribed',
    payload: transcription
  });
});

eventBus.on('youtube.video.transcribed', async (event) => {
  // Stage 3: Analyze
  const insights = await analyzeTranscription(event.payload);
  await eventBus.emit({
    eventType: 'youtube.video.analyzed',
    payload: insights
  });
});
```

### Self-Correcting Execution Pipeline
```typescript
eventBus.on('task.submitted', async (event) => {
  const result = await executor.execute(event.payload.task);

  if (result.success) {
    await eventBus.emit({
      eventType: 'task.completed',
      payload: result
    });
  } else {
    await eventBus.emit({
      eventType: 'task.failed',
      payload: { task: event.payload.task, error: result.error }
    });
  }
});

eventBus.on('task.failed', async (event) => {
  // Trigger self-correction
  const correction = await analyzeAndCorrect(event.payload);

  await eventBus.emit({
    eventType: 'task.retry',
    payload: correction.correctedTask
  });
});
```

### Data Ingestion → Action Pipeline
```typescript
// Multi-source data → consolidation → decision → action
eventBus.on('data.source1.received', storeInCache);
eventBus.on('data.source2.received', storeInCache);
eventBus.on('data.source3.received', storeInCache);

// When all sources received
aggregator.whenAll([
  'data.source1.received',
  'data.source2.received',
  'data.source3.received'
], async (events) => {
  const consolidated = consolidateData(events);

  await eventBus.emit({
    eventType: 'data.consolidated',
    payload: consolidated
  });
});

eventBus.on('data.consolidated', async (event) => {
  // Use sequential-thinking for decision making
  const decision = await makeDecision(event.payload);

  await eventBus.emit({
    eventType: 'action.triggered',
    payload: decision.action
  });
});

eventBus.on('action.triggered', executeAction);
```

## Error Handling & Resilience

### Dead Letter Queue
```typescript
class DeadLetterQueue {
  async handle(event: UVAIEvent, error: Error): Promise<void> {
    const dlqEvent = {
      ...event,
      error: {
        message: error.message,
        stack: error.stack,
        timestamp: Date.now()
      }
    };

    await filesAPI.append('dlq.jsonl', dlqEvent);

    // Emit for monitoring
    await eventBus.emit({
      eventType: 'pipeline.event.failed',
      payload: dlqEvent
    });
  }

  async retry(eventId: string): Promise<void> {
    const event = await this.loadFromDLQ(eventId);
    await eventBus.emit(event); // Retry processing
  }
}
```

### Circuit Breaker Pattern
```typescript
class CircuitBreaker {
  private failureCount = 0;
  private state: 'closed' | 'open' | 'half-open' = 'closed';

  async execute(fn: () => Promise<any>): Promise<any> {
    if (this.state === 'open') {
      throw new Error('Circuit breaker open');
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onFailure(): void {
    this.failureCount++;
    if (this.failureCount >= 5) {
      this.state = 'open';
      setTimeout(() => this.state = 'half-open', 60000);
    }
  }

  private onSuccess(): void {
    this.failureCount = 0;
    this.state = 'closed';
  }
}
```

### Retry with Exponential Backoff
```typescript
async function processWithRetry(
  event: UVAIEvent,
  handler: (e: UVAIEvent) => Promise<void>,
  maxAttempts = 3
): Promise<void> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      await handler(event);
      return;
    } catch (error) {
      if (attempt === maxAttempts) {
        await deadLetterQueue.handle(event, error);
        throw error;
      }
      await sleep(Math.pow(2, attempt) * 1000);
    }
  }
}
```

## Monitoring & Metrics

### Pipeline Observability
```typescript
interface PipelineMetrics {
  eventsEmitted: number;
  eventsProcessed: number;
  eventsFailed: number;
  averageProcessingTime: number;
  throughput: number; // events/second
  activeSubscribers: number;
  deadLetterQueueSize: number;
}

// Emit metrics periodically
setInterval(async () => {
  await eventBus.emit({
    eventType: 'metrics.pipeline.snapshot',
    payload: getCurrentMetrics()
  });
}, 60000);
```

### Event Tracing
```typescript
// Track event through entire pipeline
class EventTracer {
  async trace(correlationId: string): Promise<UVAIEvent[]> {
    const events = await eventStore.queryByCorrelationId(correlationId);

    return events.sort((a, b) => a.timestamp - b.timestamp);
  }

  async visualizePipeline(correlationId: string): Promise<string> {
    const events = await this.trace(correlationId);

    return events
      .map(e => `${e.timestamp}: ${e.eventType} (${e.source})`)
      .join('\n');
  }
}
```

## Testing Strategies

### Event Handler Testing
```typescript
describe('Event Handlers', () => {
  it('should process youtube.video.captured event', async () => {
    const event: UVAIEvent = {
      eventId: 'test-123',
      eventType: 'youtube.video.captured',
      timestamp: Date.now(),
      source: 'test',
      payload: { videoId: 'abc123' }
    };

    await handler(event);

    expect(mockEventBus.emit).toHaveBeenCalledWith(
      expect.objectContaining({
        eventType: 'youtube.video.downloaded'
      })
    );
  });
});
```

### Pipeline Integration Testing
```bash
# Test complete pipeline flow
npm test -- --integration --pipeline=youtube-processing
pytest tests/integration/test_pipelines.py -v
```

## Allowed Tools
- MCP connector (for event bus implementation)
- sequential-thinking (for pipeline orchestration)
- files API (for event sourcing and logging)
- code execution (for handler verification)
- Bash (for testing and monitoring)
- Read, Write, Edit (for pipeline configuration)

## Success Criteria
- Events flow through pipeline successfully
- All handlers idempotent and error-tolerant
- Metrics captured at every stage
- Dead letter queue handles failures gracefully
- Event replay capability functional
- Throughput meets performance requirements
- Full observability and tracing implemented
- Zero data loss during failures
