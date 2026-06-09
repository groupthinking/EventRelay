'use client';

import { RefObject, useCallback, useRef, useState } from 'react';

type RealtimeStatus = 'idle' | 'connecting' | 'connected' | 'muted' | 'error';

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
    const parsed = JSON.parse(value) as { error?: string; details?: string };
    const details = parsed.details ? JSON.parse(parsed.details) as { error?: { code?: string; message?: string } } : null;
    const code = details?.error?.code;
    const message = details?.error?.message || parsed.error;

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
      const peer = new RTCPeerConnection();
      peerRef.current = peer;

      peer.ontrack = (event) => {
        if (audioRef.current) {
          audioRef.current.srcObject = event.streams[0];
          audioRef.current.play().catch(() => undefined);
        }
        appendEvent('audio.output', 'Assistant audio connected.');
      };

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      stream.getAudioTracks().forEach((track) => peer.addTrack(track, stream));

      const channel = peer.createDataChannel('oai-events');
      channelRef.current = channel;
      channel.addEventListener('open', () => {
        setStatus('connected');
        configureSession();
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

      const response = await fetch('/api/realtime/session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/sdp',
        },
        body: offer.sdp,
      });

      const answerSdp = await response.text();
      if (!response.ok) {
        throw new Error(getFriendlyRealtimeError(answerSdp || `Realtime session failed with ${response.status}.`));
      }

      await peer.setRemoteDescription({ type: 'answer', sdp: answerSdp });
      appendEvent('session.connected', 'Voice input connected.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Voice input failed to start.';
      setError(message);
      setStatus('error');
      appendEvent('session.error', message);
      cleanupConnection();
    }
  }, [appendEvent, audioRef, cleanupConnection, configureSession, handleServerEvent, status]);

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
