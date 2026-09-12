/**
 * Type definitions for the Agent Flow Visualizer.
 * These types model the multi-agent pipeline structure,
 * execution traces, and consensus results.
 */

// ── Agent Node Types ──

export type AgentNodeStatus = 'idle' | 'pending' | 'running' | 'complete' | 'error';

export type AgentRole =
  | 'orchestrator'
  | 'router'
  | 'parallel_crew'
  | 'transcript_analyst'
  | 'visual_analyst'
  | 'audio_analyst'
  | 'action_generator'
  | 'quality_checker';

export interface AgentNode {
  id: string;
  name: string;
  role: AgentRole;
  description: string;
  status: AgentNodeStatus;
  progress: number;
  children?: string[];          // IDs of child agents
  tools?: string[];             // Tools this agent can use
  model?: string;               // LLM model used
  executionTimeMs?: number;     // Time taken to execute
  result?: AgentNodeResult;
}

export interface AgentNodeResult {
  summary: string;
  confidence: number;
  outputType: string;           // e.g., 'transcript', 'visual_analysis', 'workflow'
  data?: Record<string, unknown>;
}

// ── Connection Types ──

export interface AgentConnection {
  id: string;
  from: string;   // Source agent ID
  to: string;     // Target agent ID
  label?: string;
  active: boolean;
  dataFlowing: boolean;
}

// ── Trace Types ──

export interface TraceStep {
  id: string;
  agentId: string;
  agentName: string;
  agentRole: AgentRole;
  status: AgentNodeStatus;
  timestamp: string;
  durationMs?: number;
  input?: {
    type: string;
    preview: string;
    size?: string;
  };
  output?: {
    type: string;
    preview: string;
    size?: string;
  };
  error?: string;
  metadata?: Record<string, unknown>;
}

// ── Consensus Types ──

export interface ConsensusVote {
  agentId: string;
  agentName: string;
  classification: string;
  confidence: number;
  agrees: boolean;
}

export interface ConsensusResult {
  finalClassification: string;
  agreementRatio: number;       // e.g., 0.66 for 2/3
  votes: ConsensusVote[];
  method: '2-of-3' | 'majority' | 'unanimous';
}

// ── Pipeline State ──

export interface PipelineState {
  id: string;
  videoUrl: string;
  videoTitle: string;
  status: 'idle' | 'validating' | 'processing' | 'complete' | 'error';
  startedAt?: string;
  completedAt?: string;
  agents: Record<string, AgentNode>;
  connections: AgentConnection[];
  trace: TraceStep[];
  consensus?: ConsensusResult;
  outputWorkflow?: string;      // Generated markdown workflow
  error?: string;               // Honest terminal failure; never a simulated replacement
}

// ── Layout Positions (for SVG rendering) ──

export interface NodePosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type NodePositionMap = Record<string, NodePosition>;
