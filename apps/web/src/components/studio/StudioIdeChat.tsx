'use client';

import {
  FormEvent,
  KeyboardEvent,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  ArrowUp,
  CheckCircle2,
  Circle,
  Loader2,
  Play,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { extractYouTubeId, formatSeconds, parseTimestampToSeconds } from '@/lib/timestamp';
import type { VideoPlanInterviewAnswers } from '@/lib/video-pack-plan';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

export type StudioIdeChatProps = {
  videoId: string | null;
  packId: string | null;
  disabled?: boolean;
  isWorking?: boolean;
  statusText?: string;
  activeStage?: string;
  videoTitle?: string | null;
  onSubmitUrl?: (url: string) => void;
  onSeek?: (seconds: number) => void;
};

const FREE_QUOTA_MESSAGE = 'Free plan includes 5 AI chat messages per day.';
const PLAN_FIELDS = ['useCase', 'trigger', 'tools', 'constraints', 'successSignal'] as const;
type PlanField = (typeof PLAN_FIELDS)[number];
type PlanInterviewDraft = Partial<VideoPlanInterviewAnswers>;
type PlanChatResponse = {
  answer?: string;
  requiresInterview?: boolean;
  interviewQuestions?: string[];
  provider?: string;
  planInterview?: unknown;
  [key: string]: unknown;
};

const EXTRACTION_TIMELINE_STEPS = [
  { id: 'pack', label: 'Pack identity' },
  { id: 'captions', label: 'Captions & audio' },
  { id: 'transcript', label: 'Building transcript' },
  { id: 'events', label: 'Extracting events & tasks' },
  { id: 'ready', label: 'Pack ready' },
] as const;

const SUGGESTED_PROMPTS = [
  {
    id: 'summarize',
    label: 'Summarize key steps & decisions',
    query: 'Summarize key steps & decisions',
    autoSend: true,
  },
  {
    id: 'stack',
    label: 'Extract tools, commands & stack',
    query: 'Extract tools, commands & stack',
    autoSend: true,
  },
  {
    id: 'spec',
    label: 'Turn this into an implementation spec',
    query: 'Plan a build from this Video Pack',
    autoSend: false,
    testId: 'studio-ide-chat-plan-prompt',
  },
] as const;

const YOUTUBE_URL_EXACT_RE =
  /^(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/\S+|youtu\.be\/\S+)$/i;
const YOUTUBE_URL_EMBEDDED_RE =
  /https?:\/\/(?:www\.|m\.)?(?:youtube\.com\/\S+|youtu\.be\/\S+)/i;

function extractChatYouTubeUrl(raw: string, allowEmbedded: boolean): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  if (YOUTUBE_URL_EXACT_RE.test(trimmed)) {
    const candidate = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
    const id = extractYouTubeId(candidate);
    return id ? `https://www.youtube.com/watch?v=${id}` : null;
  }

  if (allowEmbedded) {
    const match = YOUTUBE_URL_EMBEDDED_RE.exec(trimmed);
    if (match?.[0]) {
      const cleaned = match[0].replace(/[),.;!?]+$/, '');
      const id = extractYouTubeId(cleaned);
      return id ? `https://www.youtube.com/watch?v=${id}` : null;
    }
  }

  return null;
}

function resolveTimelineIndex(activeStage?: string): number {
  const stage = (activeStage ?? '').trim().toLowerCase();
  if (!stage) return 1;
  if (stage.includes('ready')) return 4;
  if (stage.includes('event')) return 3;
  if (stage.includes('transcript')) return 2;
  if (stage.includes('caption')) return 1;
  if (stage.includes('pack')) return 0;
  return 1;
}

function cleanVideoLabel(videoTitle: string | null | undefined, videoId: string | null): string {
  const title = videoTitle?.trim() ?? '';
  if (title && !/^analyzing:/i.test(title) && !/^https?:\/\//i.test(title)) {
    return title;
  }
  return videoId ? `YouTube · ${videoId}` : 'Paste a YouTube URL to start';
}

