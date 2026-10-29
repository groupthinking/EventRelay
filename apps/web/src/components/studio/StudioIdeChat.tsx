'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUp, Sparkles } from 'lucide-react';
import type { VideoPlanInterviewAnswers } from '@/lib/video-pack-plan';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

type StudioIdeChatProps = {
  videoId: string | null;
  packId: string | null;
  disabled?: boolean;
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

/**
 * Center-pane chat for the Studio IDE. Wired to the real POST /api/chat
 * endpoint with pack grounding (video_id), not a stub. Free tier gets
 * 5 messages/day; the API returns 402 with upgradeRequired when exceeded.
 *
 * Styled in the locked light card system (DESIGN_LANGUAGE.md).
 */
export default function StudioIdeChat({ videoId, packId, disabled }: StudioIdeChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [quotaHit, setQuotaHit] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [planInterviewQuestions, setPlanInterviewQuestions] = useState<string[] | null>(null);
  const [planInterviewDraft, setPlanInterviewDraft] = useState<PlanInterviewDraft>({});
  const messagesRef = useRef<HTMLDivElement>(null);
  const idCounter = useRef(0);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      const node = messagesRef.current;
      if (node) node.scrollTop = node.scrollHeight;
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Reset conversation when the pack changes.
  useEffect(() => {
    setMessages([]);
    setQuotaHit(false);
    setError(null);
    setPlanInterviewQuestions(null);
    setPlanInterviewDraft({});
  }, [videoId, packId]);

  const send = async (event?: FormEvent) => {
    event?.preventDefault();
    const query = draft.trim();
    if (!query || sending || disabled) return;

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
        ? data.interviewQuestions.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
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
  };

  const canChat = Boolean(videoId) && !disabled;

  return (
    <section
      aria-label="Pack chat"
      data-testid="studio-ide-chat"
      className="flex h-full min-h-0 flex-col bg-white"
    >
      <div
        ref={messagesRef}
        data-testid="studio-ide-chat-messages"
        className="min-h-0 flex-1 overflow-y-auto px-4 py-4"
      >
        {messages.length === 0 ? (
          <div className="uvai-empty template-chat-welcome">
            <div className="template-mark" aria-hidden="true"><Sparkles size={24} /></div>
            <p className="text-sm font-semibold text-slate-700">
              {canChat ? 'Ask about this pack or plan a build' : 'Run a video to start chatting'}
            </p>
            <p className="max-w-[30ch] text-xs text-slate-500">
              {canChat
                ? 'Grounded in the pack — events, lingo, tools, intent. No invented answers.'
                : 'Paste a YouTube URL above and hit Run.'}
            </p>
            {canChat ? (
              <button
                type="button"
                onClick={() => setDraft('Plan a build from this Video Pack')}
                data-testid="studio-ide-chat-plan-prompt"
                className="text-xs font-semibold text-blue-700 underline"
              >
                Plan a build from this video
              </button>
            ) : null}
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {messages.map((m) => (
              <div
                key={m.id}
                data-testid={m.role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant'}
                className={m.role === 'user' ? 'uvai-chat-user' : 'uvai-chat-assistant'}
              >
                {m.content}
              </div>
            ))}
            {sending ? (
              <div className="uvai-chat-assistant text-slate-400">Thinking…</div>
            ) : null}
          </div>
        )}
      </div>
      {quotaHit ? (
        <div className="border-t border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800">
          Daily free limit reached.{' '}
          <a href="/pricing" className="font-semibold underline">
            Upgrade to Pro
          </a>{' '}
          for unlimited chat.
        </div>
      ) : null}
      {error && !sending ? (
        <div className="border-t border-red-100 bg-red-50 px-4 py-1.5 text-xs text-red-700">{error}</div>
      ) : null}
      <form
        onSubmit={send}
        data-testid="studio-ide-chat-composer"
        className="template-chat-composer p-4"
      >
        <div className="template-source-input">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={canChat ? 'Ask about this pack or plan a build…' : 'Run a video first'}
            disabled={!canChat || sending}
            aria-label="Chat message"
            data-testid="studio-ide-chat-input"
            rows={3}
            className="uvai-input min-w-0 flex-1 resize-y disabled:opacity-40"
          />
          <button
            type="submit"
            disabled={!canChat || sending || draft.trim().length === 0}
            data-testid="studio-ide-chat-send"
            aria-label={sending ? "Sending message" : "Send message"}
            className="template-send"
          >
            {sending ? '…' : <ArrowUp size={18} aria-hidden="true" />}
          </button>
        </div>
      </form>
    </section>
  );
}
