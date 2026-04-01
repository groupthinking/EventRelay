'use client';

import { useState, useEffect, useRef } from 'react';

/* ═══════════════════════════════════════════
   Real-time SSE Pipeline Progress UI
   Shows step-by-step live progress view
   with animated stage indicators
   ═══════════════════════════════════════════ */

export interface PipelineStage {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  progress: number;
  duration?: number;
  detail?: string;
}

interface PipelineProgressProps {
  stages: PipelineStage[];
  overallProgress: number;
  status: 'idle' | 'validating' | 'processing' | 'complete' | 'error';
  videoTitle?: string;
  startedAt?: string;
  className?: string;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function StageRow({ stage, index }: { stage: PipelineStage; index: number }) {
  const isRunning = stage.status === 'running';
  const isComplete = stage.status === 'complete';
  const isError = stage.status === 'error';
  const isPending = stage.status === 'pending';

  return (
    <div
      className="flex items-center gap-4 py-3 px-4 rounded-lg transition-all duration-500"
      style={{
        background: isRunning
          ? 'rgba(106, 242, 222, 0.04)'
          : isComplete
          ? 'rgba(34, 197, 94, 0.03)'
          : isError
          ? 'rgba(239, 68, 68, 0.04)'
          : 'transparent',
        borderLeft: isRunning
          ? '2px solid #6af2de'
          : isComplete
          ? '2px solid #22c55e'
          : isError
          ? '2px solid #ef4444'
          : '2px solid transparent',
      }}
    >
      {/* Status indicator */}
      <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
        {isComplete && (
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#22c55e"
            strokeWidth="2.5"
          >
            <path d="M20 6L9 17l-5-5" />
          </svg>
        )}
        {isRunning && (
          <div className="relative">
            <span className="absolute inline-flex h-4 w-4 rounded-full opacity-40 animate-ping" style={{ background: '#6af2de' }} />
            <span className="relative inline-flex h-3 w-3 rounded-full" style={{ background: '#6af2de' }} />
          </div>
        )}
        {isError && (
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#ef4444"
            strokeWidth="2.5"
          >
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        )}
        {isPending && (
          <div
            className="w-2.5 h-2.5 rounded-full"
            style={{ background: 'rgba(248, 245, 253, 0.15)' }}
          />
        )}
      </div>

      {/* Stage label */}
      <div className="flex-1 min-w-0">
        <div
          className="text-sm font-medium truncate"
          style={{
            color: isRunning
              ? '#6af2de'
              : isComplete
              ? '#22c55e'
              : isError
              ? '#ef4444'
              : 'rgba(248, 245, 253, 0.35)',
          }}
        >
          {stage.label}
        </div>
        {stage.detail && (isRunning || isComplete) && (
          <div
            className="text-xs mt-0.5 truncate"
            style={{ color: 'rgba(248, 245, 253, 0.3)' }}
          >
            {stage.detail}
          </div>
        )}
      </div>

      {/* Progress / Duration */}
      <div className="flex-shrink-0 flex items-center gap-3">
        {isRunning && (
          <div className="w-20 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(25, 25, 31, 0.8)' }}>
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${stage.progress}%`,
                background: 'linear-gradient(90deg, #6af2de, #38fbf7)',
              }}
            />
          </div>
        )}
        {stage.duration != null && (isComplete || isRunning) && (
          <span
            className="text-[10px] font-mono tabular-nums"
            style={{ color: 'rgba(248, 245, 253, 0.3)' }}
          >
            {formatDuration(stage.duration)}
          </span>
        )}
      </div>
    </div>
  );
}

export default function PipelineProgress({
  stages,
  overallProgress,
  status,
  videoTitle,
  startedAt,
  className = '',
}: PipelineProgressProps) {
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (status === 'processing' || status === 'validating') {
      const start = startedAt ? new Date(startedAt).getTime() : Date.now();
      timerRef.current = setInterval(() => {
        setElapsed(Date.now() - start);
      }, 100);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [status, startedAt]);

  const completedCount = stages.filter((s) => s.status === 'complete').length;

  return (
    <div
      className={`rounded-2xl overflow-hidden ${className}`}
      style={{
        background: 'rgba(19, 19, 24, 0.7)',
        border: '1px solid rgba(106, 242, 222, 0.08)',
        backdropFilter: 'blur(20px)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-4"
        style={{
          background: 'rgba(25, 25, 31, 0.9)',
          borderBottom: '1px solid rgba(72, 71, 77, 0.1)',
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-2 h-2 rounded-full"
            style={{
              background:
                status === 'complete'
                  ? '#22c55e'
                  : status === 'error'
                  ? '#ef4444'
                  : status === 'processing' || status === 'validating'
                  ? '#6af2de'
                  : 'rgba(248, 245, 253, 0.2)',
              boxShadow:
                status === 'processing'
                  ? '0 0 8px rgba(106, 242, 222, 0.5)'
                  : 'none',
            }}
          />
          <span
            className="font-heading text-xs tracking-widest uppercase font-bold"
            style={{ color: '#f8f5fd' }}
          >
            {status === 'idle'
              ? 'Pipeline Ready'
              : status === 'validating'
              ? 'Validating Input'
              : status === 'processing'
              ? 'Processing'
              : status === 'complete'
              ? 'Complete'
              : 'Error'}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span
            className="text-[10px] font-mono tabular-nums"
            style={{ color: 'rgba(248, 245, 253, 0.3)' }}
          >
            {completedCount}/{stages.length} stages
          </span>
          {(status === 'processing' || status === 'validating') && (
            <span
              className="text-[10px] font-mono tabular-nums"
              style={{ color: 'rgba(248, 245, 253, 0.3)' }}
            >
              {formatDuration(elapsed)}
            </span>
          )}
        </div>
      </div>

      {/* Overall progress bar */}
      <div className="h-0.5" style={{ background: 'rgba(25, 25, 31, 0.8)' }}>
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{
            width: `${overallProgress}%`,
            background:
              status === 'complete'
                ? '#22c55e'
                : status === 'error'
                ? '#ef4444'
                : 'linear-gradient(90deg, #6af2de, #38fbf7)',
          }}
        />
      </div>

      {/* Video title */}
      {videoTitle && (
        <div
          className="px-5 py-3"
          style={{ borderBottom: '1px solid rgba(72, 71, 77, 0.08)' }}
        >
          <p
            className="text-sm truncate"
            style={{ color: 'rgba(248, 245, 253, 0.6)' }}
          >
            {videoTitle}
          </p>
        </div>
      )}

      {/* Stages */}
      <div className="p-3 space-y-1">
        {stages.map((stage, i) => (
          <StageRow key={stage.id} stage={stage} index={i} />
        ))}
      </div>
    </div>
  );
}
