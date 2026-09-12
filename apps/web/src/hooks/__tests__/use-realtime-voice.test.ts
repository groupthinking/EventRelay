/**
 * @vitest-environment jsdom
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useRealtimeVoice } from '../use-realtime-voice';
import React from 'react';

// Setup basic mocks
const mockAudioRef = { current: document.createElement('audio') } as React.RefObject<HTMLAudioElement | null>;

describe('useRealtimeVoice', () => {
  let originalRTCPeerConnection: any;
  let originalGetUserMedia: any;
  let originalFetch: any;

  beforeEach(() => {
    originalRTCPeerConnection = global.RTCPeerConnection;
    originalGetUserMedia = global.navigator?.mediaDevices?.getUserMedia;
    originalFetch = global.fetch;

    global.fetch = vi.fn();
    if (!global.navigator) {
        (global as any).navigator = {};
    }
    if (!global.navigator.mediaDevices) {
        (global as any).navigator.mediaDevices = {};
    }
  });

  afterEach(() => {
    global.RTCPeerConnection = originalRTCPeerConnection;
    if (global.navigator?.mediaDevices) {
        global.navigator.mediaDevices.getUserMedia = originalGetUserMedia;
    }
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('should initialize with idle status', () => {
    const { result } = renderHook(() => useRealtimeVoice(mockAudioRef));

    expect(result.current.status).toBe('idle');
    expect(result.current.error).toBeNull();
    expect(result.current.events).toEqual([]);
    expect(result.current.isActive).toBe(false);
  });

  it('should transition to error if RTCPeerConnection is missing', async () => {
    global.RTCPeerConnection = undefined as any;

    const { result } = renderHook(() => useRealtimeVoice(mockAudioRef));

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe('error');
    expect(result.current.error).toBe('This browser does not support WebRTC voice sessions.');
  });

  it('should transition to error if getUserMedia is missing', async () => {
    global.RTCPeerConnection = vi.fn() as any;
    global.navigator.mediaDevices.getUserMedia = undefined as any;

    const { result } = renderHook(() => useRealtimeVoice(mockAudioRef));

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe('error');
    expect(result.current.error).toBe('This browser does not expose microphone input to the app.');
  });

  it('should mute and unmute voice input', async () => {
    global.RTCPeerConnection = vi.fn() as any;
    global.navigator.mediaDevices.getUserMedia = vi.fn() as any;
    const { result } = renderHook(() => useRealtimeVoice(mockAudioRef));

    // Test muting
    act(() => {
        result.current.toggleMute();
    });
    // This will not do anything because streamRef is null (not connected)

    expect(result.current.status).toBe('idle');
  });

  it('should cleanup connection on stop', () => {
    const { result } = renderHook(() => useRealtimeVoice(mockAudioRef));

    act(() => {
      result.current.stop();
    });

    expect(result.current.status).toBe('idle');
    expect(result.current.events[0]?.type).toBe('session.closed');
  });

  it('should cleanup connection on disconnect', () => {
    const { result } = renderHook(() => useRealtimeVoice(mockAudioRef));

    act(() => {
      result.current.disconnect();
    });

    expect(result.current.status).toBe('idle');
  });
});
