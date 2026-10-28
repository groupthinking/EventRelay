'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUp, Sparkles } from 'lucide-react';

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

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();

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
        throw new Error(data.answer || data.error || `Chat failed (${res.status}).`);
      }

      setMessages((prev) => [
        ...prev,
        { id: `a-${idCounter.current++}`, role: 'assistant', content: data.answer || '(empty response)' },
      ]);
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
              {canChat ? 'Ask about this pack' : 'Run a video to start chatting'}
            </p>
            <p className="max-w-[30ch] text-xs text-slate-500">
              {canChat
                ? 'Grounded in the pack — events, lingo, tools, intent. No invented answers.'
                : 'Paste a YouTube URL above and hit Run.'}
            </p>
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
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={canChat ? 'Ask about events, tools, intent…' : 'Run a video first'}
            disabled={!canChat || sending}
            aria-label="Chat message"
            data-testid="studio-ide-chat-input"
            className="uvai-input min-w-0 flex-1 disabled:opacity-40"
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
