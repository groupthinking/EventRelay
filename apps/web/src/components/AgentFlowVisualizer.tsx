'use client';

import { useCallback, useMemo, useRef } from 'react';
import { clsx } from 'clsx';
import {
  Target,
  Split,
  Zap,
  FileText,
  Eye,
  Volume2,
  Cog,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react';
import type {
  AgentNode,
  AgentConnection,
  AgentNodeStatus,
  AgentRole,
  NodePositionMap,
} from '@/lib/agent-types';

// ── Helpers ──

const STATUS_CONFIG: Record<AgentNodeStatus, { color: string; glow: string; label: string }> = {
  idle:     { color: '#4b5563', glow: 'transparent',            label: 'Idle' },
  pending:  { color: '#6b7280', glow: 'rgba(107,114,128,0.3)',  label: 'Pending' },
  running:  { color: '#818cf8', glow: 'rgba(129,140,248,0.4)',  label: 'Running' },
  complete: { color: '#34d399', glow: 'rgba(52,211,153,0.3)',   label: 'Complete' },
  error:    { color: '#f87171', glow: 'rgba(248,113,113,0.3)',  label: 'Error' },
};

const ROLE_ICONS: Record<AgentRole, LucideIcon> = {
  orchestrator:       Target,
  router:             Split,
  parallel_crew:      Zap,
  transcript_analyst: FileText,
  visual_analyst:     Eye,
  audio_analyst:      Volume2,
  action_generator:   Cog,
  quality_checker:    ShieldCheck,
};

interface AgentFlowVisualizerProps {
  agents: Record<string, AgentNode>;
  connections: AgentConnection[];
  positions: NodePositionMap;
  selectedAgentId: string | null;
  onSelectAgent: (id: string | null) => void;
  className?: string;
}

/**
 * Visualizes agent nodes and their connections in an interactive SVG flow diagram.
 *
 * @param agents - Map of agent node ids to agent data.
 * @param connections - Connections to render between agents.
 * @param positions - Layout positions for each agent node.
 * @param selectedAgentId - Id of the currently selected agent, or `null`.
 * @param onSelectAgent - Called when an agent is selected or deselected.
 * @param className - Additional classes to apply to the container.
 */
export default function AgentFlowVisualizer({
  agents,
  connections,
  positions,
  selectedAgentId,
  onSelectAgent,
  className,
}: AgentFlowVisualizerProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  // Compute SVG viewBox based on positions
  const viewBox = useMemo(() => {
    const allPos = Object.values(positions);
    if (allPos.length === 0) return '0 0 900 700';

    // ⚡ Bolt: Replace multiple O(N) map+spread passes with a single O(N) loop.
    // Expected impact: Removes 4 intermediate array allocations and prevents Maximum Call Stack Size Exceeded errors on large node graphs.
    let minX = Infinity, minY = Infinity;
    let maxX = -Infinity, maxY = -Infinity;

    for (let i = 0; i < allPos.length; i++) {
      const p = allPos[i];
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x + p.width > maxX) maxX = p.x + p.width;
      if (p.y + p.height > maxY) maxY = p.y + p.height;
    }

    minX -= 40;
    minY -= 40;
    maxX += 40;
    maxY += 40;

    return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`;
  }, [positions]);

  const handleNodeClick = useCallback(
    (agentId: string) => {
      onSelectAgent(selectedAgentId === agentId ? null : agentId);
    },
    [selectedAgentId, onSelectAgent],
  );

  return (
    <div className={clsx('relative w-full h-full', className)}>
      <svg
        ref={svgRef}
        viewBox={viewBox}
        className="w-full h-full"
        style={{ minHeight: '500px' }}
      >
        {/* Definitions */}
        <defs>
          {/* Arrow marker */}
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="rgba(129,140,248,0.5)" />
          </marker>
          <marker
            id="arrowhead-active"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#818cf8" />
          </marker>

          {/* Node glow filters */}
          <filter id="glow-running" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
            <feColorMatrix
              in="blur"
              type="matrix"
              values="0 0 0 0 0.506
                      0 0 0 0 0.549
                      0 0 0 0 0.973
                      0 0 0 0.5 0"
            />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-complete" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
            <feColorMatrix
              in="blur"
              type="matrix"
              values="0 0 0 0 0.204
                      0 0 0 0 0.827
                      0 0 0 0 0.600
                      0 0 0 0.35 0"
            />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-error" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
            <feColorMatrix
              in="blur"
              type="matrix"
              values="0 0 0 0 0.973
                      0 0 0 0 0.443
                      0 0 0 0 0.443
                      0 0 0 0.35 0"
            />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Flowing data animation */}
          <linearGradient id="flow-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="transparent" />
            <stop offset="40%" stopColor="#818cf8" />
            <stop offset="60%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="transparent" />
          </linearGradient>
        </defs>

        {/* Connections */}
        {connections.map((conn) => {
          const fromPos = positions[conn.from];
          const toPos = positions[conn.to];
          if (!fromPos || !toPos) return null;

          const fromCx = fromPos.x + fromPos.width / 2;
          const fromCy = fromPos.y + fromPos.height;
          const toCx = toPos.x + toPos.width / 2;
          const toCy = toPos.y;

          // Bezier curve for smooth connections
          const midY = (fromCy + toCy) / 2;
          const path = `M ${fromCx} ${fromCy} C ${fromCx} ${midY}, ${toCx} ${midY}, ${toCx} ${toCy}`;

          return (
            <g key={conn.id}>
              {/* Background path */}
              <path
                d={path}
                fill="none"
                stroke={conn.active ? 'rgba(129,140,248,0.4)' : 'rgba(255,255,255,0.06)'}
                strokeWidth={conn.active ? 2.5 : 1.5}
                markerEnd={conn.active ? 'url(#arrowhead-active)' : 'url(#arrowhead)'}
                className="transition-[stroke,stroke-width] duration-500 motion-reduce:transition-none"
              />
              {/* Animated flow particles */}
              {conn.dataFlowing && (
                <circle r="3" fill="#818cf8">
                  <animateMotion dur="1.2s" repeatCount="indefinite" path={path} />
                </circle>
              )}
              {/* Connection label */}
              {conn.label && conn.active && (
                <text
                  x={(fromCx + toCx) / 2}
                  y={midY - 8}
                  textAnchor="middle"
                  fill="rgba(129,140,248,0.7)"
                  fontSize="10"
                  fontFamily="var(--font-mono)"
                >
                  {conn.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Agent Nodes */}
        {Object.entries(agents).map(([id, agent]) => {
          const pos = positions[id];
          if (!pos) return null;

          const config = STATUS_CONFIG[agent.status];
          const isSelected = selectedAgentId === id;
          const filterName =
            agent.status === 'running' ? 'url(#glow-running)' :
            agent.status === 'complete' ? 'url(#glow-complete)' :
            agent.status === 'error' ? 'url(#glow-error)' :
            'none';

          const RoleIcon = ROLE_ICONS[agent.role] || Cog;
          return (
            <g
              key={id}
              role="button"
              tabIndex={0}
              aria-label={`${agent.name}: ${config.label}`}
              aria-pressed={isSelected}
              onClick={() => handleNodeClick(id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleNodeClick(id);
                }
              }}
              className="cursor-pointer focus:outline-none [&:focus-visible>rect]:stroke-[#818cf8]"
              filter={filterName}
            >
              {/* Selection ring */}
              {isSelected && (
                <rect
                  x={pos.x - 4}
                  y={pos.y - 4}
                  width={pos.width + 8}
                  height={pos.height + 8}
                  rx={16}
                  fill="none"
                  stroke="#818cf8"
                  strokeWidth={2}
                  strokeDasharray="6 3"
                  className="animate-spin-slow motion-reduce:animate-none"
                >
                  <animate
                    attributeName="stroke-dashoffset"
                    from="0"
                    to="18"
                    dur="1s"
                    repeatCount="indefinite"
                  />
                </rect>
              )}

              {/* Node background */}
              <rect
                x={pos.x}
                y={pos.y}
                width={pos.width}
                height={pos.height}
                rx={12}
                fill={isSelected ? 'rgba(26,26,46,0.95)' : 'rgba(15,23,42,0.85)'}
                stroke={config.color}
                strokeWidth={isSelected ? 2 : 1}
                className="transition-[fill,stroke,stroke-width] duration-300 motion-reduce:transition-none"
              />

              {/* Progress bar (when running) */}
              {agent.status === 'running' && (
                <rect
                  x={pos.x + 1}
                  y={pos.y + pos.height - 4}
                  width={(pos.width - 2) * (agent.progress / 100)}
                  height={3}
                  rx={1.5}
                  fill={config.color}
                  className="transition-[width] duration-300 motion-reduce:transition-none"
                />
              )}

              {/* Role icon */}
              <foreignObject x={pos.x + 10} y={pos.y + 14} width={18} height={18}>
                <RoleIcon className="h-[18px] w-[18px] text-white/80" aria-hidden="true" />
              </foreignObject>

              {/* Agent name */}
              <text
                x={pos.x + 34}
                y={pos.y + 28}
                fill="white"
                fontSize="11"
                fontWeight="600"
                fontFamily="var(--font-body)"
              >
                {agent.name.length > 18 ? agent.name.substring(0, 16) + '…' : agent.name}
              </text>

              {/* Status indicator */}
              <circle
                cx={pos.x + pos.width - 18}
                cy={pos.y + 24}
                r={5}
                fill={config.color}
              >
                {agent.status === 'running' && (
                  <animate
                    attributeName="opacity"
                    values="1;0.4;1"
                    dur="1.5s"
                    repeatCount="indefinite"
                  />
                )}
              </circle>

              {/* Description */}
              <text
                x={pos.x + 14}
                y={pos.y + 48}
                fill="rgba(255,255,255,0.4)"
                fontSize="9"
                fontFamily="var(--font-mono)"
              >
                {agent.model || agent.role}
              </text>

              {/* Execution time (when complete) */}
              {agent.executionTimeMs !== undefined && agent.status === 'complete' && (
                <text
                  x={pos.x + pos.width - 14}
                  y={pos.y + 48}
                  fill="rgba(52,211,153,0.6)"
                  fontSize="9"
                  fontFamily="var(--font-mono)"
                  textAnchor="end"
                >
                  {(agent.executionTimeMs / 1000).toFixed(1)}s
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
