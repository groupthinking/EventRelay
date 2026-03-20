'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { clsx } from 'clsx';
import AgentFlowVisualizer from '@/components/AgentFlowVisualizer';
import TracePanel from '@/components/TracePanel';
import ConsensusIndicator from '@/components/ConsensusIndicator';
import type { PipelineState } from '@/lib/agent-types';
import { createNodePositions } from '@/lib/agent-pipeline';
import { useAgentPipeline, type PipelineMode } from '@/lib/use-agent-pipeline';

// ── Mode Badge ──

const MODE_CONFIG: Record<PipelineMode, { label: string; color: string; bg: string } | null> = {
  idle: null,
  live:       { label: 'Live',       color: 'text-emerald-300', bg: 'bg-emerald-500/15' },
  serverless: { label: 'Serverless', color: 'text-sky-300',     bg: 'bg-sky-500/15' },
  demo:       { label: 'Demo',       color: 'text-amber-300',   bg: 'bg-amber-500/15' },
};

function ModeBadge({ mode }: { mode: PipelineMode }) {
  const cfg = MODE_CONFIG[mode];
  if (!cfg) return null;
  return (
    <span className={clsx('px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', cfg.color, cfg.bg)}>
      {cfg.label}
    </span>
  );
}

// ── Status Header Bar ──

function PipelineStatusBar({ state, mode }: { state: PipelineState; mode: PipelineMode }) {
  const statusConfig = {
    idle:       { label: 'Ready',      color: 'text-white/40',     dot: 'bg-gray-500',    bg: 'bg-white/[0.03]' },
    validating: { label: 'Validating', color: 'text-amber-400',    dot: 'bg-amber-400',   bg: 'bg-amber-500/10' },
    processing: { label: 'Processing', color: 'text-indigo-400',   dot: 'bg-indigo-400',  bg: 'bg-indigo-500/10' },
    complete:   { label: 'Complete',   color: 'text-emerald-400',  dot: 'bg-emerald-400', bg: 'bg-emerald-500/10' },
    error:      { label: 'Error',      color: 'text-red-400',      dot: 'bg-red-400',     bg: 'bg-red-500/10' },
  };

  const cfg = statusConfig[state.status];
  const agentList = Object.values(state.agents);
  const complete = agentList.filter((a) => a.status === 'complete').length;
  const running = agentList.filter((a) => a.status === 'running').length;
  const total = agentList.length;

  return (
    <div className="flex items-center gap-4">
      {/* Status badge */}
      <div className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/[0.05]', cfg.bg)}>
        <span className="relative flex h-2 w-2">
          {state.status === 'processing' && (
            <span className={clsx('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', cfg.dot)} />
          )}
          <span className={clsx('relative inline-flex rounded-full h-2 w-2', cfg.dot)} />
        </span>
        <span className={clsx('text-xs font-bold uppercase tracking-wider', cfg.color)}>
          {cfg.label}
        </span>
      </div>

      {/* Mode badge */}
      <ModeBadge mode={mode} />

      {/* Agent counts */}
      {state.status === 'processing' && (
        <div className="flex items-center gap-4 text-xs font-mono">
          {running > 0 && <span className="text-indigo-400">⚡ {running} running</span>}
          <span className="text-emerald-400/60">✓ {complete}/{total}</span>
        </div>
      )}

      {/* Pipeline timing */}
      {state.completedAt && state.startedAt && (
        <span className="text-xs text-white/30 font-mono">
          {((new Date(state.completedAt).getTime() - new Date(state.startedAt).getTime()) / 1000).toFixed(1)}s total
        </span>
      )}
    </div>
  );
}

// ── Agent Detail Sidebar ──