function parseTools(value: string): string[] {
  return value
    .split(',')
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
}

function normalizeInterviewKey(value: string): PlanField | null {
  const key = value.replace(/[^a-z]/gi, '').toLowerCase();
  if (key === 'usecase' || key === 'workflow' || key === 'objective') return 'useCase';
  if (key === 'trigger' || key === 'schedule') return 'trigger';
  if (key === 'tools' || key === 'integrations' || key === 'systems') return 'tools';
  if (key === 'constraints' || key === 'guardrails' || key === 'rules') return 'constraints';
  if (key === 'successsignal' || key === 'successmetric' || key === 'success') return 'successSignal';
  return null;
}

function parseStructuredInterviewAnswer(text: string): PlanInterviewDraft | null {
  const labelPattern =
    /(useCase|workflow|objective|trigger|schedule|tools|integrations|systems|constraints|guardrails|rules|successSignal|successMetric|success)\s*:/gi;
  const labelMatches = Array.from(text.matchAll(labelPattern));
  if (labelMatches.length > 0) {
    const fromLabels: PlanInterviewDraft = {};
    for (let index = 0; index < labelMatches.length; index += 1) {
      const current = labelMatches[index];
      const next = labelMatches[index + 1];
      if (!current || current.index == null) continue;
      const rawKey = current[1];
      const key = rawKey ? normalizeInterviewKey(rawKey) : null;
      if (!key) continue;
      const valueStart = current.index + current[0].length;
      const valueEnd = next?.index ?? text.length;
      const rawValue = text.slice(valueStart, valueEnd).trim().replace(/[|,;]+$/, '').trim();
      if (!rawValue) continue;
      if (key === 'tools') {
        fromLabels.tools = parseTools(rawValue);
      } else {
        fromLabels[key] = rawValue;
      }
    }
    if (Object.keys(fromLabels).length > 0) return fromLabels;
  }

  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  const fromLabels: PlanInterviewDraft = {};
  let matchedLabel = false;
  for (const line of lines) {
    const idx = line.indexOf(':');
    if (idx < 1) continue;
    const key = normalizeInterviewKey(line.slice(0, idx).trim());
    if (!key) continue;
    const rawValue = line.slice(idx + 1).trim();
    if (!rawValue) continue;
    matchedLabel = true;
    if (key === 'tools') {
      fromLabels.tools = parseTools(rawValue);
    } else {
      fromLabels[key] = rawValue;
    }
  }
  if (matchedLabel) return fromLabels;

  const parts = text
    .split('|')
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
  if (parts.length !== 5) return null;
  return {
    useCase: parts[0],
    trigger: parts[1],
    tools: parseTools(parts[2]),
    constraints: parts[3],
    successSignal: parts[4],
  };
}

function nextMissingInterviewField(interview: PlanInterviewDraft): PlanField | null {
  for (const field of PLAN_FIELDS) {
    if (field === 'tools') {
      if (!Array.isArray(interview.tools) || interview.tools.length === 0) return field;
      continue;
    }
    if (typeof interview[field] !== 'string' || interview[field]?.trim().length === 0) {
      return field;
    }
  }
  return null;
}

function mergeInterviewDraft(base: PlanInterviewDraft, patch: PlanInterviewDraft): PlanInterviewDraft {
  return {
    ...base,
    ...patch,
    ...(patch.tools ? { tools: patch.tools } : {}),
  };
}

function withSequentialAnswer(base: PlanInterviewDraft, answer: string): PlanInterviewDraft {
  const field = nextMissingInterviewField(base);
  if (!field) return base;
  const normalized = answer.trim();
  if (!normalized) return base;
  if (field === 'tools') {
    return { ...base, tools: parseTools(normalized) };
  }
  return { ...base, [field]: normalized };
}

