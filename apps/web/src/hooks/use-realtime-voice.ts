'use client';

import { RefObject, useCallback, useRef, useState } from 'react';

type RealtimeStatus = 'idle' | 'connecting' | 'connected' | 'muted' | 'error';

const OPENAI_REALTIME_CALLS_URL = 'https://api.openai.com/v1/realtime/calls';
const REALTIME_CONNECTION_TIMEOUT_MS = 20_000;

export interface RealtimeEventLog {
  id: string;
  type: string;
  label: string;
  timestamp: string;
}

interface FunctionCallItem {
  type?: string;
  name?: string;
  call_id?: string;
  arguments?: string;
}

interface RealtimeServerEvent {
  type?: string;
  response?: {
    output?: FunctionCallItem[];
  };
}

interface RealtimeClientSecretResponse {
  value?: string;
  client_secret?: {
    value?: string;
  };
  error?: unknown;
  details?: unknown;
}

function makeLog(type: string, label: string): RealtimeEventLog {
  return {
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    type,
    label,
    timestamp: new Date().toISOString(),
  };
}

function parseJsonObject(value: string | undefined): Record<string, unknown> {
  if (!value) return {};
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function getFriendlyRealtimeError(value: string) {
  try {
    const parsed = JSON.parse(value) as { error?: string | { code?: string; message?: string }; details?: string | { error?: { code?: string; message?: string } } };
    const details = typeof parsed.details === 'string'
      ? JSON.parse(parsed.details) as { error?: { code?: string; message?: string } }
      : parsed.details;
    const parsedError = typeof parsed.error === 'object' ? parsed.error : null;
    const code = details?.error?.code || parsedError?.code;
    const message = details?.error?.message || parsedError?.message || (typeof parsed.error === 'string' ? parsed.error : null);

    if (code === 'insufficient_quota') {
      return 'Voice is wired correctly, but the OpenAI project behind OPENAI_API_KEY is out of quota or billing access.';
    }

    if (code === 'invalid_offer') {
      return 'Voice could not start because the browser did not provide a usable audio WebRTC offer.';
    }

    return message || value;
  } catch {
    return value;
  }
}

function getFriendlyStartError(err: unknown) {
  if (err instanceof DOMException) {
    if (err.name === 'NotAllowedError' || err.name === 'SecurityError') {
      return 'Microphone permission was blocked. Allow microphone access for this site and try voice again.';
    }

    if (err.name === 'NotFoundError') {
      return 'No microphone input device was found.';
    }

    if (err.name === 'NotReadableError') {
      return 'The microphone is already in use or cannot be read by the browser.';
    }
  }

  return err instanceof Error ? err.message : 'Voice input failed to start.';
}

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit, timeoutMs: number) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}

async function readRealtimeError(response: Response, fallback: string) {
  const body = await response.text();
  if (!body) return fallback;
  return getFriendlyRealtimeError(body);
}

function getClientSecret(data: RealtimeClientSecretResponse) {
  return data.value || data.client_secret?.value || '';
}

function waitForDataChannelOpen(channel: RTCDataChannel, peer: RTCPeerConnection, timeoutMs: number) {
  if (channel.readyState === 'open') return Promise.resolve();

  return new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      cleanup();
      reject(new Error('Voice connected to OpenAI, but the Realtime event channel did not open.'));
    }, timeoutMs);

    const cleanup = () => {
      window.clearTimeout(timeout);
      channel.removeEventListener('open', handleOpen);
      channel.removeEventListener('error', handleChannelError);
      peer.removeEventListener('connectionstatechange', handlePeerState);
    };

    const handleOpen = () => {
      cleanup();
      resolve();
    };

    const handleChannelError = () => {
      cleanup();
      reject(new Error('The Realtime event channel failed to open.'));
    };

    const handlePeerState = () => {
      if (peer.connectionState === 'failed' || peer.connectionState === 'closed') {
        cleanup();
        reject(new Error(`The Realtime WebRTC connection ${peer.connectionState}.`));
      }
    };

    channel.addEventListener('open', handleOpen);
    channel.addEventListener('error', handleChannelError);
    peer.addEventListener('connectionstatechange', handlePeerState);
  });
}

