/**
 * Optional JSON Canvas 1.0 emit from the Video Pack slice
 * (transcript + visual events + SOP). Spec:
 * https://github.com/groupthinking/jsoncanvas/blob/main/spec/1.0.md
 *
 * File name in the App Builder / Studio workspace: mission.canvas
 * Omit the file when the pack has no usable emit-slice content.
 * Never invent architecture, code_snippets, or keyframe file nodes.
 * File nodes are emitted only when a durable captured image_path is present.
 */

import { isDurableCapturedImagePath } from '@/lib/keyframe-image-path';

export const JSON_CANVAS_SPEC = '1.0' as const;
export const JSON_CANVAS_SPEC_URL =
  'https://github.com/groupthinking/jsoncanvas/blob/main/spec/1.0.md' as const;
export const MISSION_CANVAS_FILENAME = 'mission.canvas' as const;

const NODE_TYPES = ['text', 'file', 'link', 'group'] as const;
const EDGE_SIDES = ['top', 'right', 'bottom', 'left'] as const;
const EDGE_ENDS = ['none', 'arrow'] as const;
const BACKGROUND_STYLES = ['cover', 'ratio', 'repeat'] as const;

const PRESET_COLOR = /^[1-6]$/;
const HEX_COLOR = /^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;
const TRANSCRIPT_EXCERPT = 900;
const LANE_WIDTH = 480;
const LANE_GAP = 72;
const TEXT_WIDTH = 440;
const ORIGIN_X = 40;
const ORIGIN_Y = 40;

export type JsonCanvasNodeType = (typeof NODE_TYPES)[number];
export type JsonCanvasSide = (typeof EDGE_SIDES)[number];
export type JsonCanvasEnd = (typeof EDGE_ENDS)[number];
export type JsonCanvasBackgroundStyle = (typeof BACKGROUND_STYLES)[number];

export type JsonCanvasEmitInput = {
  videoId: string;
  sourceUrl: string;
  sourceHash?: string;
  packId?: string;
  transcript?: {
    full_text: string;
    language?: string | null;
    segments?: Array<{ start_s?: number; text: string }>;
  } | null;
  visualEvents?: Array<{
    timestamp: number;
    content: string;
    element_type?: string;
    image_path?: string | null;
  }>;
  sopSteps?: Array<{
    id: string;
    order: number;
    title: string;
    description: string;
    timestamp?: number;
  }>;
};

type GenericNode = {
  id: string;
  type: JsonCanvasNodeType;
  x: number;
  y: number;
  width: number;
  height: number;
  color?: string;
};

export type JsonCanvasTextNode = GenericNode & { type: 'text'; text: string };
export type JsonCanvasFileNode = GenericNode & {
  type: 'file';
  file: string;
  subpath?: string;
};
export type JsonCanvasLinkNode = GenericNode & { type: 'link'; url: string };
export type JsonCanvasGroupNode = GenericNode & {
  type: 'group';
  label?: string;
  background?: string;
  backgroundStyle?: JsonCanvasBackgroundStyle;
};

export type JsonCanvasNode =
  | JsonCanvasTextNode
  | JsonCanvasFileNode
  | JsonCanvasLinkNode
  | JsonCanvasGroupNode;

export type JsonCanvasEdge = {
  id: string;
  fromNode: string;
  toNode: string;
  fromSide?: JsonCanvasSide;
  fromEnd?: JsonCanvasEnd;
  toSide?: JsonCanvasSide;
  toEnd?: JsonCanvasEnd;
  color?: string;
  label?: string;
};

export type JsonCanvas = {
  nodes?: JsonCanvasNode[];
  edges?: JsonCanvasEdge[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value);
}

function isCanvasColor(value: unknown): value is string {
  return typeof value === 'string' && (PRESET_COLOR.test(value) || HEX_COLOR.test(value));
}

