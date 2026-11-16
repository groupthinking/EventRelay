import { describe, expect, it } from 'vitest';
import {
  buildStudioAgentGraph,
  runStudioSelfCorrectionLoop,
} from '@/lib/studio-agent-graph';

describe('studio-agent-graph', () => {
  it('builds graph node statuses for idle, working, and ready states', () => {
    const idleNoVideo = buildStudioAgentGraph({
      videoId: '',
      outcome: 'app',
      runState: 'idle',
      runQuality: 'idle',
      unsafe: false,
    });
    expect(idleNoVideo.traceId).toBe('trace_draft_app');
    expect(idleNoVideo.nodes).toHaveLength(5);
    expect(idleNoVideo.nodes.every((n) => n.status === 'idle')).toBe(true);
    expect(idleNoVideo.loop.passed).toBe(false);
    expect(idleNoVideo.loop.iterations).toBe(0);

    const idleWithVideo = buildStudioAgentGraph({
      videoId: 'auJzb1D-fag',
      outcome: 'sop',
      runState: 'idle',
      runQuality: 'idle',
      unsafe: false,
    });
    expect(idleWithVideo.traceId).toBe('trace_auJzb1D-fag_sop');
    expect(idleWithVideo.nodes[0].status).toBe('complete');
    expect(idleWithVideo.nodes[1].status).toBe('idle');

    const working = buildStudioAgentGraph({
      videoId: 'auJzb1D-fag',
      outcome: 'app',
      runState: 'working',
      runQuality: 'idle',
      unsafe: false,
    });
    expect(working.nodes.map((n) => n.status)).toEqual([
      'complete',
      'complete',
      'running',
      'running',
      'idle',
    ]);
    expect(working.handoffs.every((h) => h.acknowledged === false)).toBe(true);

    const ready = buildStudioAgentGraph({
      videoId: 'auJzb1D-fag',
      outcome: 'app',
      runState: 'ready',
      runQuality: 'live',
      unsafe: false,
      jobId: 'job_123',
    });
    expect(ready.nodes.every((n) => n.status === 'complete')).toBe(true);
    expect(ready.handoffs.every((h) => h.acknowledged === true)).toBe(true);
    expect(ready.loop.passed).toBe(true);
    expect(ready.loop.iterations).toBe(1);
    expect(ready.nodes[4].detail).toContain('job_123');
  });

  it('accumulates handoff envelope lineage across all 5 graph nodes', () => {
    const graph = buildStudioAgentGraph({
      videoId: 'auJzb1D-fag',
      outcome: 'automation',
      runState: 'ready',
      runQuality: 'live',
      unsafe: false,
    });

    expect(graph.handoffs).toHaveLength(4);
    expect(graph.handoffs.map((h) => [h.senderAgent, h.recipientAgent])).toEqual([
      ['transcript_ingest', 'conditional_router'],
      ['conditional_router', 'parallel_crew'],
      ['parallel_crew', 'self_correction_loop'],
      ['self_correction_loop', 'package_handoff'],
    ]);
    expect(graph.handoffs[0].lineage).toEqual(['transcript_ingest']);
    expect(graph.handoffs[3].lineage).toEqual([
      'transcript_ingest',
      'conditional_router',
      'parallel_crew',
      'self_correction_loop',
    ]);
    expect(graph.handoffs.every((h) => h.traceId === graph.traceId)).toBe(true);
  });

  it('runs self-correction loop recording critique on iteration 1 and converging on iteration 2', () => {
    const initialGraph = buildStudioAgentGraph({
      videoId: 'auJzb1D-fag',
      outcome: 'app',
      runState: 'ready',
      runQuality: 'fallback',
      unsafe: false,
    });
    const initialPkg = {
      deliverables: ['Responsive screen map'],
      nextSteps: ['Confirm the target user journey'],
      evidence: ['Video preview loaded'],
      sourceNotes: ['Source URL: https://www.youtube.com/watch?v=auJzb1D-fag'],
    };

    const { pkg: refinedPkg, graph: updatedGraph } = runStudioSelfCorrectionLoop(
      initialPkg,
      initialGraph,
      3,
    );

    expect(updatedGraph.loop.passed).toBe(true);
    expect(updatedGraph.loop.iterations).toBe(2);
    expect(updatedGraph.loop.history).toHaveLength(2);
    expect(updatedGraph.loop.history[0].passed).toBe(false);
    expect(updatedGraph.loop.history[0].critique).toBe(
      'Missing explicit self-correction verification deliverable and handoff guard',
    );
    expect(updatedGraph.loop.history[1].passed).toBe(true);
    expect(updatedGraph.loop.history[1].critique).toBeNull();

    expect(refinedPkg.deliverables).toContain('Self-correction verification checklist');
    expect(refinedPkg.nextSteps).toContain(
      'Verify agent handoff lineage before production deploy',
    );
    expect(refinedPkg.evidence).toContain(
      'Self-correction loop converged (evaluator passed)',
    );
    expect(updatedGraph.nodes.every((n) => n.status === 'complete')).toBe(true);
  });
});