function checkCalendar(date: string, time: string) {
  const hour = Number.parseInt(time.split(':')[0] || '0', 10);
  const available = Number.isFinite(hour) ? hour >= 9 && hour < 17 && hour !== 12 : true;

  return {
    available,
    date,
    time,
    reason: available
      ? 'That review time is open.'
      : 'That time is outside the standard workflow review window.',
  };
}

export function useRealtimeVoice(audioRef: RefObject<HTMLAudioElement | null>) {
  const [status, setStatus] = useState<RealtimeStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<RealtimeEventLog[]>([]);

  const peerRef = useRef<RTCPeerConnection | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const channelRef = useRef<RTCDataChannel | null>(null);

  const appendEvent = useCallback((type: string, label: string) => {
    setEvents((current) => [makeLog(type, label), ...current].slice(0, 24));
  }, []);

  const sendEvent = useCallback((event: Record<string, unknown>) => {
    const channel = channelRef.current;
    if (!channel || channel.readyState !== 'open') return;
    channel.send(JSON.stringify(event));
  }, []);

  const configureSession = useCallback(() => {
    sendEvent({
      type: 'session.update',
      session: {
        type: 'realtime',
        model: 'gpt-realtime-2',
        instructions:
          'Help the user turn video evidence into safe workflows, plans, exports, and deployable app ideas. Ask short clarifying questions only when needed.',
        audio: {
          input: {
            turn_detection: {
              type: 'server_vad',
            },
          },
          output: {
            voice: 'marin',
          },
        },
        reasoning: {
          effort: 'low',
        },
        tools: [
          {
            type: 'function',
            name: 'check_calendar',
            description: 'Check whether a requested review or workflow handoff time is available.',
            parameters: {
              type: 'object',
              properties: {
                date: {
                  type: 'string',
                  description: 'Requested calendar date.',
                },
                time: {
                  type: 'string',
                  description: 'Requested time in 24-hour local time, such as 14:30.',
                },
              },
              required: ['date', 'time'],
              additionalProperties: false,
            },
          },
        ],
        tool_choice: 'auto',
      },
    });
    appendEvent('session.update', 'Voice input is ready.');
  }, [appendEvent, sendEvent]);

  const requestAudioReadyCheck = useCallback(() => {
    sendEvent({
      type: 'conversation.item.create',
      item: {
        type: 'message',
        role: 'user',
        content: [
          {
            type: 'input_text',
            text: 'Say one brief sentence confirming that UVAI voice is ready, then wait for my spoken request.',
          },
        ],
      },
    });
    sendEvent({ type: 'response.create' });
    appendEvent('response.create', 'Assistant audio check requested.');
  }, [appendEvent, sendEvent]);

  const handleFunctionCall = useCallback(
    (item: FunctionCallItem) => {
      if (item.type !== 'function_call' || item.name !== 'check_calendar' || !item.call_id) {
        return;
      }

      const args = parseJsonObject(item.arguments);
      const date = typeof args.date === 'string' ? args.date : new Date().toISOString().slice(0, 10);
      const time = typeof args.time === 'string' ? args.time : '10:00';
      const result = checkCalendar(date, time);

      sendEvent({
        type: 'conversation.item.create',
        item: {
          type: 'function_call_output',
          call_id: item.call_id,
          output: JSON.stringify(result),
        },
      });
      sendEvent({ type: 'response.create' });
      appendEvent('check_calendar', result.available ? 'Review time is available.' : 'Review time needs another slot.');
    },
    [appendEvent, sendEvent],
  );

  const handleServerEvent = useCallback(
    (event: RealtimeServerEvent) => {
      if (!event.type) return;

      if (event.type === 'response.done') {
        event.response?.output?.forEach(handleFunctionCall);
      }

      const readable =
        event.type === 'response.done'
          ? 'Assistant turn completed.'
          : event.type === 'error'
            ? 'Voice service returned an error.'
            : event.type.replaceAll('_', ' ');
      appendEvent(event.type, readable);
    },
    [appendEvent, handleFunctionCall],
  );

  const cleanupConnection = useCallback(() => {
    channelRef.current?.close();
    channelRef.current = null;

    peerRef.current?.close();
    peerRef.current = null;

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (audioRef.current) {
      audioRef.current.srcObject = null;
    }
  }, [audioRef]);

  const stop = useCallback(() => {
    cleanupConnection();

    setStatus('idle');
    appendEvent('session.closed', 'Voice input stopped.');
  }, [appendEvent, cleanupConnection]);

  const start = useCallback(async () => {
    if (status === 'connecting' || status === 'connected' || status === 'muted') return;

    setError(null);
    setStatus('connecting');
    appendEvent('session.start', 'Preparing voice input.');

    try {
      if (typeof RTCPeerConnection === 'undefined') {
        throw new Error('This browser does not support WebRTC voice sessions.');
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('This browser does not expose microphone input to the app.');
      }

      const tokenResponse = await fetchWithTimeout('/api/realtime/session', {
        method: 'GET',
        cache: 'no-store',
      }, REALTIME_CONNECTION_TIMEOUT_MS);

      if (!tokenResponse.ok) {
        throw new Error(await readRealtimeError(
          tokenResponse,
          `Realtime client secret creation failed with ${tokenResponse.status}.`,
        ));
      }

      const tokenData = await tokenResponse.json() as RealtimeClientSecretResponse;
      const clientSecret = getClientSecret(tokenData);
      if (!clientSecret) {
        throw new Error('Realtime client secret response did not include a usable token.');
      }
      appendEvent('session.secret', 'Realtime session token ready.');

      const peer = new RTCPeerConnection();
      peerRef.current = peer;
      peer.addEventListener('connectionstatechange', () => {
        if (peer.connectionState === 'failed') {
          setError('The Realtime WebRTC connection failed.');
          setStatus('error');
          appendEvent('connection.failed', 'Realtime WebRTC connection failed.');
          cleanupConnection();
        }
      });

      peer.ontrack = (event) => {
        if (audioRef.current) {
          audioRef.current.autoplay = true;
          audioRef.current.setAttribute('playsinline', 'true');
          audioRef.current.setAttribute('webkit-playsinline', 'true');
          audioRef.current.srcObject = event.streams[0];
          audioRef.current.play().catch(() => undefined);
        }
        appendEvent('audio.output', 'Assistant audio connected.');
      };

      appendEvent('audio.input', 'Requesting microphone access.');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      stream.getAudioTracks().forEach((track) => peer.addTrack(track, stream));
      appendEvent('audio.input', 'Microphone input connected.');

      const channel = peer.createDataChannel('oai-events');
      channelRef.current = channel;
      channel.addEventListener('open', () => {
        setStatus('connected');
        configureSession();
        requestAudioReadyCheck();
      });
      channel.addEventListener('message', (message) => {
        try {
          handleServerEvent(JSON.parse(message.data));
        } catch {
          appendEvent('message', 'Received a voice event.');
        }
      });
      channel.addEventListener('close', () => appendEvent('data.closed', 'Voice event channel closed.'));

      const offer = await peer.createOffer();
      await peer.setLocalDescription(offer);

      if (!offer.sdp) {
        throw new Error('The browser did not create a usable WebRTC SDP offer.');
      }

      const response = await fetchWithTimeout(OPENAI_REALTIME_CALLS_URL, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${clientSecret}`,
          'Content-Type': 'application/sdp',
        },
        body: offer.sdp,
      }, REALTIME_CONNECTION_TIMEOUT_MS);

      const answerSdp = await response.text();
      if (!response.ok) {
        throw new Error(getFriendlyRealtimeError(answerSdp || `Realtime session failed with ${response.status}.`));
      }

      await peer.setRemoteDescription({ type: 'answer', sdp: answerSdp });
      await waitForDataChannelOpen(channel, peer, REALTIME_CONNECTION_TIMEOUT_MS);
      appendEvent('session.connected', 'Voice input connected.');
    } catch (err) {
      const message = getFriendlyStartError(err);
      setError(message);
      setStatus('error');
      appendEvent('session.error', message);
      cleanupConnection();
    }
  }, [appendEvent, audioRef, cleanupConnection, configureSession, handleServerEvent, requestAudioReadyCheck, status]);

  const toggleMute = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;

    const shouldMute = status !== 'muted';
    stream.getAudioTracks().forEach((track) => {
      track.enabled = !shouldMute;
    });
    setStatus(shouldMute ? 'muted' : 'connected');
    appendEvent(shouldMute ? 'audio.muted' : 'audio.unmuted', shouldMute ? 'Voice input muted.' : 'Voice input resumed.');
  }, [appendEvent, status]);

  return {
    status,
    error,
    events,
    start,
    stop,
    disconnect: cleanupConnection,
    toggleMute,
    isActive: status === 'connected' || status === 'muted',
  };
}
