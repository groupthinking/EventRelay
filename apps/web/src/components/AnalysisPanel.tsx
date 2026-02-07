'use client';

import { useState, useRef, useEffect } from 'react';
import { clsx } from 'clsx';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AnalysisPanelProps {
  videoId: string;
  videoUrl: string;
  initialContext?: string;
  onClose?: () => void;
}

export default function AnalysisPanel({
  videoId,
  videoUrl,
  initialContext,
  onClose
}: AnalysisPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hello! I've analyzed this video. You can ask me anything about its content, extracted actions, or specific details. How can I help you today?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Logic to call backend chat/ask endpoint
      // For now, simulating a response. In production, this would call /api/v1/chat or similar.
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_id: videoId,
          video_url: videoUrl,
          query: input,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        })
      });

      if (!response.ok) throw new Error('Failed to get answer');

      const data = await response.json();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.answer || "I'm sorry, I couldn't find an answer to that.",
        timestamp: new Date()
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: "I encountered an error while trying to answer your question. Please try again.",
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-900/50 backdrop-blur-xl border-l border-white/[0.08] animate-slide-in-right">
      {/* Header */}
      <div className="p-4 border-b border-white/[0.08] flex items-center justify-between bg-surface-900/80">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary-500 flex items-center justify-center">
            <span className="text-lg">🤖</span>
          </div>
          <div>
            <h3 className="font-bold text-sm">Video Assistant</h3>
            <p className="text-[10px] text-green-400 font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              Online
            </p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/5 rounded-lg text-white/40 hover:text-white transition-colors"
          >
            ✕
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={clsx(
              "flex flex-col max-w-[85%] animate-fade-in-up",
              msg.role === 'user' ? "ml-auto items-end" : "items-start"
            )}
          >
            <div
              className={clsx(
                "px-4 py-3 rounded-2xl text-sm leading-relaxed",
                msg.role === 'user'
                  ? "bg-primary-500 text-white rounded-tr-none shadow-lg shadow-primary-500/10"
                  : "bg-white/[0.05] text-white/90 border border-white/[0.05] rounded-tl-none"
              )}
            >
              {msg.content}
            </div>
            <span className="text-[10px] text-white/20 mt-1 px-1">
              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        ))}
        {isLoading && (
          <div className="flex flex-col items-start max-w-[85%] animate-fade-in-up">
            <div className="px-4 py-3 rounded-2xl bg-white/[0.05] border border-white/[0.05] rounded-tl-none">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 bg-surface-900/80 border-t border-white/[0.08]">
        <form onSubmit={handleSendMessage} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about the video..."
            className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 pr-12 text-sm focus:outline-none focus:border-primary-500/50 transition-all placeholder:text-white/20"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-1.5 p-1.5 rounded-lg bg-primary-500 text-white hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          </button>
        </form>
        <p className="text-[10px] text-white/20 text-center mt-3">
          Powered by Gemini 2.0 • Multimodal Video Intelligence
        </p>
      </div>
    </div>
  );
}