function AgentDetailPanel({
  state,
  agentId,
  onClose,
}: {
  state: PipelineState;
  agentId: string;
  onClose: () => void;
}) {
  const agent = state.agents[agentId];
  if (!agent) return null;

  const relatedTraces = state.trace.filter((t) => t.agentId === agentId);

  return (
    <div className="animate-slide-in-right space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-white/80">{agent.name}</h3>
        <button
          onClick={onClose}
          className="text-white/30 hover:text-white/60 transition text-lg leading-none"
        >
          ×
        </button>
      </div>

      {/* Description */}
      <p className="text-xs text-white/40 leading-relaxed">{agent.description}</p>

      {/* Properties */}
      <div className="space-y-2">
        {agent.model && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-white/40">Model</span>
            <span className="text-indigo-400 font-mono">{agent.model}</span>
          </div>
        )}
        <div className="flex items-center justify-between text-xs">
          <span className="text-white/40">Role</span>
          <span className="text-white/60 font-mono">{agent.role}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-white/40">Status</span>
          <span className={clsx(
            'font-mono font-bold',
            agent.status === 'complete' ? 'text-emerald-400' :
            agent.status === 'running' ? 'text-indigo-400' :
            agent.status === 'error' ? 'text-red-400' :
            'text-white/50',
          )}>
            {agent.status}
          </span>
        </div>
        {agent.executionTimeMs !== undefined && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-white/40">Duration</span>
            <span className="text-amber-400/60 font-mono">
              {(agent.executionTimeMs / 1000).toFixed(1)}s
            </span>
          </div>
        )}
      </div>

      {/* Tools */}
      {agent.tools && agent.tools.length > 0 && (
        <div>
          <h4 className="text-[10px] font-bold text-white/40 uppercase tracking-wider mb-2">
            Tools
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {agent.tools.map((tool) => (
              <span
                key={tool}
                className="px-2 py-1 text-[10px] font-mono bg-white/[0.03] border border-white/[0.06] rounded-md text-white/50"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Trace history */}
      {relatedTraces.length > 0 && (
        <div>
          <h4 className="text-[10px] font-bold text-white/40 uppercase tracking-wider mb-2">
            Trace History
          </h4>
          <div className="space-y-1.5">
            {relatedTraces.map((trace) => (
              <div
                key={trace.id}
                className={clsx(
                  'px-2.5 py-2 rounded-lg text-xs font-mono border',
                  trace.status === 'complete'
                    ? 'bg-emerald-500/[0.04] border-emerald-500/10 text-emerald-400/60'
                    : trace.status === 'running'
                      ? 'bg-indigo-500/[0.04] border-indigo-500/10 text-indigo-400/60'
                      : 'bg-white/[0.02] border-white/[0.05] text-white/40',
                )}
              >
                <div className="flex justify-between items-center">
                  <span className="capitalize">{trace.status}</span>
                  {trace.durationMs !== undefined && (
                    <span className="text-amber-400/50 text-[10px]">
                      {(trace.durationMs / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>
                {trace.output && (
                  <p className="mt-1 text-[10px] text-white/30 leading-relaxed">
                    {trace.output.preview}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Page ──

export default function AgentPipelinePage() {
  const [videoUrl, setVideoUrl] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const { state: pipelineState, mode, startPipeline, resetPipeline } = useAgentPipeline();

  const positions = createNodePositions();

  const handleStart = useCallback(() => {
    if (!videoUrl.trim()) return;
    setSelectedAgentId(null);
    startPipeline(videoUrl);
  }, [videoUrl, startPipeline]);

  const handleReset = useCallback(() => {
    setSelectedAgentId(null);
    resetPipeline();
    setVideoUrl('');
  }, [resetPipeline]);

  return (
    <div className="h-screen flex flex-col text-white overflow-hidden bg-surface-950">
      {/* Navigation */}
      <nav className="flex-none flex items-center justify-between px-6 py-3 border-b border-white/[0.05] bg-surface-900/80 backdrop-blur-xl z-50">
        <div className="flex items-center gap-5">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center font-black text-sm shadow-lg shadow-primary-500/25">
              E
            </div>
            <span className="font-bold tracking-tight text-sm">EventRelay</span>
          </Link>
          <div className="h-5 w-px bg-white/[0.08]" />
          <div className="flex items-center gap-1">
            <Link href="/dashboard" className="text-white/40 hover:text-white/60 text-sm transition">
              Dashboard
            </Link>
            <span className="text-white/20 mx-1">/</span>
            <span className="text-white/70 text-sm font-medium">Agent Pipeline</span>
          </div>
        </div>

        <PipelineStatusBar state={pipelineState} mode={mode} />
      </nav>

      {/* Main content area: 3-column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Input + Consensus + Agent Detail */}
        <div className="w-[300px] flex-none flex flex-col border-r border-white/[0.05] bg-[#0a0a14]">
          {/* URL Input */}
          <div className="flex-none p-4 border-b border-white/[0.05]">
            <label className="text-[10px] font-bold text-white/40 uppercase tracking-wider block mb-2">
              Video URL
            </label>
            <form
              onSubmit={(e) => { e.preventDefault(); handleStart(); }}
              className="flex flex-col gap-2"
            >
              <input
                type="text"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="https://youtube.com/watch?v=..."
                className="w-full px-3 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.08] text-sm text-white placeholder:text-white/25 focus:outline-none focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20 transition font-mono text-xs"
                disabled={pipelineState.status === 'processing' || pipelineState.status === 'validating'}
              />
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={!videoUrl.trim() || pipelineState.status === 'processing' || pipelineState.status === 'validating'}
                  className="flex-1 btn btn-primary py-2.5 text-xs rounded-xl disabled:opacity-30"
                >
                  {pipelineState.status === 'processing' ? '⚡ Running…' : '▶ Start Pipeline'}
                </button>
                {pipelineState.status !== 'idle' && (
                  <button
                    type="button"
                    onClick={handleReset}
                    className="btn btn-ghost py-2.5 text-xs rounded-xl text-white/40 hover:text-white/70"
                  >
                    ↺
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* Scrollable sidebar content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Consensus */}
            <ConsensusIndicator consensus={pipelineState.consensus} />

            {/* Agent detail (when selected) */}
            {selectedAgentId && (
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <AgentDetailPanel
                  state={pipelineState}
                  agentId={selectedAgentId}
                  onClose={() => setSelectedAgentId(null)}
                />
              </div>
            )}

            {/* Pipeline info */}
            {pipelineState.status === 'idle' && (
              <div className="text-center py-8 space-y-3">
                <div className="text-4xl opacity-20">🧠</div>
                <p className="text-xs text-white/30 leading-relaxed max-w-[220px] mx-auto">
                  Enter a YouTube URL above to start the multi-agent video intelligence pipeline.
                </p>
                <div className="flex flex-wrap gap-1.5 justify-center pt-2">
                  {['Orchestrator', 'Router', 'ParallelCrew', 'Analysts ×3', 'ActionGen', 'QA'].map((label) => (
                    <span
                      key={label}
                      className="px-2 py-1 text-[9px] font-mono bg-white/[0.02] border border-white/[0.05] rounded text-white/30"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Pipeline complete output */}
            {pipelineState.status === 'complete' && pipelineState.outputWorkflow && (
              <div className="p-4 rounded-xl bg-emerald-500/[0.04] border border-emerald-500/15">
                <h4 className="text-[10px] font-bold text-emerald-400/70 uppercase tracking-wider mb-2">
                  Generated Workflow
                </h4>
                <pre className="text-[10px] text-white/50 font-mono whitespace-pre-wrap leading-relaxed">
                  {pipelineState.outputWorkflow}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Center: Agent Flow Visualization */}
        <div className="flex-1 flex flex-col bg-[#070710] relative overflow-hidden">
          {/* Grid background */}
          <div
            className="absolute inset-0 opacity-[0.03] pointer-events-none"
            style={{
              backgroundImage:
                'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
              backgroundSize: '40px 40px',
            }}
          />

          <AgentFlowVisualizer
            agents={pipelineState.agents}
            connections={pipelineState.connections}
            positions={positions}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
            className="flex-1"
          />
        </div>

        {/* Right: Trace Panel */}
        <div className="w-[320px] flex-none border-l border-white/[0.05] bg-[#0a0a14]">
          <TracePanel
            steps={pipelineState.trace}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
          />
        </div>
      </div>
    </div>
  );
}
