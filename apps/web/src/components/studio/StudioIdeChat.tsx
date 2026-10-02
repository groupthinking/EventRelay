'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';

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
      className="flex h-full min-h-0 flex-col"
    >
      <div
        ref={messagesRef}
        data-testid="studio-ide-chat-messages"
        className="min-h-0 flex-1 overflow-y-auto px-3 py-3"
      >
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
            <p className="text-sm font-medium text-white/70">
              {canChat ? 'Ask about this pack' : 'Run a video to start chatting'}
            </p>
            <p className="max-w-[26ch] text-xs text-white/40">
              {canChat
                ? 'Grounded in the pack — events, lingo, tools, intent. No invented answers.'
                : 'Paste a YouTube URL above and hit Run.'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {messages.map((m) => (
              <div
                key={m.id}
                data-testid={m.role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant'}
                className={
                  m.role === 'user'
                    ? 'self-end rounded-lg bg-amber-500/15 px-3 py-2 text-sm text-amber-100'
                    : 'self-start rounded-lg bg-white/5 px-3 py-2 text-sm text-white/85'
                }
              >
                {m.content}
              </div>
            ))}
            {sending ? (
              <div className="self-start rounded-lg bg-white/5 px-3 py-2 text-sm text-white/40">
                Thinking…
              </div>
            ) : null}
          </div>
        )}
      </div>
      {quotaHit ? (
        <div className="border-t border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          Daily free limit reached.{' '}
          <a href="/pricing" className="font-semibold underline">
            Upgrade to Pro
          </a>{' '}
          for unlimited chat.
        </div>
      ) : null}
      {error && !sending ? (
        <div className="border-t border-white/10 px-3 py-1 text-xs text-red-300/80">{error}</div>
      ) : null}
      <form
        onSubmit={send}
        data-testid="studio-ide-chat-composer"
        className="border-t border-white/10 p-2"
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={canChat ? 'Ask about events, tools, intent…' : 'Run a video first'}
            disabled={!canChat || sending}
            aria-label="Chat message"
            data-testid="studio-ide-chat-input"
            className="min-w-0 flex-1 rounded-lg border border-white/15 bg-[#0b0c10] px-3 py-2 text-sm text-white outline-none placeholder:text-white/30 focus:border-amber-500/60 disabled:opacity-40"
          />
          <button
            type="submit"
            disabled={!canChat || sending || draft.trim().length === 0}
            data-testid="studio-ide-chat-send"
            className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-black disabled:opacity-40"
          >
            {sending ? '…' : 'Send'}
          </button>
        </div>
      </form>
    </section>
  );
}
