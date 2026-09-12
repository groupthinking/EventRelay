import { describe, expect, it } from 'vitest';
import {
  maxDuration,
  MAX_DURATION_MS,
  PIPELINE_HEALTH_TIMEOUT_MS,
  PIPELINE_BACKEND_TIMEOUT_MS,
  PIPELINE_GEMINI_TIMEOUT_MS,
  PIPELINE_RESPONSE_BUFFER_MS,
  PipelineDeadline,
} from '../route';

describe('Pipeline API Constants', () => {
  it('should have correct timeout constants', () => {
    // Basic constants
    expect(maxDuration).toBe(60);
    expect(MAX_DURATION_MS).toBe(60000);

    // Check specific pipeline timeout values
    expect(PIPELINE_BACKEND_TIMEOUT_MS).toBe(25000);
    expect(PIPELINE_GEMINI_TIMEOUT_MS).toBe(15000);
    expect(PIPELINE_RESPONSE_BUFFER_MS).toBe(2000);

    // Ensure that backend timeout is strictly less than the total available duration
    // keeping in mind some buffer needed
    expect(PIPELINE_BACKEND_TIMEOUT_MS).toBeLessThan(MAX_DURATION_MS);
    expect(PIPELINE_GEMINI_TIMEOUT_MS).toBeLessThan(MAX_DURATION_MS);

    // Verify HEALTH timeout is exported
    expect(PIPELINE_HEALTH_TIMEOUT_MS).toBeDefined();
    expect(typeof PIPELINE_HEALTH_TIMEOUT_MS).toBe('number');
  });
});

describe('PipelineDeadline', () => {
  it('should initialize correctly with fromMaxDuration', () => {
    const deadline = PipelineDeadline.fromMaxDuration();
    expect(deadline).toBeInstanceOf(PipelineDeadline);
    // Since MAX_DURATION_MS is 60000, deadline.endsAt should be around Date.now() + 60000
    // We can't access private endsAt, but we can check remainingMs()
    const remaining = deadline.remainingMs();
    expect(remaining).toBeGreaterThan(0);
    expect(remaining).toBeLessThanOrEqual(MAX_DURATION_MS);
  });

  it('remainingMs calculates correctly', () => {
    const endsAt = Date.now() + 5000;
    const deadline = new (PipelineDeadline as any)(endsAt);

    // Allow slight delay due to test execution time
    expect(deadline.remainingMs()).toBeGreaterThan(4900);
    expect(deadline.remainingMs()).toBeLessThanOrEqual(5000);
  });

  it('remainingMs never returns negative', () => {
    const endsAt = Date.now() - 5000;
    const deadline = new (PipelineDeadline as any)(endsAt);
    expect(deadline.remainingMs()).toBe(0);
  });

  it('budgetMs caps at remaining time', () => {
    const endsAt = Date.now() + 5000;
    const deadline = new (PipelineDeadline as any)(endsAt);

    expect(deadline.budgetMs(2000)).toBe(2000); // requested is less than remaining
    expect(deadline.budgetMs(10000)).toBeLessThanOrEqual(5000); // requested is more than remaining
    expect(deadline.budgetMs(10000)).toBeGreaterThan(4900);
  });

  it('signalFor returns an AbortSignal that aborts after the budget', async () => {
    const endsAt = Date.now() + 500;
    const deadline = new (PipelineDeadline as any)(endsAt);

    // Request a signal that should timeout after 200ms
    const signal = deadline.signalFor(200);
    expect(signal).toBeInstanceOf(AbortSignal);
    expect(signal.aborted).toBe(false);

    // Wait for 300ms
    await new Promise(resolve => setTimeout(resolve, 300));

    expect(signal.aborted).toBe(true);
  });

  it('runWithBudget successfully completes a promise', async () => {
    const endsAt = Date.now() + 5000;
    const deadline = new (PipelineDeadline as any)(endsAt);

    const result = await deadline.runWithBudget(
      Promise.resolve('success'),
      1000,
      'Test operation'
    );

    expect(result).toBe('success');
  });

  it('runWithBudget rejects if promise takes too long', async () => {
    const endsAt = Date.now() + 5000;
    const deadline = new (PipelineDeadline as any)(endsAt);

    const slowPromise = new Promise(resolve => setTimeout(() => resolve('done'), 1000));

    await expect(
      deadline.runWithBudget(slowPromise, 100, 'Test timeout')
    ).rejects.toThrow('Test timeout timed out');
  });
});
