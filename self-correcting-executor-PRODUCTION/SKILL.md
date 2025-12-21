# Self-Correcting Executor Skill

## Description
Implementation patterns for building executors that automatically detect failures, analyze root causes, and apply corrections autonomously - core to UVAI's "own the loop" methodology.

## When to Use This Skill
- Building automated task execution systems
- Implementing CI/CD pipelines with auto-remediation
- Creating resilient data processing workflows
- Developing agents that learn from failures
- Any system requiring high reliability and autonomous recovery

## Core Principles

### Execution Loop Pattern
```
Execute → Measure → Detect Failure → Analyze → Correct → Re-Execute → Verify
```

### Self-Correction Requirements
1. **Measurable Outcomes**: Every execution produces verifiable metrics
2. **Failure Detection**: Automated identification of error conditions
3. **Root Cause Analysis**: Systematic investigation using sequential-thinking
4. **Correction Strategies**: Predefined and learned remediation patterns
5. **Verification**: Post-correction validation before marking success

## Implementation Architecture

### Basic Executor Structure
```typescript
interface ExecutionResult {
  success: boolean;
  output?: any;
  error?: Error;
  metrics: {
    duration: number;
    resourceUsage: number;
    attemptNumber: number;
  };
  correctionApplied?: string;
}

class SelfCorrectingExecutor {
  async execute(task: Task, maxAttempts = 3): Promise<ExecutionResult> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const result = await this.tryExecute(task, attempt);

      if (result.success) {
        await this.recordSuccess(task, result);
        return result;
      }

      lastError = result.error!;
      const correction = await this.analyzeAndCorrect(task, result);

      if (!correction.possible) {
        break;
      }

      task = correction.correctedTask;
    }

    return this.handleFinalFailure(task, lastError!);
  }

  private async analyzeAndCorrect(
    task: Task,
    result: ExecutionResult
  ): Promise<Correction> {
    // Use sequential-thinking for root cause analysis
    const analysis = await this.rootCauseAnalysis(result.error);

    // Apply correction strategy
    const strategy = this.selectCorrectionStrategy(analysis);

    // Modify task for retry
    return strategy.apply(task, analysis);
  }
}
```

### Correction Strategy Patterns

#### 1. Dependency Resolution
```typescript
// Missing dependency detected → Install and retry
if (error.includes('MODULE_NOT_FOUND')) {
  await exec(`npm install ${extractPackageName(error)}`);
  return { possible: true, correctedTask: task };
}
```

#### 2. Configuration Adjustment
```typescript
// Invalid config → Validate and adjust
if (error.includes('INVALID_CONFIG')) {
  const validConfig = await this.validateAndFixConfig(task.config);
  task.config = validConfig;
  return { possible: true, correctedTask: task };
}
```

#### 3. Resource Availability
```typescript
// Resource unavailable → Wait and retry with backoff
if (error.includes('ECONNREFUSED') || error.includes('TIMEOUT')) {
  await sleep(Math.pow(2, attemptNumber) * 1000);
  return { possible: true, correctedTask: task };
}
```

#### 4. Permission Issues
```typescript
// Permission denied → Adjust file permissions
if (error.includes('EACCES') || error.includes('EPERM')) {
  await exec(`chmod +x ${task.targetFile}`);
  return { possible: true, correctedTask: task };
}
```

#### 5. Code Syntax Errors
```typescript
// Syntax error → Use code execution to validate fix
if (error.includes('SyntaxError')) {
  const fixed = await this.autoFixSyntax(task.code);
  task.code = fixed;
  return { possible: true, correctedTask: task };
}
```

## Integration with Anthropic Tools

### Sequential-Thinking for Analysis
```typescript
async rootCauseAnalysis(error: Error): Promise<Analysis> {
  // Use sequential-thinking tool for structured error analysis
  const analysis = await sequentialThinking({
    thought: `Analyze error: ${error.message}`,
    context: {
      stackTrace: error.stack,
      environment: process.env,
      previousAttempts: this.history
    }
  });

  return {
    rootCause: analysis.conclusion,
    correctionStrategy: analysis.recommendation,
    confidence: analysis.confidence
  };
}
```

### Code Execution for Verification
```typescript
async verifyCorrection(correctedTask: Task): Promise<boolean> {
  // Use code execution tool to verify fix before actual retry
  try {
    await codeExecution(correctedTask.code);
    return true;
  } catch (error) {
    return false;
  }
}
```

### Files API for Pattern Learning
```typescript
async recordCorrectionPattern(
  error: string,
  correction: Correction,
  success: boolean
): Promise<void> {
  // Store successful correction patterns for future use
  const pattern = {
    errorPattern: error,
    correctionApplied: correction,
    success: success,
    timestamp: Date.now()
  };

  await filesAPI.append('correction-patterns.json', pattern);
}
```