function isNodeType(value: unknown): value is JsonCanvasNodeType {
  return typeof value === 'string' && (NODE_TYPES as readonly string[]).includes(value);
}

function isSide(value: unknown): value is JsonCanvasSide {
  return typeof value === 'string' && (EDGE_SIDES as readonly string[]).includes(value);
}

function isEnd(value: unknown): value is JsonCanvasEnd {
  return typeof value === 'string' && (EDGE_ENDS as readonly string[]).includes(value);
}

function isBackgroundStyle(value: unknown): value is JsonCanvasBackgroundStyle {
  return typeof value === 'string' && (BACKGROUND_STYLES as readonly string[]).includes(value);
}

function requireGeneric(node: Record<string, unknown>, index: number): GenericNode {
  const id = node.id;
  const type = node.type;
  if (typeof id !== 'string' || id.trim() === '') {
    throw new Error(`JSON Canvas node[${index}] id must be a non-empty string.`);
  }
  if (!isNodeType(type)) {
    throw new Error(`JSON Canvas node[${index}] type must be text, file, link, or group.`);
  }
  if (!isInteger(node.x) || !isInteger(node.y) || !isInteger(node.width) || !isInteger(node.height)) {
    throw new Error(`JSON Canvas node[${index}] x, y, width, and height must be integers.`);
  }
  if (node.width <= 0 || node.height <= 0) {
    throw new Error(`JSON Canvas node[${index}] width and height must be positive.`);
  }
  const generic: GenericNode = {
    id,
    type,
    x: node.x,
    y: node.y,
    width: node.width,
    height: node.height,
  };
  if (node.color !== undefined) {
    if (!isCanvasColor(node.color)) {
      throw new Error(`JSON Canvas node[${index}] color must be #hex or preset 1-6.`);
    }
    generic.color = node.color;
  }
  return generic;
}

function parseNode(value: unknown, index: number): JsonCanvasNode {
  if (!isRecord(value)) {
    throw new Error(`JSON Canvas node[${index}] must be an object.`);
  }
  const generic = requireGeneric(value, index);
  switch (generic.type) {
    case 'text': {
      if (typeof value.text !== 'string') {
        throw new Error(`JSON Canvas text node[${index}] requires text.`);
      }
      return { ...generic, type: 'text', text: value.text };
    }
    case 'file': {
      if (typeof value.file !== 'string' || value.file.trim() === '') {
        throw new Error(`JSON Canvas file node[${index}] requires file.`);
      }
      const fileNode: JsonCanvasFileNode = { ...generic, type: 'file', file: value.file };
      if (value.subpath !== undefined) {
        if (typeof value.subpath !== 'string' || !value.subpath.startsWith('#')) {
          throw new Error(`JSON Canvas file node[${index}] subpath must start with #.`);
        }
        fileNode.subpath = value.subpath;
      }
      return fileNode;
    }
    case 'link': {
      if (typeof value.url !== 'string' || value.url.trim() === '') {
        throw new Error(`JSON Canvas link node[${index}] requires url.`);
      }
      return { ...generic, type: 'link', url: value.url };
    }
    case 'group': {
      const group: JsonCanvasGroupNode = { ...generic, type: 'group' };
      if (value.label !== undefined) {
        if (typeof value.label !== 'string') {
          throw new Error(`JSON Canvas group node[${index}] label must be a string.`);
        }
        group.label = value.label;
      }
      if (value.background !== undefined) {
        if (typeof value.background !== 'string') {
          throw new Error(`JSON Canvas group node[${index}] background must be a string.`);
        }
        group.background = value.background;
      }
      if (value.backgroundStyle !== undefined) {
        if (!isBackgroundStyle(value.backgroundStyle)) {
          throw new Error(`JSON Canvas group node[${index}] backgroundStyle is invalid.`);
        }
        group.backgroundStyle = value.backgroundStyle;
      }
      return group;
    }
    default: {
      const exhausted: never = generic.type;
      throw new Error(`JSON Canvas node type is unhandled: ${String(exhausted)}`);
    }
  }
}

