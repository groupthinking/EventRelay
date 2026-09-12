import { describe, expect, it } from 'vitest';
import { identityHash } from '@/lib/video-pack';
import {
  MISSION_CANVAS_FILENAME,
  emitJsonCanvas,
  emitMissionCanvasFile,
  validateJsonCanvas,
} from '@/lib/emit-json-canvas';
import {
  emitAppBuilderSandbox,
  sandboxFromVideoPack,
} from '@/lib/emit-app-builder-sandbox';
import { buildStudioShipPackage } from '@/lib/action-surface';
import {
  QJ_FORBIDDEN_ARCHITECTURE,
  QJ_FORBIDDEN_CODE_SNIPPETS,
  QJ_PACK_ID,
  QJ_SOP_STEPS,
  QJ_SOURCE_HASH,
  QJ_SOURCE_URL,
  QJ_TRANSCRIPT,
  QJ_VIDEO_ID,
  QJ_VISUAL_EVENTS,
} from '@/lib/__fixtures__/qj-z5ohr7sga-emit';
import {
  XYMC_FORBIDDEN_ARCHITECTURE,
  XYMC_FORBIDDEN_CODE_SNIPPETS,
  XYMC_KEYFRAMES,
  XYMC_PACK_ID,
  XYMC_SOP_STEPS,
  XYMC_SOURCE_HASH,
  XYMC_SOURCE_URL,
  XYMC_TRANSCRIPT,
  XYMC_VIDEO_ID,
  XYMC_VISUAL_EVENTS,
} from '@/lib/__fixtures__/xymcbrfsj4c-emit';

/**
 * Official sample from groupthinking/jsoncanvas (spec 1.0 / sample.canvas).
 * Validator must accept this document — we do not invent a parallel format.
 */
const OFFICIAL_SAMPLE_CANVAS = {
  nodes: [
    {
      id: '754a8ef995f366bc',
      type: 'group',
      x: -300,
      y: -460,
      width: 610,
      height: 200,
      label: 'JSON Canvas',
    },
    {
      id: '8132d4d894c80022',
      type: 'file',
      file: 'readme.md',
      x: -280,
      y: -200,
      width: 570,
      height: 560,
      color: '6',
    },
    {
      id: '7efdbbe0c4742315',
      type: 'file',
      file: '_site/logo.svg',
      x: -280,
      y: -440,
      width: 217,
      height: 80,
    },
    {
      id: '59e896bc8da20699',
      type: 'text',
      text: 'Learn more:\n\n- [Apps](/docs/apps.md)\n- [Spec](spec/1.0.md)\n- [Github](https://github.com/obsidianmd/jsoncanvas)',
      x: 40,
      y: -440,
      width: 250,
      height: 160,
    },
    {
      id: '0ba565e7f30e0652',
      type: 'file',
      file: 'spec/1.0.md',
      x: 360,
      y: -400,
      width: 400,
      height: 400,
    },
  ],
  edges: [
    {
      id: '6fa11ab87f90b8af',
      fromNode: '7efdbbe0c4742315',
      fromSide: 'right',
      toNode: '59e896bc8da20699',
      toSide: 'left',
    },
  ],
};

function qjInput() {
  return {
    videoId: QJ_VIDEO_ID,
    sourceUrl: QJ_SOURCE_URL,
    sourceHash: QJ_SOURCE_HASH,
    packId: QJ_PACK_ID,
    transcript: QJ_TRANSCRIPT,
    visualEvents: QJ_VISUAL_EVENTS,
    sopSteps: QJ_SOP_STEPS,
  };
}

function xymcInput() {
  return {
    videoId: XYMC_VIDEO_ID,
    sourceUrl: XYMC_SOURCE_URL,
    sourceHash: XYMC_SOURCE_HASH,
    packId: XYMC_PACK_ID,
    transcript: XYMC_TRANSCRIPT,
    visualEvents: XYMC_VISUAL_EVENTS,
    sopSteps: XYMC_SOP_STEPS,
  };
}

function parseCanvas(raw: string | undefined) {
  expect(raw).toBeTruthy();
  return validateJsonCanvas(JSON.parse(raw as string));
}

describe('validateJsonCanvas (jsoncanvas spec 1.0)', () => {
  it('accepts the official groupthinking/jsoncanvas sample.canvas', () => {
    const canvas = validateJsonCanvas(OFFICIAL_SAMPLE_CANVAS);
    expect(canvas.nodes?.length).toBe(5);
    expect(canvas.edges?.length).toBe(1);
    expect(canvas.nodes?.some((node) => node.type === 'file')).toBe(true);
    expect(canvas.nodes?.some((node) => node.type === 'text')).toBe(true);
    expect(canvas.nodes?.some((node) => node.type === 'group')).toBe(true);
  });

  it('rejects invented node types and non-integer geometry', () => {
    expect(() =>
      validateJsonCanvas({
        nodes: [{ id: 'x', type: 'architecture', x: 0, y: 0, width: 10, height: 10 }],
      }),
    ).toThrow(/type/i);
    expect(() =>
      validateJsonCanvas({
        nodes: [{ id: 'x', type: 'text', text: 'hi', x: 0.5, y: 0, width: 10, height: 10 }],
      }),
    ).toThrow(/integer/i);
  });
});

