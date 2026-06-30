'use client';

import { useState, useEffect, useRef } from 'react';
import { clsx } from 'clsx';
import type { TraceStep, AgentNodeStatus, AgentRole } from '@/lib/agent-types';

// ── Helpers ──

const STATUS_STYLES: Record<AgentNodeStatus, { bg: string; text: string; dot: string; border: string }> = {
  idle:     { bg: 'bg-white/[0.02]', text: 'text-white/40', dot: 'bg-gray-500',    border: 'border-white/[0.05]' },
  pending:  { bg: 'bg-white/[0.03]', text: 'text-white/50', dot: 'bg-gray-400',    border: 'border-white/[0.08]' },
  running:  { bg: 'bg-indigo-500/[0.06]', text: 'text-indigo-400', dot: 'bg-indigo-400', border: 'border-indigo-500/20' },
  complete: { bg: 'bg-emerald-500/[0.06]', text: 'text-emerald-400', dot: 'bg-emerald-400', border: 'border-emerald-500/20' },
  error:    { bg: 'bg-red-500/[0.06]', text: 'text-red-400', dot: 'bg-red-400',    border: 'border-red-500/20' },
};

const ROLE_ICONS: Record<AgentRole, string> = {
  orchestrator:       '🎯',
  router:             '🔀',
  parallel_crew:      '⚡',
  transcript_analyst: '📝',
  visual_analyst:     '👁️',
  audio_analyst:      '🔊',
  action_generator:   '⚙️',
  quality_checker:    '🛡️',
};

function formatTime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '—';
  }
}

// ── Component ──

interface TracePanelProps {
  steps: TraceStep[];
  selectedAgentId: string | null;
  onSelectAgent: (id: string | null) => void;
  className?: string;
}

export default function TracePanel({
  steps,
  selectedAgentId,
  onSelectAgent,
  className,
}: TracePanelProps) {
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest trace step
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps.length]);

  const toggleExpand = (stepId: string) => {
    setExpandedStepId((prev) => (prev === stepId ? null : stepId));
  };

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex-none flex items-center justify-between px-5 py-4 border-b border-white/[0.05]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          <h3 className="text-sm font-bold text-white/70 uppercase tracking-wider">
            Execution Trace
          </h3>
        </div>
        <span className="text-xs text-white/30 font-mono">
          {steps.length} steps
        </span>
      </div>

      {/* Trace Steps */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {steps.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12 px-4">
            <div className="text-3xl mb-3 opacity-20">📋</div>
            <p className="text-white/30 text-sm">
              Trace steps will appear here as agents execute
            </p>
          </div>
        ) : (
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[22px] top-4 bottom-4 w-px bg-white/[0.06]" />

            {steps.map((step, index) => {
              const style = STATUS_STYLES[step.status];
              const isExpanded = expandedStepId === step.id;
              const isSelected = selectedAgentId === step.agentId;
              const isLatest = index === steps.length - 1;

              return (
                <div
                  key={step.id}
                  className={clsx(
                    'relative pl-11 pr-4 py-3 transition-all duration-200 cursor-pointer',
                    'hover:bg-white/[0.02]',
                    isSelected && 'bg-indigo-500/[0.04]',
                    isLatest && step.status === 'running' && 'animate-fade-in-up',
                  )}
                  onClick={() => {
                    onSelectAgent(step.agentId);
                    toggleExpand(step.id);
                  }}
                >
                  {/* Timeline dot */}
                  <div
                    className={clsx(
                      'absolute left-[16px] top-[18px] w-[13px] h-[13px] rounded-full border-2 border-[#0f0f1a] z-10',
                      style.dot,
                    )}
                  >
                    {step.status === 'running' && (
                      <span className="absolute inset-0 rounded-full bg-indigo-400 animate-ping opacity-50" />
                    )}
                  </div>

                  {/* Step content */}
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{ROLE_ICONS[step.agentRole] || '⚙️'}</span>
                      <span className="text-sm font-semibold text-white/80">
                        {step.agentName.length > 22
                          ? step.agentName.substring(0, 20) + '…'
                          : step.agentName}
                      </span>
                    </div>
                    <span className={clsx('text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md', style.bg, style.text, style.border, 'border')}>
                      {step.status}
                    </span>
                  </div>

                  {/* Timestamp + duration */}
                  <div className="flex items-center gap-3 text-[10px] text-white/30 font-mono">
                    <span>{formatTime(step.timestamp)}</span>
                    {step.durationMs !== undefined && (
                      <span className="text-amber-400/60">
                        {step.durationMs >= 1000
                          ? `${(step.durationMs / 1000).toFixed(1)}s`
                          : `${step.durationMs}ms`}
                      </span>
                    )}
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="mt-3 space-y-2 animate-scale-in">
                      {step.input && (
                        <div className="p-2.5 rounded-lg bg-blue-500/[0.05] border border-blue-500/10">
                          <div className="text-[10px] font-bold text-blue-400/70 uppercase tracking-wider mb-1">
                            Input
                          </div>
                          <p className="text-xs text-blue-300/60 font-mono leading-relaxed">
                            {step.input.preview}
                          </p>
                        </div>
                      )}
                      {step.output && (
                        <div className="p-2.5 rounded-lg bg-emerald-500/[0.05] border border-emerald-500/10">
                          <div className="text-[10px] font-bold text-emerald-400/70 uppercase tracking-wider mb-1">
                            Output
                          </div>
                          <p className="text-xs text-emerald-300/60 font-mono leading-relaxed">
                            {step.output.preview}
                          </p>
                        </div>
                      )}
                      {step.error && (
                        <div className="p-2.5 rounded-lg bg-red-500/[0.05] border border-red-500/10">
                          <div className="text-[10px] font-bold text-red-400/70 uppercase tracking-wider mb-1">
                            Error
                          </div>
                          <p className="text-xs text-red-300/60 font-mono">
                            {step.error}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
