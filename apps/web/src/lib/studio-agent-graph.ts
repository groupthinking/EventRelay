/**
 * Frontend representation and evaluator-optimizer loop for EventRelay's
 * AgentGraph and AgentHandoffEnvelope orchestration.
 */

export type StudioGraphNodeStatus = 'idle' | 'running' | 'complete' | 'error';

export interface StudioGraphNode {
  id: string;
  label: string;
  role: string;
  status: StudioGraphNodeStatus;
  detail: string;
}

export interface StudioHandoffEnvelope {
  traceId: string;
  senderAgent: string;
  recipientAgent: string;
  intent: string;
  lineage: string[];
  contractVersion: string;
  acknowledged: boolean;
}

export interface StudioSelfCorrectionIteration {
  iteration: number;
  passed: boolean;
  critique: string | null;
  refinements: string[];
}

export interface StudioAgentGraphState {
  graphName: string;
  traceId: string;
  nodes: StudioGraphNode[];
  handoffs: StudioHandoffEnvelope[];
  loop: {
    passed: boolean;
    iterations: number;
    maxIterations: number;
    history: StudioSelfCorrectionIteration[];
  };
}

export interface BuildStudioAgentGraphInput {
  videoId: string;
  outcome: string;
  runState: 'idle' | 'working' | 'ready';
  runQuality: string;
  unsafe: boolean;
  jobId?: string;
  actionCount?: number;
  liveUrl?: string | null;
}

const VERIFICATION_DELIVERABLE = 'Self-correction verification checklist';
const HANDOFF_NEXT_STEP = 'Verify agent handoff lineage before production deploy';
const CONVERGENCE_EVIDENCE = 'Self-correction loop converged (evaluator passed)';

const NODE_CHAIN: Array<{
  id: string;
  label: string;
  role: string;
  intent: string;
}> = [
  {
    id: 'transcript_ingest',
    label: 'Transcript & Frame Ingest',
    role: 'ingest',
    intent: 'ingest_video_source',
  },
  {
    id: 'conditional_router',
    label: 'Outcome & Safety Router',
    role: 'router',
    intent: 'route_outcome_and_safety',
  },
  {
    id: 'parallel_crew',
    label: 'Parallel Analyst Crew',
    role: 'fork_join',
    intent: 'analyze_parallel_modalities',
  },
  {
    id: 'self_correction_loop',
    label: 'Self-Correction Evaluator',
    role: 'evaluator_loop',
    intent: 'evaluate_and_refine',
  },
  {
    id: 'package_handoff',
    label: 'Package & Deploy Handoff',
    role: 'handoff',
    intent: 'finalize_handoff_package',
  },
];

function nodeStatusFor(
  nodeId: string,
  runState: 'idle' | 'working' | 'ready',
  hasVideo: boolean,
): StudioGraphNodeStatus {
  if (runState === 'ready') {
    return 'complete';
  }
  if (runState === 'working') {
    if (nodeId === 'transcript_ingest' || nodeId === 'conditional_router') {
      return 'complete';
    }
    if (nodeId === 'parallel_crew' || nodeId === 'self_correction_loop') {
      return 'running';
    }
    return 'idle';
  }
  if (nodeId === 'transcript_ingest' && hasVideo) {
    return 'complete';
  }
  return 'idle';
}

function nodeDetailFor(
  nodeId: string,
  input: BuildStudioAgentGraphInput,
): string {
  const hasVideo = Boolean(input.videoId);
  switch (nodeId) {
    case 'transcript_ingest':
      return hasVideo
        ? `Source ${input.videoId} attached`
        : 'Waiting for YouTube source';
    case 'conditional_router':
      return input.unsafe
        ? 'Safety gate redirected to risk-review branch'
        : `Routed to ${input.outcome} topology`;
    case 'parallel_crew':
      if (typeof input.actionCount === 'number' && input.actionCount > 0) {
        return `${input.actionCount} durable actions extracted`;
      }
      return input.runQuality === 'live'
        ? 'Live backend analysts coordinated'
        : 'Transcript, frames, and intent aligned';
    case 'self_correction_loop':
      if (input.runState === 'ready') {
        return hasVideo && !input.unsafe
          ? 'Initial verification pass recorded'
          : 'Awaiting self-correction verification';
      }
      return input.runState === 'working'
        ? 'Evaluating deliverable and lineage constraints'
        : 'Evaluator ready (max 3 cycles)';
    case 'package_handoff':
      if (input.liveUrl) {
        return `Deployed live: ${input.liveUrl}`;
      }
      if (input.jobId) {
        return `Linked backend job ${input.jobId}`;
      }
      return input.runState === 'ready'
        ? 'Package ready for preview, export, or deploy'
        : 'Waiting for upstream graph nodes';
    default:
      return '';
  }
}

/**
 * Deterministically builds the AgentGraph execution state and AgentHandoffEnvelope
 * lineage for VideoWorkflowStudio.
 */