function parseEdge(value: unknown, index: number, nodeIds: Set<string>): JsonCanvasEdge {
  if (!isRecord(value)) {
    throw new Error(`JSON Canvas edge[${index}] must be an object.`);
  }
  if (typeof value.id !== 'string' || value.id.trim() === '') {
    throw new Error(`JSON Canvas edge[${index}] id must be a non-empty string.`);
  }
  if (typeof value.fromNode !== 'string' || typeof value.toNode !== 'string') {
    throw new Error(`JSON Canvas edge[${index}] requires fromNode and toNode.`);
  }
  if (!nodeIds.has(value.fromNode) || !nodeIds.has(value.toNode)) {
    throw new Error(`JSON Canvas edge[${index}] must connect existing nodes.`);
  }
  const edge: JsonCanvasEdge = {
    id: value.id,
    fromNode: value.fromNode,
    toNode: value.toNode,
  };
  if (value.fromSide !== undefined) {
    if (!isSide(value.fromSide)) {
      throw new Error(`JSON Canvas edge[${index}] fromSide is invalid.`);
    }
    edge.fromSide = value.fromSide;
  }
  if (value.toSide !== undefined) {
    if (!isSide(value.toSide)) {
      throw new Error(`JSON Canvas edge[${index}] toSide is invalid.`);
    }
    edge.toSide = value.toSide;
  }
  if (value.fromEnd !== undefined) {
    if (!isEnd(value.fromEnd)) {
      throw new Error(`JSON Canvas edge[${index}] fromEnd is invalid.`);
    }
    edge.fromEnd = value.fromEnd;
  }
  if (value.toEnd !== undefined) {
    if (!isEnd(value.toEnd)) {
      throw new Error(`JSON Canvas edge[${index}] toEnd is invalid.`);
    }
    edge.toEnd = value.toEnd;
  }
  if (value.color !== undefined) {
    if (!isCanvasColor(value.color)) {
      throw new Error(`JSON Canvas edge[${index}] color must be #hex or preset 1-6.`);
    }
    edge.color = value.color;
  }
  if (value.label !== undefined) {
    if (typeof value.label !== 'string') {
      throw new Error(`JSON Canvas edge[${index}] label must be a string.`);
    }
    edge.label = value.label;
  }
  return edge;
}

/** Validate an unknown document against JSON Canvas spec 1.0. */
export function validateJsonCanvas(value: unknown): JsonCanvas {
  if (!isRecord(value)) {
    throw new Error('JSON Canvas document must be an object.');
  }
  const canvas: JsonCanvas = {};
  if (value.nodes !== undefined) {
    if (!Array.isArray(value.nodes)) {
      throw new Error('JSON Canvas nodes must be an array.');
    }
    const nodes = value.nodes.map((node, index) => parseNode(node, index));
    const ids = new Set<string>();
    for (const node of nodes) {
      if (ids.has(node.id)) {
        throw new Error(`JSON Canvas node id is duplicated: ${node.id}`);
      }
      ids.add(node.id);
    }
    canvas.nodes = nodes;
  }
  if (value.edges !== undefined) {
    if (!Array.isArray(value.edges)) {
      throw new Error('JSON Canvas edges must be an array.');
    }
    const nodeIds = new Set((canvas.nodes ?? []).map((node) => node.id));
    const edges = value.edges.map((edge, index) => parseEdge(edge, index, nodeIds));
    const ids = new Set<string>();
    for (const edge of edges) {
      if (ids.has(edge.id) || nodeIds.has(edge.id)) {
        throw new Error(`JSON Canvas edge id is duplicated: ${edge.id}`);
      }
      ids.add(edge.id);
    }
    canvas.edges = edges;
  }
  return canvas;
}