function composeInterviewAssistantMessage(answer: string, questions: string[]): string {
  return [
    answer.trim(),
    '',
    ...questions.map((question, index) => `${index + 1}. ${question}`),
    '',
    'Reply in one message with:',
    'useCase: ...',
    'trigger: ...',
    'tools: tool1, tool2',
    'constraints: ...',
    'successSignal: ...',
  ].join('\n');
}

const TIMESTAMP_TOKEN_RE =
  /(\[(?:transcript|visual)\s+(\d{1,5})s\]|[[(]?\b((?:\d{1,2}:)?\d{1,2}:\d{2})\b[\])]?)/gi;

function parseMatchedSeconds(match: RegExpExecArray): { seconds: number; label: string } | null {
  if (match[2]) {
    const seconds = Number(match[2]);
    if (!Number.isFinite(seconds) || seconds < 0) return null;
    const prefix = match[1].toLowerCase().includes('visual') ? 'visual' : 'transcript';
    return { seconds, label: `${prefix} ${formatSeconds(seconds)}` };
  }
  if (match[3]) {
    const parts = match[3].split(':').map((n) => parseInt(n, 10));
    if (parts.some((n) => !Number.isFinite(n))) return null;
    const last = parts[parts.length - 1];
    const mid = parts.length === 3 ? parts[1] : undefined;
    if (last >= 60 || (mid !== undefined && mid >= 60)) return null;
    const seconds = parseTimestampToSeconds(match[3]);
    if (seconds === null) return null;
    return { seconds, label: match[3] };
  }
  return null;
}

function renderLineWithTimestampChips(
  line: string,
  onSeek: ((seconds: number) => void) | undefined,
  videoId: string | null,
  keyPrefix: string,
): ReactNode {
  const nodes: ReactNode[] = [];
  TIMESTAMP_TOKEN_RE.lastIndex = 0;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let chipIndex = 0;

  while ((match = TIMESTAMP_TOKEN_RE.exec(line)) !== null) {
    const fullMatch = match[0];
    const start = match.index;
    const prevChar = start > 0 ? line[start - 1] : '';
    const nextChar = line[start + fullMatch.length] ?? '';

    // Avoid tokenizing inside URLs or colon-delimited identifiers.
    if (prevChar === '/' || prevChar === ':' || nextChar === ':') {
      continue;
    }

    const parsed = parseMatchedSeconds(match);
    if (!parsed) continue;

    if (start > lastIndex) {
      nodes.push(line.slice(lastIndex, start));
    }

    const chipKey = `${keyPrefix}-ts-${chipIndex++}`;
    const safeVideoId =
      videoId && /^[A-Za-z0-9_-]{6,20}$/.test(videoId) ? encodeURIComponent(videoId) : null;
    if (onSeek) {
      nodes.push(
        <button
          key={chipKey}
          type="button"
          data-testid="chat-timestamp-chip"
          onClick={() => onSeek(parsed.seconds)}
          title={`Seek video to ${formatSeconds(parsed.seconds)}`}
          className="studio-ts-chip"
        >
          <Play size={10} aria-hidden="true" />
          <span>{parsed.label}</span>
        </button>,
      );
    } else if (safeVideoId) {
      nodes.push(
        <a
          key={chipKey}
          href={`https://www.youtube.com/watch?v=${safeVideoId}&t=${Math.floor(parsed.seconds)}s`}
          target="_blank"
          rel="noreferrer"
          data-testid="chat-timestamp-chip"
          title={`Open YouTube at ${formatSeconds(parsed.seconds)}`}
          className="studio-ts-chip"
        >
          <Play size={10} aria-hidden="true" />
          <span>{parsed.label}</span>
        </a>,
      );
    } else {
      nodes.push(
        <span key={chipKey} data-testid="chat-timestamp-chip" className="studio-ts-chip">
          {parsed.label}
        </span>,
      );
    }

    lastIndex = start + fullMatch.length;
  }

  if (lastIndex === 0) return line;
  if (lastIndex < line.length) {
    nodes.push(line.slice(lastIndex));
  }
  return nodes;
}

