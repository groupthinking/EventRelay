/* @vitest-environment jsdom */
import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useBuiltInAI } from '../use-builtin-ai';
import { checkCapabilities, summarizeTranscript, extractEventsLocal } from '@/lib/services/builtin-ai';

vi.mock('@/lib/services/builtin-ai', () => ({
  checkCapabilities: vi.fn(),
  summarizeTranscript: vi.fn(),
  extractEventsLocal: vi.fn(),
}));

describe('useBuiltInAI', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('should initialize with default false capabilities', async () => {
    // Prevent the promise from resolving immediately for this specific check
    let resolvePromise: (val: any) => void;
    const promise = new Promise(resolve => {
      resolvePromise = resolve;
    });
    (checkCapabilities as ReturnType<typeof vi.fn>).mockReturnValue(promise);

    const { result } = renderHook(() => useBuiltInAI());

    expect(result.current.available).toEqual({
      promptAPI: false,
      summarizerAPI: false,
    });
    expect(result.current.summarize).toBe(summarizeTranscript);
    expect(result.current.extractEvents).toBe(extractEventsLocal);

    // Resolve promise and wait for update to avoid act() warning
    await act(async () => {
      resolvePromise!({ promptAPI: false, summarizerAPI: false });
    });
  });

  it('should update capabilities when checkCapabilities resolves', async () => {
    (checkCapabilities as ReturnType<typeof vi.fn>).mockResolvedValue({
      promptAPI: true,
      summarizerAPI: true,
    });

    const { result } = renderHook(() => useBuiltInAI());

    await waitFor(() => {
      expect(result.current.available).toEqual({
        promptAPI: true,
        summarizerAPI: true,
      });
    });

    expect(checkCapabilities).toHaveBeenCalledTimes(1);
  });

  it('should handle checkCapabilities error gracefully by leaving capabilities false', async () => {
    // Mock console.error to prevent polluting test output if it logs
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    (checkCapabilities as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useBuiltInAI());

    // We wait a bit to ensure the promise rejection is processed
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(result.current.available).toEqual({
      promptAPI: false,
      summarizerAPI: false,
    });

    consoleSpy.mockRestore();
  });
});