function excerpt(text: string, max = TRANSCRIPT_EXCERPT): string {
  const trimmed = text.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max).trimEnd()}…`;
}

function textHeight(text: string): number {
  const wrapped = Math.ceil(text.length / 52);
  const explicit = (text.match(/\n/g) ?? []).length;
  return Math.min(420, Math.max(100, 36 + (wrapped + explicit) * 18));
}

function usableVisuals(input: JsonCanvasEmitInput) {
  return (input.visualEvents ?? []).filter((event) => event.content.trim());
}

function usableSop(input: JsonCanvasEmitInput) {
  return (input.sopSteps ?? []).filter((step) => step.title.trim());
}

function usableTranscript(input: JsonCanvasEmitInput): string {
  return input.transcript?.full_text?.trim() ?? '';
}

export function hasJsonCanvasContent(input: JsonCanvasEmitInput): boolean {
  return Boolean(usableTranscript(input) || usableVisuals(input).length > 0 || usableSop(input).length > 0);
}

function laneX(index: number): number {
  return ORIGIN_X + index * (LANE_WIDTH + LANE_GAP);
}

/**
 * Build a spec 1.0 canvas from the allowed emit slice only.
 * Returns null when transcript, visual events, and SOP are all empty.
 * File nodes are never emitted — B2 left keyframe image_path null.
 */
export function emitJsonCanvas(input: JsonCanvasEmitInput): JsonCanvas | null {
  if (!hasJsonCanvasContent(input)) {
    return null;
  }

  const nodes: JsonCanvasNode[] = [];
  const edges: JsonCanvasEdge[] = [];
  const transcript = usableTranscript(input);
  const visuals = usableVisuals(input);
  const sop = usableSop(input);
  const videoId = input.videoId.trim();
  const sourceUrl = input.sourceUrl.trim();
  const packId = (input.packId || (videoId ? `vp:v0:${videoId}` : '')).trim();

  const lanes: Array<{ id: string; kind: 'source' | 'transcript' | 'visual' | 'sop' }> = [
    { id: 'source', kind: 'source' },
  ];
  if (transcript) lanes.push({ id: 'transcript', kind: 'transcript' });
  if (visuals.length > 0) lanes.push({ id: 'visual', kind: 'visual' });
  if (sop.length > 0) lanes.push({ id: 'sop', kind: 'sop' });

  for (const [index, lane] of lanes.entries()) {
    const x = laneX(index);
    const innerX = x + 20;
    switch (lane.kind) {
      case 'source': {
        const identity = [
          videoId ? `# Video Pack ${videoId}` : '# Video Pack',
          packId ? `Pack \`${packId}\`` : '',
        ]
          .filter((line) => line.length > 0)
          .join('\n\n');
        const identityH = textHeight(identity);
        nodes.push({
          id: 'source',
          type: 'group',
          x,
          y: ORIGIN_Y,
          width: LANE_WIDTH,
          height: 80 + identityH + 140,
          color: '6',
          label: 'Source',
        });
        nodes.push({
          id: 'source-identity',
          type: 'text',
          x: innerX,
          y: ORIGIN_Y + 48,
          width: TEXT_WIDTH,
          height: identityH,
          color: '6',
          text: identity,
        });
        if (sourceUrl.startsWith('http')) {
          nodes.push({
            id: 'source-link',
            type: 'link',
            x: innerX,
            y: ORIGIN_Y + 56 + identityH,
            width: TEXT_WIDTH,
            height: 88,
            color: '6',
            url: sourceUrl,
          });
        }
        break;
      }
      case 'transcript': {
        const body = excerpt(transcript);
        const height = textHeight(body);
        nodes.push({
          id: 'transcript',
          type: 'group',
          x,
          y: ORIGIN_Y,
          width: LANE_WIDTH,
          height: 80 + height,
          color: '5',
          label: 'Transcript',
        });
        nodes.push({
          id: 'transcript-text',
          type: 'text',
          x: innerX,
          y: ORIGIN_Y + 48,
          width: TEXT_WIDTH,
          height,
          color: '5',
          text: body,
        });
        break;
      }
      case 'visual': {
        const bodies = visuals.map((event) => {
          const stamp = Number.isFinite(event.timestamp) ? `${event.timestamp}s` : '';
          const kind = event.element_type?.trim() ? ` · ${event.element_type.trim()}` : '';
          return [`${stamp}${kind}`, event.content.trim()].filter(Boolean).join('\n\n');
        });
        const heights = bodies.map((body) => textHeight(body));
        const groupHeight = 68 + heights.reduce((sum, height) => sum + height + 16, 0);
        nodes.push({
          id: 'visual',
          type: 'group',
          x,
          y: ORIGIN_Y,
          width: LANE_WIDTH,
          height: groupHeight,
          color: '3',
          label: 'Visual events',
        });
        let cursorY = ORIGIN_Y + 48;
        for (const [eventIndex, body] of bodies.entries()) {
          const height = heights[eventIndex] ?? 100;
          const captured = visuals[eventIndex]?.image_path;
          if (isDurableCapturedImagePath(captured)) {
            nodes.push({
              id: `visual-${eventIndex}`,
              type: 'file',
              x: innerX,
              y: cursorY,
              width: TEXT_WIDTH,
              height,
              color: '3',
              file: captured,
            });
          } else {
            nodes.push({
              id: `visual-${eventIndex}`,
              type: 'text',
              x: innerX,
              y: cursorY,
              width: TEXT_WIDTH,
              height,
              color: '3',
              text: body,
            });
          }
          cursorY += height + 16;
        }
        break;
      }
      case 'sop': {
        const bodies = sop.map((step) => {
          const stamp = step.timestamp != null ? ` (${step.timestamp}s)` : '';
          return [`${step.order}. ${step.title.trim()}${stamp}`, step.description.trim()]
            .filter((line) => line.length > 0)
            .join('\n\n');
        });
        const heights = bodies.map((body) => textHeight(body));
        const groupHeight = 68 + heights.reduce((sum, height) => sum + height + 16, 0);
        nodes.push({
          id: 'sop',
          type: 'group',
          x,
          y: ORIGIN_Y,
          width: LANE_WIDTH,
          height: groupHeight,
          color: '4',
          label: 'SOP',
        });
        let cursorY = ORIGIN_Y + 48;
        for (const [stepIndex, step] of sop.entries()) {
          const height = heights[stepIndex] ?? 100;
          const body = bodies[stepIndex] ?? step.title.trim();
          nodes.push({
            id: `sop-step-${stepIndex}`,
            type: 'text',
            x: innerX,
            y: cursorY,
            width: TEXT_WIDTH,
            height,
            color: '4',
            text: body,
          });
          cursorY += height + 16;
        }
        break;
      }
      default: {
        const exhausted: never = lane.kind;
        throw new Error(`JSON Canvas lane is unhandled: ${String(exhausted)}`);
      }
    }
  }

  for (let index = 0; index < lanes.length - 1; index += 1) {
    const from = lanes[index];
    const to = lanes[index + 1];
    edges.push({
      id: `edge-${from.id}-${to.id}`,
      fromNode: from.id,
      toNode: to.id,
      fromSide: 'right',
      toSide: 'left',
      toEnd: 'arrow',
      label: to.kind,
    });
  }

  return validateJsonCanvas({ nodes, edges });
}

/** Serialize mission.canvas or return null when the emit slice is empty. */
export function emitMissionCanvasFile(input: JsonCanvasEmitInput): string | null {
  try {
    const canvas = emitJsonCanvas(input);
    if (!canvas) return null;
    return `${JSON.stringify(canvas, null, 2)}\n`;
  } catch (error) {
    console.error('JSON Canvas emit omitted: document failed spec 1.0 validation.', error);
    return null;
  }
}