function AssistantProse({
  content,
  onSeek,
  videoId,
}: {
  content: string;
  onSeek?: (seconds: number) => void;
  videoId: string | null;
}) {
  const lines = useMemo(() => content.split(/\r?\n/), [content]);

  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={`sp-${index}`} className="h-1" aria-hidden="true" />;
        }
        const isTopHeading = index === 0 && lines.length > 2 && !trimmed.startsWith('-');
        return (
          <p
            key={`ln-${index}`}
            className={
              isTopHeading
                ? 'min-w-0 font-semibold text-[var(--uvai-ink)]'
                : 'min-w-0 text-[var(--uvai-ink-soft)]'
            }
          >
            {renderLineWithTimestampChips(line, onSeek, videoId, `ln-${index}`)}
          </p>
        );
      })}
    </div>
  );
}

/**
 * Antigravity-style full-height conversational pane for Studio.
 * Supports grounded pack Q&A, plan interviews, clickable timestamp chips,
 * live extraction progress timeline, and direct YouTube URL paste submission.
 */
export default function StudioIdeChat({
  videoId,
  packId,
  disabled,
  isWorking,
  statusText,
  activeStage,
  videoTitle,
  onSubmitUrl,
  onSeek,
}: StudioIdeChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [quotaHit, setQuotaHit] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [planInterviewQuestions, setPlanInterviewQuestions] = useState<string[] | null>(null);
  const [planInterviewDraft, setPlanInterviewDraft] = useState<PlanInterviewDraft>({});
  const messagesRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const idCounter = useRef(0);

  const isExtracting = Boolean(isWorking) || (Boolean(videoId) && Boolean(disabled));
  const canChat = Boolean(videoId) && !disabled && !isExtracting;
  const canSubmitUrlInChat = Boolean(onSubmitUrl) && !isExtracting;
  const composerEnabled = canChat || canSubmitUrlInChat;

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      const node = messagesRef.current;
      if (node) node.scrollTop = node.scrollHeight;
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending, isExtracting, scrollToBottom]);

  // Reset conversation when the selected video or pack changes.
  useEffect(() => {
    setMessages([]);
    setQuotaHit(false);
    setError(null);
    setPlanInterviewQuestions(null);
    setPlanInterviewDraft({});
  }, [videoId, packId]);

  // Clear stale chat error whenever a fresh extraction begins.
  useEffect(() => {
    if (isExtracting) {
      setError(null);
    }
  }, [isExtracting]);

  // Auto-grow composer textarea smoothly up to 144px.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    if (!draft) {
      el.style.height = '';
      return;
    }
    el.style.height = 'auto';
    if (el.scrollHeight > 0) {
      el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
    }
  }, [draft]);

  const clearConversation = useCallback(() => {
    setMessages([]);
    setQuotaHit(false);
    setError(null);
    setPlanInterviewQuestions(null);
    setPlanInterviewDraft({});
  }, []);

  const sendQuery = useCallback(
    async (rawQuery: string) => {
      const query = rawQuery.trim();
      if (!query || sending || isExtracting) return;

      // Support pasting a YouTube URL directly into the chat composer.
      if (onSubmitUrl) {
        const pastedUrl = extractChatYouTubeUrl(query, !videoId);
        if (pastedUrl) {
          setDraft('');
          setError(null);
          onSubmitUrl(pastedUrl);
          return;
        }
      }

      if (!videoId || disabled) {
        if (onSubmitUrl) {
          setError('Paste a valid YouTube link (youtube.com or youtu.be) to start analyzing.');
        }
        return;
      }

      const userMsg: ChatMessage = { id: `u-${idCounter.current++}`, role: 'user', content: query };
      setMessages((prev) => [...prev, userMsg]);
      setDraft('');
      setSending(true);
      setError(null);

      const history = [...messages, userMsg]
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }));

      try {
        const body: Record<string, unknown> = { query, history };
        if (videoId) body.video_id = videoId;
        if (packId) body.pack_id = packId;
        if (planInterviewQuestions) {
          const structured = parseStructuredInterviewAnswer(query);
          const draftPayload = structured
            ? mergeInterviewDraft(planInterviewDraft, structured)
            : withSequentialAnswer(planInterviewDraft, query);
          body.planIntent = true;
          body.planInterview = draftPayload;
        }

        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(30_000),
        });
        const data = (await res.json()) as PlanChatResponse;

        if (res.status === 402 && data.upgradeRequired) {
          setQuotaHit(true);
          setMessages((prev) => [
            ...prev,
            {
              id: `a-${idCounter.current++}`,
              role: 'assistant',
              content: data.answer || FREE_QUOTA_MESSAGE,
            },
          ]);
          return;
        }

        if (!res.ok) {
          const failure =
            typeof data.answer === 'string'
              ? data.answer
              : typeof data.error === 'string'
                ? data.error
                : `Chat failed (${res.status}).`;
          throw new Error(failure);
        }

        const interviewQuestions = Array.isArray(data.interviewQuestions)
          ? data.interviewQuestions.filter(
              (value): value is string => typeof value === 'string' && value.trim().length > 0,
            )
          : [];
        const assistantContent =
          data.requiresInterview && interviewQuestions.length > 0
            ? composeInterviewAssistantMessage(data.answer || '(empty response)', interviewQuestions)
            : data.answer || '(empty response)';

        setMessages((prev) => [
          ...prev,
          { id: `a-${idCounter.current++}`, role: 'assistant', content: assistantContent },
        ]);

        if (data.requiresInterview) {
          const structured = parseStructuredInterviewAnswer(query);
          const nextDraft = structured
            ? mergeInterviewDraft(planInterviewDraft, structured)
            : planInterviewQuestions
              ? withSequentialAnswer(planInterviewDraft, query)
              : planInterviewDraft;
          setPlanInterviewQuestions(interviewQuestions.length > 0 ? interviewQuestions : []);
          setPlanInterviewDraft(nextDraft);
        } else if (data.provider === 'video-pack-planner') {
          setPlanInterviewQuestions(null);
          setPlanInterviewDraft({});
        } else if (!data.requiresInterview) {
          setPlanInterviewQuestions(null);
        }
      } catch (err) {
        const text = err instanceof Error ? err.message : 'Chat failed.';
        setError(text);
        setMessages((prev) => [
          ...prev,
          { id: `a-${idCounter.current++}`, role: 'assistant', content: `Error: ${text}` },
        ]);
      } finally {
        setSending(false);
      }
    },
    [
      disabled,
      isExtracting,
      messages,
      onSubmitUrl,
      packId,
      planInterviewDraft,
      planInterviewQuestions,
      sending,
      videoId,
    ],
  );

  const send = (event?: FormEvent) => {
    event?.preventDefault();
    void sendQuery(draft);
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (draft.trim().length > 0) {
        void sendQuery(draft);
      }
    }
  };

  const timelineActiveIndex = resolveTimelineIndex(activeStage);
  const statusState = isExtracting
    ? 'working'
    : packId
      ? 'ready'
      : videoId
        ? 'loaded'
        : 'idle';
  const statusPillLabel = isExtracting
    ? 'Extracting'
    : packId
      ? 'Pack ready'
      : videoId
        ? 'Video loaded'
        : 'Idle';
  const contextLabel = cleanVideoLabel(videoTitle, videoId);

  return (
    <section
      aria-label="Pack chat"
      data-testid="studio-ide-chat"
      className="flex h-full min-h-0 min-w-0 flex-1 flex-col bg-[var(--uvai-bg)]"
    >
      {/* Antigravity Assistant Identity Header */}
      <header className="studio-chat-header" data-testid="studio-chat-header">
        <div className="flex min-w-0 flex-1 items-center gap-2.5">
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--uvai-accent-soft)] text-[var(--uvai-accent-ink)]"
            aria-hidden="true"
          >
            <Sparkles size={14} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-semibold text-[var(--uvai-ink)]">Studio Assistant</span>
              <span className="rounded bg-[var(--uvai-surface-warm)] px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider text-[var(--uvai-accent-ink)]">
                ASK UVAI
              </span>
            </div>
            <p className="truncate text-[11px] text-[var(--uvai-ink-faint)]" title={contextLabel}>
              {contextLabel}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <span
            data-testid="studio-chat-status-pill"
            data-state={statusState}
            className="studio-chat-status-pill"
          >
            {statusPillLabel}
          </span>
          {messages.length > 0 && !sending ? (
            <button
              type="button"
              onClick={clearConversation}
              aria-label="New conversation"
              data-testid="studio-ide-chat-clear"
              title="Clear conversation"
              className="inline-flex items-center gap-1 rounded-md border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-1 text-[11px] font-medium text-[var(--uvai-ink-soft)] transition-colors hover:border-[var(--uvai-border-strong)] hover:text-[var(--uvai-ink)]"
            >
              <RotateCcw size={11} aria-hidden="true" />
              <span>New</span>
            </button>
          ) : null}
        </div>
      </header>

      {/* Full-Height Message Stream */}
      <div
        ref={messagesRef}
        data-testid="studio-ide-chat-messages"
        className="flex min-h-0 min-w-0 flex-1 flex-col gap-4 overflow-y-auto overflow-x-hidden px-4 py-4"
      >
        {messages.length === 0 && !sending && !isExtracting ? (
          <div className="template-chat-welcome my-auto flex min-w-0 flex-col gap-4 py-2">
            <div className="flex min-w-0 flex-col gap-1.5">
              <h2 className="text-base font-semibold tracking-tight text-[var(--uvai-ink)]">
                {canChat ? 'Ask anything about this video' : 'Drop a YouTube link to begin'}
              </h2>
              <p className="text-xs leading-relaxed text-[var(--uvai-ink-soft)]">
                {canChat
                  ? 'Grounded in the pack — transcript, chapters, events, tools, and spec. No invented answers.'
                  : onSubmitUrl
                    ? 'Paste any YouTube URL below (or in the top bar) to extract tasks, code, specs, and interactive Q&A.'
                    : 'Paste a YouTube URL above and hit Analyze.'}
              </p>
            </div>

            {canChat ? (
              <div className="flex min-w-0 flex-col gap-2" aria-label="Suggested prompts">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt.id}
                    type="button"
                    data-testid={'testId' in prompt ? prompt.testId : `studio-chat-prompt-${prompt.id}`}
                    onClick={() => {
                      if (prompt.autoSend) {
                        void sendQuery(prompt.query);
                      } else {
                        setDraft(prompt.query);
                        inputRef.current?.focus();
                      }
                    }}
                    className="studio-chat-prompt-pill"
                  >
                    <span className="min-w-0 flex-1">{prompt.label}</span>
                    <ArrowUp size={13} className="shrink-0 rotate-45 text-[var(--uvai-ink-faint)]" aria-hidden="true" />
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : (
          <div className="flex min-w-0 flex-col gap-4">
            {messages.map((m) => (
              <div
                key={m.id}
                data-testid={m.role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant'}
                className={m.role === 'user' ? 'uvai-chat-user' : 'uvai-chat-assistant'}
              >
                {m.role === 'assistant' ? (
                  <AssistantProse content={m.content} onSeek={onSeek} videoId={videoId} />
                ) : (
                  m.content
                )}
              </div>
            ))}
            {sending ? (
              <div className="uvai-chat-assistant flex items-center gap-2 text-xs text-[var(--uvai-ink-faint)]">
                <Loader2 size={14} className="motion-safe:animate-spin" aria-hidden="true" />
                <span>Thinking…</span>
              </div>
            ) : null}
          </div>
        )}

        {/* Inline Live Extraction Timeline Card */}
        {isExtracting ? (
          <div
            data-testid="studio-chat-extraction-card"
            role="status"
            aria-live="polite"
            className="studio-chat-timeline flex flex-col gap-3"
          >
            <div className="flex min-w-0 items-start gap-2.5">
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[var(--uvai-accent-soft)] text-[var(--uvai-accent-ink)]">
                <Loader2 size={14} className="motion-safe:animate-spin" aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-[var(--uvai-ink)]">Extracting Video Pack…</p>
                <p className="mt-0.5 text-xs leading-relaxed text-[var(--uvai-ink-soft)]">
                  {statusText?.trim() ||
                    'Building transcript, chapters, events, and runnable specs. Chat unlocks automatically when ready.'}
                </p>
              </div>
            </div>
            <ol className="flex min-w-0 flex-col gap-1.5 border-t border-[var(--uvai-border)] pt-2.5">
              {EXTRACTION_TIMELINE_STEPS.map((step, index) => {
                const stepState =
                  index < timelineActiveIndex
                    ? 'done'
                    : index === timelineActiveIndex
                      ? 'active'
                      : 'pending';
                return (
                  <li
                    key={step.id}
                    data-step={step.id}
                    data-state={stepState}
                    className="flex min-w-0 items-center gap-2 text-xs"
                  >
                    {stepState === 'done' ? (
                      <CheckCircle2 size={13} className="shrink-0 text-[#1e9a80]" aria-hidden="true" />
                    ) : stepState === 'active' ? (
                      <Loader2
                        size={13}
                        className="shrink-0 text-[var(--uvai-accent-ink)] motion-safe:animate-spin"
                        aria-hidden="true"
                      />
                    ) : (
                      <Circle size={13} className="shrink-0 text-[var(--uvai-ink-faint)]" aria-hidden="true" />
                    )}
                    <span
                      className={
                        stepState === 'active'
                          ? 'min-w-0 font-medium text-[var(--uvai-ink)]'
                          : stepState === 'done'
                            ? 'min-w-0 text-[var(--uvai-ink-soft)]'
                            : 'min-w-0 text-[var(--uvai-ink-faint)]'
                      }
                    >
                      {step.label}
                    </span>
                  </li>
                );
              })}
            </ol>
          </div>
        ) : null}
      </div>

      {quotaHit ? (
        <div className="border-t border-[var(--uvai-warn-border)] bg-[var(--uvai-warn-bg)] px-4 py-2.5 text-xs text-[var(--uvai-warn-ink)]">
          Daily free limit reached.{' '}
          <a href="/pricing" className="font-semibold underline">
            Upgrade to Pro
          </a>{' '}
          for unlimited chat.
        </div>
      ) : null}

      {error && !sending && !isExtracting ? (
        <div
          role="alert"
          className="border-t border-[var(--uvai-danger-border)] bg-[var(--uvai-danger-bg)] px-4 py-1.5 text-xs text-[var(--uvai-danger-ink)]"
        >
          {error}
        </div>
      ) : null}

      {/* Pinned Antigravity Rounded Composer */}
      <form
        onSubmit={send}
        data-testid="studio-ide-chat-composer"
        className="template-chat-composer"
      >
        <div className="studio-chat-composer-box">
          <textarea
            id="studio-chat-input"
            name="studioChatMessage"
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleComposerKeyDown}
            placeholder={
              isExtracting
                ? 'Extracting video pack…'
                : canChat
                  ? 'Ask a question or paste a URL…'
                  : canSubmitUrlInChat
                    ? 'Paste a YouTube link…'
                    : 'Run a video first'
            }
            disabled={!composerEnabled || sending}
            aria-label="Chat message"
            data-testid="studio-ide-chat-input"
            rows={1}
            className="uvai-input min-w-0 flex-1 leading-snug disabled:opacity-40"
          />
          <button
            type="submit"
            disabled={!composerEnabled || sending || draft.trim().length === 0}
            data-testid="studio-ide-chat-send"
            aria-label={sending ? 'Sending message' : 'Send message'}
            className="template-send"
          >
            {sending ? '…' : <ArrowUp size={16} aria-hidden="true" />}
          </button>
        </div>
      </form>
    </section>
  );
}
