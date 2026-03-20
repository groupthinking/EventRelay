/**
 * Mock pipeline data generator for the Agent Flow Visualizer.
 *
 * Generates a realistic multi-agent pipeline structure based on
 * the UVAI video intelligence architecture defined in Phase 3.
 *
 * In production, this will be replaced by real WebSocket data
 * from the backend orchestrator.
 */

import type {
  AgentNode,
  AgentConnection,
  TraceStep,
  ConsensusResult,
  PipelineState,
  NodePosition,
  NodePositionMap,
} from './agent-types';

// ── Default Pipeline Agents ──

export function createDefaultAgents(): Record<string, AgentNode> {
  return {
    orchestrator: {
      id: 'orchestrator',
      name: 'VideoIntelligenceOrchestrator',
      role: 'orchestrator',
      description: 'Coordinates video analysis and workflow generation',
      status: 'idle',
      progress: 0,
      children: ['router'],
      model: 'gemini-2.5-flash',
      tools: ['generate_output'],
    },
    router: {
      id: 'router',
      name: 'ContentTypeRouter',
      role: 'router',
      description: 'Routes processing based on video content type',
      status: 'idle',
      progress: 0,
      children: ['crew'],
    },
    crew: {
      id: 'crew',
      name: 'AnalysisCrew',
      role: 'parallel_crew',
      description: 'Runs transcript, visual, and audio analysis in parallel',
      status: 'idle',
      progress: 0,
      children: ['transcript', 'visual', 'audio'],
    },
    transcript: {
      id: 'transcript',
      name: 'TranscriptAnalyst',
      role: 'transcript_analyst',
      description: 'Analyzes video transcript for structure and key content',
      status: 'idle',
      progress: 0,
      model: 'gemini-2.5-flash',
      tools: ['STT API', 'NLP Cleaning'],
    },
    visual: {
      id: 'visual',
      name: 'VisualAnalyst',
      role: 'visual_analyst',
      description: 'Analyzes video frames for UI, code, and demonstrations',
      status: 'idle',
      progress: 0,
      model: 'gemini-2.5-flash',
      tools: ['Vision API', 'Scene Detection'],
    },
    audio: {
      id: 'audio',
      name: 'AudioAnalyst',
      role: 'audio_analyst',
      description: 'Analyzes audio for tone, emphasis, and supplementary data',
      status: 'idle',
      progress: 0,
      model: 'gemini-2.5-flash',
      tools: ['Audio API', 'Sentiment Analysis'],
    },
    action_gen: {
      id: 'action_gen',
      name: 'ActionGenerator',
      role: 'action_generator',
      description: 'Generates actionable workflows from combined analysis',
      status: 'idle',
      progress: 0,
      model: 'gemini-2.5-flash',
      tools: ['Template Engine', 'Validator'],
    },
    quality: {
      id: 'quality',
      name: 'QualityChecker',
      role: 'quality_checker',
      description: 'Validates all outputs against quality constraints',
      status: 'idle',
      progress: 0,
      tools: ['Schema Validator', 'Fact Checker'],
    },
  };
}

// ── Default Connections ──

export function createDefaultConnections(): AgentConnection[] {
  return [
    { id: 'c1', from: 'orchestrator', to: 'router', label: 'Video URL', active: false, dataFlowing: false },
    { id: 'c2', from: 'router', to: 'crew', label: 'Content Type', active: false, dataFlowing: false },
    { id: 'c3', from: 'crew', to: 'transcript', label: 'parallel', active: false, dataFlowing: false },
    { id: 'c4', from: 'crew', to: 'visual', label: 'parallel', active: false, dataFlowing: false },
    { id: 'c5', from: 'crew', to: 'audio', label: 'parallel', active: false, dataFlowing: false },
    { id: 'c6', from: 'transcript', to: 'action_gen', label: 'Segments', active: false, dataFlowing: false },
    { id: 'c7', from: 'visual', to: 'action_gen', label: 'Frames', active: false, dataFlowing: false },
    { id: 'c8', from: 'audio', to: 'action_gen', label: 'Audio Data', active: false, dataFlowing: false },
    { id: 'c9', from: 'action_gen', to: 'quality', label: 'Workflow', active: false, dataFlowing: false },
    { id: 'c10', from: 'quality', to: 'orchestrator', label: 'Validated', active: false, dataFlowing: false },
  ];
}

// ── Layout Positions ──

export function createNodePositions(): NodePositionMap {
  const w = 180;
  const h = 72;
  return {
    orchestrator: { x: 360, y: 24, width: w, height: h },
    router:       { x: 360, y: 140, width: w, height: h },
    crew:         { x: 360, y: 256, width: w, height: h },
    transcript:   { x: 100, y: 380, width: w, height: h },
    visual:       { x: 360, y: 380, width: w, height: h },
    audio:        { x: 620, y: 380, width: w, height: h },
    action_gen:   { x: 360, y: 510, width: w, height: h },
    quality:      { x: 360, y: 630, width: w, height: h },
  };
}

// ── Simulation Engine ──

type SimCallback = (state: PipelineState) => void;

const STEP_DELAYS: Record<string, number> = {
  orchestrator: 800,
  router: 600,
  crew: 200,
  transcript: 2400,
  visual: 2800,
  audio: 2000,
  action_gen: 1800,
  quality: 1200,
};

/**
 * Simulates a full pipeline execution with realistic timing.
 * Calls the callback at each state change so the UI updates in real time.
 */