describe('emitJsonCanvas (pack→JSON Canvas emit)', () => {
  it('emits a non-empty spec 1.0 canvas from QjZ5ohr7sGA transcript, visual, and SOP', () => {
    expect(identityHash(QJ_VIDEO_ID)).toBe(QJ_SOURCE_HASH);
    const canvas = emitJsonCanvas(qjInput());
    expect(canvas).not.toBeNull();
    const valid = validateJsonCanvas(canvas);
    expect((valid.nodes ?? []).length).toBeGreaterThan(0);
    const texts = (valid.nodes ?? [])
      .filter((node) => node.type === 'text')
      .map((node) => node.text)
      .join('\n');
    expect(texts).toContain('five flat tires');
    expect(texts).toContain('scissor jack');
    expect(texts).toContain('Safety and Vehicle Staging');
    expect(texts).not.toContain('SimpleKnotState');
    expect(texts).not.toContain('tire_procedure.ts');
    expect(texts).not.toContain('TireChangeContext');
    expect(texts).not.toContain('Procedural pipeline for roadside tire changing');
    expect(JSON.stringify(valid)).not.toMatch(/dpl_/);
    expect(valid.nodes?.some((node) => node.type === 'file')).toBe(false);
  });

  it('emits a non-empty spec 1.0 canvas from XYMcBrFSJ4c transcript, visual, and SOP', () => {
    expect(identityHash(XYMC_VIDEO_ID)).toBe(XYMC_SOURCE_HASH);
    const canvas = emitJsonCanvas(xymcInput());
    expect(canvas).not.toBeNull();
    const valid = validateJsonCanvas(canvas);
    expect((valid.nodes ?? []).length).toBeGreaterThan(0);
    const texts = (valid.nodes ?? [])
      .filter((node) => node.type === 'text')
      .map((node) => node.text)
      .join('\n');
    expect(texts).toContain('unpaid invoices');
    expect(texts).toContain('Torty Gym');
    expect(texts).toContain('Email Triage Workflow');
    expect(texts).not.toContain('EmailClassification');
    expect(texts).not.toContain('email_triage.ts');
    expect(texts).not.toContain('Modular agency architecture connecting lead capture');
    expect(texts).not.toContain('five flat tires');
    expect(valid.nodes?.some((node) => node.type === 'file')).toBe(false);
  });

  it('omits the canvas when the pack has no transcript, visual events, or SOP', () => {
    expect(
      emitJsonCanvas({
        videoId: QJ_VIDEO_ID,
        sourceUrl: QJ_SOURCE_URL,
        sourceHash: QJ_SOURCE_HASH,
      }),
    ).toBeNull();
    expect(
      emitMissionCanvasFile({
        videoId: QJ_VIDEO_ID,
        sourceUrl: QJ_SOURCE_URL,
        sourceHash: QJ_SOURCE_HASH,
      }),
    ).toBeNull();
  });

  it('never emits file nodes for B2-null keyframe image_path', () => {
    const canvas = emitJsonCanvas({
      ...xymcInput(),
      visualEvents: XYMC_KEYFRAMES.map((frame) => ({
        timestamp: frame.t_s,
        content: frame.desc ?? '',
        element_type: 'keyframe',
      })),
    });
    expect(canvas).not.toBeNull();
    const valid = validateJsonCanvas(canvas);
    expect(valid.nodes?.some((node) => node.type === 'file')).toBe(false);
    expect(JSON.stringify(valid)).not.toMatch(/image_path/);
    expect(JSON.stringify(valid)).not.toMatch(/\/tmp\/|\.png|\.jpg|keyframes\//);
    expect(
      (valid.nodes ?? [])
        .filter((node) => node.type === 'text')
        .map((node) => node.text)
        .join('\n'),
    ).toContain('n8n workflow editor for email triage');
  });
});

describe('App Builder / Studio file map (mission.canvas)', () => {
  it('lands mission.canvas on the Qj sandbox and Studio export, omitting architecture', () => {
    const sandbox = sandboxFromVideoPack({
      version: 'v0',
      id: QJ_PACK_ID,
      video_id: QJ_VIDEO_ID,
      source_url: QJ_SOURCE_URL,
      provenance: { source_hash: QJ_SOURCE_HASH },
      transcript: QJ_TRANSCRIPT,
      keyframes: QJ_VISUAL_EVENTS.map((event) => ({
        t_s: event.timestamp,
        desc: event.content,
        image_path: null,
      })),
      visual_context: {
        visual_elements: QJ_VISUAL_EVENTS.map((event) => ({
          timestamp: event.timestamp,
          element_type: event.element_type ?? 'scene',
          content: event.content,
          confidence: 0.9,
        })),
        summary: 'Roadside tire replacement tools.',
        frame_analysis_count: 4,
      },
      requirements: QJ_SOP_STEPS.map((step) => ({
        id: step.id,
        title: step.title,
        detail: step.description,
      })),
      architecture: QJ_FORBIDDEN_ARCHITECTURE,
      artifacts: [
        {
          path_hint: 'tire_procedure.ts',
          purpose: 'Invented type dump',
          interface: 'interface ITireReplacement',
        },
      ],
      stack: { tools: [] },
      concepts: [],
      code_snippets: QJ_FORBIDDEN_CODE_SNIPPETS,
      metrics: {},
    });
    expect(MISSION_CANVAS_FILENAME).toBe('mission.canvas');
    const canvas = parseCanvas(sandbox.files[MISSION_CANVAS_FILENAME]);
    expect((canvas.nodes ?? []).length).toBeGreaterThan(0);
    const shipped = Object.values(sandbox.files).join('\n');
    expect(shipped).toContain('five flat tires');
    expect(shipped).not.toContain('tire_procedure.ts');
    expect(shipped).not.toContain('TireChangeContext');
    expect(shipped).not.toContain('ITireReplacement');

    const pkg = buildStudioShipPackage({
      projectName: 'uvai-project',
      actions: [],
      videoPack: {
        videoId: QJ_VIDEO_ID,
        sourceUrl: QJ_SOURCE_URL,
        sourceHash: QJ_SOURCE_HASH,
        packId: QJ_PACK_ID,
        visual: {
          visual_context: {
            visual_elements: QJ_VISUAL_EVENTS.map((event) => ({
              timestamp: event.timestamp,
              element_type: event.element_type ?? 'scene',
              content: event.content,
              confidence: 0.9,
            })),
          },
        },
        requirements: QJ_SOP_STEPS.map((step) => ({
          id: step.id,
          title: step.title,
          detail: step.description,
        })),
      },
      transcript: QJ_TRANSCRIPT,
      packFormation: {
        architecture: QJ_FORBIDDEN_ARCHITECTURE,
        artifacts: [
          {
            path_hint: 'tire_procedure.ts',
            purpose: 'Invented type dump',
            interface: 'interface ITireReplacement',
          },
        ],
      },
    });
    expect(pkg.files[MISSION_CANVAS_FILENAME]).toBeTruthy();
    expect(pkg.files['ARCHITECTURE.md']).toBeUndefined();
    expect(Object.values(pkg.files).join('\n')).not.toContain('tire_procedure.ts');
  });

  it('lands mission.canvas on the XYMc sandbox without inventing keyframe files', () => {
    const sandbox = sandboxFromVideoPack({
      version: 'v0',
      id: XYMC_PACK_ID,
      video_id: XYMC_VIDEO_ID,
      source_url: XYMC_SOURCE_URL,
      provenance: { source_hash: XYMC_SOURCE_HASH },
      transcript: XYMC_TRANSCRIPT,
      keyframes: XYMC_KEYFRAMES.map((frame) => ({
        t_s: frame.t_s,
        desc: frame.desc,
        image_path: frame.image_path,
      })),
      visual_context: {
        visual_elements: XYMC_VISUAL_EVENTS.map((event) => ({
          timestamp: event.timestamp,
          element_type: event.element_type,
          content: event.content,
          confidence: 0.9,
        })),
        summary: 'Live functional demos of n8n, Make, Retell AI, and Voiceflow.',
        frame_analysis_count: 12,
      },
      requirements: XYMC_SOP_STEPS.map((step) => ({
        id: step.id,
        title: step.title,
        detail: step.description,
      })),
      architecture: {
        summary: XYMC_FORBIDDEN_ARCHITECTURE.summary,
        stages: XYMC_FORBIDDEN_ARCHITECTURE.stages.map((stage) => ({ ...stage })),
        mermaid: XYMC_FORBIDDEN_ARCHITECTURE.mermaid,
      },
      artifacts: [],
      stack: { tools: [] },
      concepts: [],
      code_snippets: XYMC_FORBIDDEN_CODE_SNIPPETS.map((snippet) => ({ ...snippet })),
      metrics: {},
    });
    const canvas = parseCanvas(sandbox.files[MISSION_CANVAS_FILENAME]);
    expect(canvas.nodes?.some((node) => node.type === 'file')).toBe(false);
    const texts = (canvas.nodes ?? [])
      .filter((node) => node.type === 'text')
      .map((node) => node.text)
      .join('\n');
    expect(texts).toContain('unpaid invoices');
    expect(texts).toContain('Email Triage Workflow');
    expect(texts).toContain('Diagram showing CRM, AI Agent, and Client unpaid invoice follow-up flow');
    expect(texts).not.toContain('EmailClassification');
    expect(texts).not.toContain('email_triage.ts');
    expect(JSON.stringify(canvas)).not.toMatch(/image_path/);
  });

  it('omits mission.canvas from an empty-slice sandbox', () => {
    const sandbox = emitAppBuilderSandbox({
      videoId: QJ_VIDEO_ID,
      sourceUrl: QJ_SOURCE_URL,
      sourceHash: QJ_SOURCE_HASH,
    });
    expect(sandbox.files[MISSION_CANVAS_FILENAME]).toBeUndefined();
  });
});