### MCP Connector for External Remediation
```typescript
async triggerExternalRemediation(error: Error): Promise<void> {
  // Use MCP connector to call external remediation services
  await mcpConnector.call('remediation-service', {
    tool: 'auto-heal',
    params: { error: error.message }
  });
}
```

## Advanced Patterns

### Multi-Stage Correction Pipeline
```typescript
const correctionPipeline = [
  this.tryQuickFix,
  this.tryDependencyResolution,
  this.tryConfigurationAdjustment,
  this.tryEnvironmentFix,
  this.tryCodeRewrite,
  this.escalateToHuman
];

for (const strategy of correctionPipeline) {
  const result = await strategy(task, error);
  if (result.success) return result;
}
```

### Learning from Patterns
```typescript
async selectCorrectionStrategy(analysis: Analysis): Promise<Strategy> {
  // Query files API for similar past errors
  const patterns = await filesAPI.read('correction-patterns.json');

  const similar = patterns.filter(p =>
    similarity(p.errorPattern, analysis.error) > 0.8
  );

  if (similar.length > 0) {
    // Use proven correction from history
    return similar.sort((a, b) => b.success - a.success)[0].correction;
  }

  // Analyze new error with sequential-thinking
  return await this.deriveNewStrategy(analysis);
}
```

### Parallel Correction Attempts
```typescript
async tryMultipleCorrectionsConcurrently(
  task: Task,
  error: Error
): Promise<ExecutionResult> {
  const strategies = this.getCandidateStrategies(error);

  // Try all strategies in parallel
  const results = await Promise.allSettled(
    strategies.map(s => s.apply(task).then(t => this.tryExecute(t)))
  );

  // Return first successful result
  const success = results.find(r => r.status === 'fulfilled' && r.value.success);

  if (success) {
    await this.recordWinningStrategy(success);
    return success.value;
  }

  return { success: false, error };
}
```

## Measurement & Monitoring

### Execution Metrics
```typescript
interface ExecutorMetrics {
  totalExecutions: number;
  successRate: number;
  averageAttempts: number;
  correctionSuccessRate: number;
  mostCommonErrors: Map<string, number>;
  mostEffectiveCorrections: Map<string, number>;
  averageTimeToCorrection: number;
}
```

### Real-Time Monitoring
```typescript
// Emit events for UVAI pipeline monitoring
executor.on('execution-start', (task) => {
  emitEvent('uvai.executor.start', { taskId: task.id });
});

executor.on('correction-applied', (correction) => {
  emitEvent('uvai.executor.correction', {
    type: correction.type,
    confidence: correction.confidence
  });
});

executor.on('execution-complete', (result) => {
  emitEvent('uvai.executor.complete', {
    success: result.success,
    attempts: result.metrics.attemptNumber
  });
});
```

## Testing Strategy

### Unit Tests for Correction Strategies
```typescript
describe('SelfCorrectingExecutor', () => {
  it('should resolve missing dependencies', async () => {
    const task = createTask({ requiresMissingPackage: true });
    const result = await executor.execute(task);

    expect(result.success).toBe(true);
    expect(result.correctionApplied).toBe('dependency-resolution');
  });

  it('should retry with backoff on network errors', async () => {
    const task = createTask({ networkUnstable: true });
    const result = await executor.execute(task, 3);

    expect(result.metrics.attemptNumber).toBeGreaterThan(1);
    expect(result.success).toBe(true);
  });
});
```

### Integration Tests
```bash
# Test full correction pipeline with real failures
npm test -- --integration
pytest tests/integration/test_executor.py --verbose
```

## Common Correction Patterns Library

### File System Issues
- Missing directories → Create with proper permissions
- File not found → Check paths, create if needed
- Permission denied → Adjust chmod/chown

### Network Issues
- Connection refused → Retry with exponential backoff
- Timeout → Increase timeout, check service health
- DNS errors → Verify connectivity, use IP fallback

### Dependency Issues
- Module not found → Install from package manager
- Version conflict → Update to compatible versions
- Missing binaries → Install system dependencies

### Configuration Issues
- Invalid JSON → Parse error location, auto-fix
- Missing required fields → Add defaults
- Type mismatches → Convert to expected types

### Code Issues
- Syntax errors → Use linter suggestions
- Type errors → Add type assertions/casts
- Runtime errors → Add null checks, validation

## Allowed Tools
- sequential-thinking (for root cause analysis)
- code execution (for verification)
- files API (for pattern storage and learning)
- MCP connector (for external remediation)
- Bash (for system-level corrections)
- Read, Write, Edit (for code modifications)

## Success Criteria
- Success rate > 90% with corrections applied
- Average attempts to success < 2
- Correction patterns accumulate and improve over time
- Root cause analysis accurate and actionable
- No infinite retry loops
- Human escalation only for truly unsolvable issues
- Full audit trail of all correction attempts