export function simulatePipeline(
  videoUrl: string,
  videoTitle: string,
  onUpdate: SimCallback
): { cancel: () => void } {
  let cancelled = false;
  const agents = createDefaultAgents();
  const connections = createDefaultConnections();
  const trace: TraceStep[] = [];

  const state: PipelineState = {
    id: `pipeline_${Date.now()}`,
    videoUrl,
    videoTitle,
    status: 'validating',
    startedAt: new Date().toISOString(),
    agents,
    connections,
    trace,
  };

  function updateAgent(id: string, patch: Partial<AgentNode>): void {
    state.agents[id] = { ...state.agents[id], ...patch };
  }

  function activateConnection(from: string, to: string): void {
    const conn = state.connections.find((c) => c.from === from && c.to === to);
    if (conn) {
      conn.active = true;
      conn.dataFlowing = true;
    }
  }

  function deactivateConnection(from: string, to: string): void {
    const conn = state.connections.find((c) => c.from === from && c.to === to);
    if (conn) {
      conn.dataFlowing = false;
    }
  }

  function addTrace(agentId: string, status: AgentNode['status'], extra?: Partial<TraceStep>): void {
    trace.push({
      id: `trace_${trace.length}`,
      agentId,
      agentName: agents[agentId].name,
      agentRole: agents[agentId].role,
      status,
      timestamp: new Date().toISOString(),
      ...extra,
    });
  }

  function emit(): void {
    if (!cancelled) onUpdate({ ...state, trace: [...trace] });
  }

  async function delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function runAgent(id: string, inputPreview: string, outputPreview: string): Promise<void> {
    if (cancelled) return;
    const dur = STEP_DELAYS[id] || 1000;

    updateAgent(id, { status: 'running', progress: 0 });
    addTrace(id, 'running', { input: { type: 'data', preview: inputPreview } });
    emit();

    // Simulate progress
    const steps = 5;
    for (let i = 1; i <= steps; i++) {
      if (cancelled) return;
      await delay(dur / steps);
      updateAgent(id, { progress: Math.round((i / steps) * 100) });
      emit();
    }

    updateAgent(id, { status: 'complete', progress: 100, executionTimeMs: dur });
    addTrace(id, 'complete', {
      durationMs: dur,
      output: { type: 'data', preview: outputPreview },
    });
    emit();
  }

  // Main simulation sequence
  (async () => {
    // Step 1: Validation
    state.status = 'validating';
    addTrace('orchestrator', 'pending', { input: { type: 'url', preview: videoUrl } });
    emit();
    await delay(500);

    // Step 2: Orchestrator
    state.status = 'processing';
    activateConnection('orchestrator', 'router');
    await runAgent('orchestrator', videoUrl, 'Dispatching to router…');
    deactivateConnection('orchestrator', 'router');

    // Step 3: Router
    activateConnection('router', 'crew');
    await runAgent('router', 'Video metadata loaded', 'Content type: tutorial');
    deactivateConnection('router', 'crew');

    // Step 4: Parallel Crew dispatch
    updateAgent('crew', { status: 'running', progress: 0 });
    addTrace('crew', 'running', { input: { type: 'dispatch', preview: '3 parallel agents' } });
    activateConnection('crew', 'transcript');
    activateConnection('crew', 'visual');
    activateConnection('crew', 'audio');
    emit();

    // Step 5: Run 3 analysts in parallel
    await Promise.all([
      runAgent('transcript', 'Raw transcript (12,400 words)', '24 segments, 48 action steps'),
      runAgent('visual', '142 key frames extracted', '38 code snippets, 12 UI elements'),
      runAgent('audio', 'Audio stream analysis', '8 key emphases, 2 corrections'),
    ]);

    updateAgent('crew', { status: 'complete', progress: 100 });
    addTrace('crew', 'complete', { output: { type: 'aggregated', preview: '3/3 analysts complete' } });
    deactivateConnection('crew', 'transcript');
    deactivateConnection('crew', 'visual');
    deactivateConnection('crew', 'audio');

    // Consensus
    state.consensus = {
      finalClassification: 'tutorial',
      agreementRatio: 0.67,
      method: '2-of-3',
      votes: [
        { agentId: 'transcript', agentName: 'TranscriptAnalyst', classification: 'tutorial', confidence: 0.92, agrees: true },
        { agentId: 'visual', agentName: 'VisualAnalyst', classification: 'tutorial', confidence: 0.88, agrees: true },
        { agentId: 'audio', agentName: 'AudioAnalyst', classification: 'demo', confidence: 0.71, agrees: false },
      ],
    };
    emit();

    // Step 6: Action Generator
    activateConnection('transcript', 'action_gen');
    activateConnection('visual', 'action_gen');
    activateConnection('audio', 'action_gen');
    await runAgent('action_gen', 'Combined analysis from 3 analysts', 'Generated 12-step workflow');
    deactivateConnection('transcript', 'action_gen');
    deactivateConnection('visual', 'action_gen');
    deactivateConnection('audio', 'action_gen');

    // Step 7: Quality Checker
    activateConnection('action_gen', 'quality');
    await runAgent('quality', '12-step workflow draft', 'Validated: 12/12 steps pass schema');
    deactivateConnection('action_gen', 'quality');

    // Step 8: Return to orchestrator
    activateConnection('quality', 'orchestrator');
    await delay(300);
    deactivateConnection('quality', 'orchestrator');

    // Done
    state.status = 'complete';
    state.completedAt = new Date().toISOString();
    state.outputWorkflow = '## Generated Workflow\n\n1. Setup environment\n2. Clone repository\n3. Install dependencies\n...';
    emit();
  })();

  return {
    cancel: () => {
      cancelled = true;
    },
  };
}