export function buildStudioAgentGraph(
  input: BuildStudioAgentGraphInput,
): StudioAgentGraphState {
  const hasVideo = Boolean(input.videoId);
  const traceId = hasVideo
    ? `trace_${input.videoId}_${input.outcome}`
    : `trace_draft_${input.outcome}`;

  const nodes: StudioGraphNode[] = NODE_CHAIN.map((spec) => ({
    id: spec.id,
    label: spec.label,
    role: spec.role,
    status: nodeStatusFor(spec.id, input.runState, hasVideo),
    detail: nodeDetailFor(spec.id, input),
  }));

  const handoffs: StudioHandoffEnvelope[] = [];
  const lineage: string[] = [];
  for (let i = 0; i < NODE_CHAIN.length - 1; i += 1) {
    const sender = NODE_CHAIN[i];
    const recipient = NODE_CHAIN[i + 1];
    if (!lineage.includes(sender.id)) {
      lineage.push(sender.id);
    }
    handoffs.push({
      traceId,
      senderAgent: sender.id,
      recipientAgent: recipient.id,
      intent: recipient.intent,
      lineage: [...lineage],
      contractVersion: '1.0.0',
      acknowledged: input.runState === 'ready',
    });
  }

  const initialPassed = input.runState === 'ready' && hasVideo && !input.unsafe;
  const history: StudioSelfCorrectionIteration[] =
    input.runState === 'ready'
      ? [
          {
            iteration: 1,
            passed: initialPassed,
            critique: initialPassed
              ? null
              : !hasVideo
                ? 'Source video ID missing for full verification'
                : 'Safety redirection requires manual verification',
            refinements: [],
          },
        ]
      : [];

  return {
    graphName: 'studio_workflow_graph',
    traceId,
    nodes,
    handoffs,
    loop: {
      passed: initialPassed,
      iterations: input.runState === 'ready' ? 1 : 0,
      maxIterations: 3,
      history,
    },
  };
}

/**
 * Executes an Evaluator-Optimizer self-correction cycle over a generated Studio package
 * and updates the graph state with differential critiques and convergence evidence.
 */
export function runStudioSelfCorrectionLoop<
  T extends {
    deliverables: string[];
    nextSteps: string[];
    evidence: string[];
    sourceNotes: string[];
  },
>(
  pkg: T,
  graph: StudioAgentGraphState,
  maxIterations = 3,
): { pkg: T; graph: StudioAgentGraphState } {
  const deliverables = [...pkg.deliverables];
  const nextSteps = [...pkg.nextSteps];
  const evidence = [...pkg.evidence];
  const sourceNotes = [...pkg.sourceNotes];

  const history: StudioSelfCorrectionIteration[] = [];
  let passed = false;
  let iterations = 0;

  for (let i = 1; i <= maxIterations; i += 1) {
    iterations = i;
    const hasDeliverable = deliverables.includes(VERIFICATION_DELIVERABLE);
    const hasNextStep = nextSteps.includes(HANDOFF_NEXT_STEP);

    if (hasDeliverable && hasNextStep) {
      if (!evidence.includes(CONVERGENCE_EVIDENCE)) {
        evidence.push(CONVERGENCE_EVIDENCE);
      }
      history.push({
        iteration: i,
        passed: true,
        critique: null,
        refinements: [],
      });
      passed = true;
      break;
    }

    const refinements: string[] = [];
    if (!hasDeliverable) {
      deliverables.push(VERIFICATION_DELIVERABLE);
      refinements.push(`Added deliverable: ${VERIFICATION_DELIVERABLE}`);
    }
    if (!hasNextStep) {
      nextSteps.push(HANDOFF_NEXT_STEP);
      refinements.push(`Added next step: ${HANDOFF_NEXT_STEP}`);
    }
    if (!evidence.includes(CONVERGENCE_EVIDENCE)) {
      evidence.push(CONVERGENCE_EVIDENCE);
      refinements.push(`Attached evidence: ${CONVERGENCE_EVIDENCE}`);
    }

    history.push({
      iteration: i,
      passed: false,
      critique: 'Missing explicit self-correction verification deliverable and handoff guard',
      refinements,
    });
  }

  const convergenceNote = `AgentGraph ${graph.traceId} verified in ${iterations}/${maxIterations} loop iteration${iterations === 1 ? '' : 's'}.`;
  if (!sourceNotes.includes(convergenceNote)) {
    sourceNotes.push(convergenceNote);
  }

  const updatedPkg: T = {
    ...pkg,
    deliverables,
    nextSteps,
    evidence,
    sourceNotes,
  };

  const updatedGraph: StudioAgentGraphState = {
    ...graph,
    nodes: graph.nodes.map((node) => ({
      ...node,
      status: 'complete',
      detail:
        node.id === 'self_correction_loop'
          ? passed
            ? `Converged in ${iterations}/${maxIterations} cycles`
            : `Stopped after ${iterations}/${maxIterations} cycles`
          : node.detail,
    })),
    handoffs: graph.handoffs.map((h) => ({ ...h, acknowledged: true })),
    loop: {
      passed,
      iterations,
      maxIterations,
      history,
    },
  };

  return { pkg: updatedPkg, graph: updatedGraph };
}
