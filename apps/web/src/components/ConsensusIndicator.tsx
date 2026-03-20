'use client';

import { clsx } from 'clsx';
import type { ConsensusResult } from '@/lib/agent-types';

const ROLE_ICONS: Record<string, string> = {
  transcript: '📝',
  visual: '👁️',
  audio: '🔊',
};

interface ConsensusIndicatorProps {
  consensus: ConsensusResult | undefined;
  className?: string;
}

export default function ConsensusIndicator({
  consensus,
  className,
}: ConsensusIndicatorProps) {
  if (!consensus) return null;

  const percentage = Math.round(consensus.agreementRatio * 100);
  const agreeCount = consensus.votes.filter((v) => v.agrees).length;
  const totalCount = consensus.votes.length;

  return (
    <div
      className={clsx(
        'rounded-xl border overflow-hidden transition-all duration-500',
        percentage >= 80
          ? 'bg-emerald-500/[0.04] border-emerald-500/20'
          : percentage >= 50
            ? 'bg-amber-500/[0.04] border-amber-500/20'
            : 'bg-red-500/[0.04] border-red-500/20',
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05]">
        <div className="flex items-center gap-2">
          <span className="text-sm">🤝</span>
          <h4 className="text-xs font-bold text-white/60 uppercase tracking-wider">
            Consensus: {consensus.method}
          </h4>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              'text-xs font-bold',
              percentage >= 80 ? 'text-emerald-400' :
              percentage >= 50 ? 'text-amber-400' :
              'text-red-400',
            )}
          >
            {agreeCount}/{totalCount} Agree
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-4 pt-3 pb-1">
        <div className="w-full h-2 rounded-full bg-white/[0.05] overflow-hidden">
          <div
            className={clsx(
              'h-full rounded-full transition-all duration-1000 ease-out',
              percentage >= 80 ? 'bg-emerald-500' :
              percentage >= 50 ? 'bg-amber-500' :
              'bg-red-500',
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] text-white/30 font-mono">0%</span>
          <span
            className={clsx(
              'text-xs font-bold font-mono',
              percentage >= 80 ? 'text-emerald-400' :
              percentage >= 50 ? 'text-amber-400' :
              'text-red-400',
            )}
          >
            {percentage}%
          </span>
          <span className="text-[10px] text-white/30 font-mono">100%</span>
        </div>
      </div>

      {/* Votes */}
      <div className="px-4 pb-4 pt-2 space-y-2">
        {consensus.votes.map((vote) => (
          <div
            key={vote.agentId}
            className={clsx(
              'flex items-center justify-between px-3 py-2 rounded-lg border transition-all',
              vote.agrees
                ? 'bg-emerald-500/[0.04] border-emerald-500/15'
                : 'bg-red-500/[0.04] border-red-500/15',
            )}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm">
                {ROLE_ICONS[vote.agentId] || '⚙️'}
              </span>
              <span className="text-xs font-medium text-white/70">
                {vote.agentName}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-mono text-white/40">
                {vote.classification}
              </span>
              <span
                className={clsx(
                  'text-[10px] font-bold font-mono px-1.5 py-0.5 rounded',
                  vote.agrees
                    ? 'text-emerald-400 bg-emerald-500/10'
                    : 'text-red-400 bg-red-500/10',
                )}
              >
                {Math.round(vote.confidence * 100)}%
              </span>
              <span className={vote.agrees ? 'text-emerald-400' : 'text-red-400'}>
                {vote.agrees ? '✓' : '✗'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Result */}
      <div className="px-4 pb-4">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <span className="text-xs font-bold text-white/50 uppercase tracking-wider">
            Result:
          </span>
          <span className="text-xs font-bold text-white/80">
            {consensus.finalClassification}
          </span>
          <span className="text-[10px] text-white/30 font-mono">
            ({percentage}% confidence)
          </span>
        </div>
      </div>
    </div>
  );
}
