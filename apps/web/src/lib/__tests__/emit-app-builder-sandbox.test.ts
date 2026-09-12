import { describe, expect, it } from 'vitest';
import { identityHash } from '@/lib/video-pack';
import {
  APP_BUILDER_CONTRACT,
  APP_BUILDER_CUT,
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

function emitFixture() {
  return emitAppBuilderSandbox({
    videoId: QJ_VIDEO_ID,
    sourceUrl: QJ_SOURCE_URL,
    sourceHash: QJ_SOURCE_HASH,
    packId: QJ_PACK_ID,
    transcript: QJ_TRANSCRIPT,
    visualEvents: QJ_VISUAL_EVENTS,
    sopSteps: QJ_SOP_STEPS,
  });
}

function forbiddenPayload(): string {
  return [
    QJ_FORBIDDEN_ARCHITECTURE.summary,
    QJ_FORBIDDEN_CODE_SNIPPETS[0]?.content,
    'SimpleKnotState',
    'tire_procedure.ts',
    'TireChangeContext',
    'ITireReplacement',
    'dpl_',
  ].join('\n');
}

describe('emitAppBuilderSandbox (ingest→App Builder sandbox emit)', () => {
  it('uses the live QjZ5ohr7sGA identity hash', () => {
    expect(identityHash(QJ_VIDEO_ID)).toBe(QJ_SOURCE_HASH);
    expect(QJ_PACK_ID).toBe('vp:v0:QjZ5ohr7sGA');
  });

  it('emits the trail-velvet startup.sh contract: probe 127.0.0.1:8080 then npm run dev', () => {
    const sandbox = emitFixture();
    expect(sandbox.contract).toBe(APP_BUILDER_CONTRACT);
    expect(sandbox.cut).toBe(APP_BUILDER_CUT);
    expect(sandbox.preview.port).toBe(8080);
    expect(sandbox.preview.host).toBe('0.0.0.0');
    expect(sandbox.preview.probe).toBe('http://127.0.0.1:8080/');
    expect(sandbox.preview.start).toBe('npm run dev');
    expect(sandbox.preview.smoke).toBe('node scripts/browser-smoke.mjs');
    expect(sandbox.preview.gates).toEqual(['npm run build', 'npm run typecheck']);

    const startup = sandbox.files['startup.sh'];
    expect(startup).toMatch(/^#!/);
    expect(startup).toContain('cd /workspace');
    expect(startup).toMatch(/curl[\s\S]*http:\/\/127\.0\.0\.1:8080\//);
    expect(startup).toContain('npm run dev');
    expect(startup).not.toMatch(/\bvite\b/);
    expect(startup).not.toContain('npx vite');
  });

  it('binds npm run dev to 0.0.0.0:8080 and ships build + typecheck scripts', () => {
    const sandbox = emitFixture();
    const pkg = JSON.parse(sandbox.files['package.json']) as {
      scripts: Record<string, string>;
    };
    expect(pkg.scripts.dev).toMatch(/--host\s+0\.0\.0\.0/);
    expect(pkg.scripts.dev).toMatch(/--port\s+8080/);
    expect(pkg.scripts.build).toBeTruthy();
    expect(pkg.scripts.typecheck).toMatch(/tsc/);
    expect(sandbox.files['tsconfig.json']).toContain('"noEmit"');
    expect(sandbox.files['vite.config.ts']).toMatch(/8080/);
  });

  it('ships browser-smoke.mjs that requires visible UI on 127.0.0.1:8080', () => {
    const sandbox = emitFixture();
    const smoke = sandbox.files['scripts/browser-smoke.mjs'];
    expect(smoke).toContain('127.0.0.1:8080');
    expect(smoke).toContain('app-builder-sandbox');
    expect(smoke).toContain(QJ_VIDEO_ID);
    expect(smoke).toMatch(/visible|textContent|innerText|data-testid/);
  });

  it('renders transcript, visual events, and SOP — not architecture or code snippets', () => {
    const sandbox = emitFixture();
    const html = sandbox.files['index.html'];
    const packTs = sandbox.files['src/pack.ts'];
    const shipped = `${html}\n${packTs}\n${Object.values(sandbox.files).join('\n')}`;
    expect(html).toContain('data-testid="app-builder-sandbox"');
    expect(html).toContain(QJ_VIDEO_ID);
    expect(html).toContain(QJ_SOURCE_URL);
    expect(html).toContain(QJ_SOURCE_HASH);
    expect(html).toContain('five flat tires');
    expect(html).toContain('scissor jack');
    expect(html).toContain('Safety and Vehicle Staging');
    expect(html).toContain('Star Pattern Torquing');
    expect(html).not.toMatch(/shopify/i);
    expect(html).not.toMatch(/https:\/\/[a-z0-9-]+\.vercel\.app/i);
    expect(html).not.toMatch(/G\.A\.T\.E\. HOLD/i);
    expect(html).not.toContain('data-testid="pack-architecture"');
    expect(shipped).not.toContain('SimpleKnotState');
    expect(shipped).not.toContain('tire_procedure.ts');
    expect(shipped).not.toContain('TireChangeContext');
    expect(shipped).not.toContain('Procedural pipeline for roadside tire changing');
    expect(shipped).not.toMatch(/dpl_/);
  });

  it('uses an honest empty workbench when transcript, visual, and SOP are missing', () => {
    const sandbox = emitAppBuilderSandbox({
      videoId: QJ_VIDEO_ID,
      sourceUrl: QJ_SOURCE_URL,
      sourceHash: QJ_SOURCE_HASH,
    });
    const html = sandbox.files['index.html'];
    expect(html).toContain(QJ_VIDEO_ID);
    expect(html).toMatch(/transcript not extracted/i);
    expect(html).toMatch(/no visual events/i);
    expect(html).toMatch(/no sop steps/i);
    expect(html).not.toContain('five flat tires');
  });

  it('fails closed without source_url and source_hash', () => {
    expect(() =>
      emitAppBuilderSandbox({
        videoId: QJ_VIDEO_ID,
        sourceUrl: '',
        sourceHash: QJ_SOURCE_HASH,
      }),
    ).toThrow(/source_url/i);
    expect(() =>
      emitAppBuilderSandbox({
        videoId: QJ_VIDEO_ID,
        sourceUrl: QJ_SOURCE_URL,
        sourceHash: 'not-a-hash',
      }),
    ).toThrow(/source_hash/i);
  });

  it('strips architecture and code_snippets when materializing from a ready pack', () => {
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
    const shipped = Object.values(sandbox.files).join('\n');
    expect(sandbox.files['index.html']).toContain('five flat tires');
    expect(sandbox.files['index.html']).toContain('Safety and Vehicle Staging');
    expect(sandbox.files['src/pack.ts']).toContain(QJ_VIDEO_ID);
    expect(shipped).not.toContain('tire_procedure.ts');
    expect(shipped).not.toContain('ITireReplacement');
    expect(shipped).not.toContain('TireChangeContext');
    expect(forbiddenPayload()).toContain('tire_procedure.ts');
  });
});

describe('buildStudioShipPackage', () => {
  it('merges the App Builder sandbox and drops architecture files', () => {
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
            summary: 'Roadside tire replacement tools.',
            frame_analysis_count: 4,
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
    expect(pkg.files['startup.sh']).toContain('npm run dev');
    expect(pkg.files['scripts/browser-smoke.mjs']).toContain(QJ_VIDEO_ID);
    expect(pkg.files['index.html']).toContain('five flat tires');
    expect(pkg.files['index.html']).toContain('scissor jack');
    expect(pkg.files['index.html']).toContain('Safety and Vehicle Staging');
    expect(pkg.files['ARCHITECTURE.md']).toBeUndefined();
    expect(pkg.files['artifacts.json']).toBeUndefined();
    expect(Object.values(pkg.files).join('\n')).not.toContain('tire_procedure.ts');
  });
});

function emitXymcFixture() {
  return emitAppBuilderSandbox({
    videoId: XYMC_VIDEO_ID,
    sourceUrl: XYMC_SOURCE_URL,
    sourceHash: XYMC_SOURCE_HASH,
    packId: XYMC_PACK_ID,
    transcript: XYMC_TRANSCRIPT,
    visualEvents: [...XYMC_VISUAL_EVENTS],
    sopSteps: [...XYMC_SOP_STEPS],
  });
}

describe('emitAppBuilderSandbox (second-video XYMcBrFSJ4c)', () => {
  it('uses the live XYMcBrFSJ4c identity hash and does not alias QjZ5ohr7sGA', () => {
    expect(identityHash(XYMC_VIDEO_ID)).toBe(XYMC_SOURCE_HASH);
    expect(XYMC_PACK_ID).toBe('vp:v0:XYMcBrFSJ4c');
    expect(XYMC_VIDEO_ID).not.toBe(QJ_VIDEO_ID);
    expect(XYMC_SOURCE_HASH).not.toBe(QJ_SOURCE_HASH);
    expect(identityHash(QJ_VIDEO_ID)).toBe(QJ_SOURCE_HASH);
  });

  it('renders XYMc transcript, visual events, and SOP — not architecture or Qj tire copy', () => {
    const sandbox = emitXymcFixture();
    const html = sandbox.files['index.html'];
    const shipped = Object.values(sandbox.files).join('\n');
    expect(sandbox.videoId).toBe(XYMC_VIDEO_ID);
    expect(sandbox.preview.port).toBe(8080);
    expect(html).toContain(XYMC_VIDEO_ID);
    expect(html).toContain(XYMC_SOURCE_URL);
    expect(html).toContain(XYMC_SOURCE_HASH);
    expect(html).toContain('unpaid invoices');
    expect(html).toContain('nine boring AI automations');
    expect(html).toContain('Torty Gym');
    expect(html).toContain('Email Triage Workflow');
    expect(html).toContain('Sub-60s Speed-to-Lead Calling');
    expect(html).not.toContain('five flat tires');
    expect(html).not.toContain('scissor jack');
    expect(html).not.toContain('Safety and Vehicle Staging');
    expect(html).not.toContain(QJ_VIDEO_ID);
    expect(html).not.toContain('data-testid="pack-architecture"');
    expect(shipped).not.toContain('EmailClassification');
    expect(shipped).not.toContain('email_triage.ts');
    expect(shipped).not.toContain('OutboundCallPayload');
    expect(shipped).not.toContain('Modular agency architecture connecting lead capture');
    expect(shipped).not.toMatch(/dpl_/);
  });

  it('strips invented architecture and code_snippets from the live XYMc pack shape', () => {
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
      artifacts: [
        {
          path_hint: 'workflows/speed_to_lead_n8n.json',
          purpose: 'Invented workflow dump',
          interface: 'n8n workflow definition',
        },
      ],
      stack: { tools: [] },
      concepts: [],
      code_snippets: XYMC_FORBIDDEN_CODE_SNIPPETS.map((snippet) => ({ ...snippet })),
      metrics: {},
    });
    const html = sandbox.files['index.html'];
    const shipped = Object.values(sandbox.files).join('\n');
    expect(html).toContain('unpaid invoices');
    expect(html).toContain('Torty Gym');
    expect(html).toContain('Email Triage Workflow');
    expect(html).toContain('Diagram showing CRM, AI Agent, and Client unpaid invoice follow-up flow');
    expect(sandbox.files['src/pack.ts']).toContain(XYMC_VIDEO_ID);
    expect(shipped).not.toContain('email_triage.ts');
    expect(shipped).not.toContain('EmailClassification');
    expect(shipped).not.toContain('retell_voice.ts');
    expect(shipped).not.toContain('calendar_tool.ts');
    expect(shipped).not.toContain('speed_to_lead_n8n.json');
    expect(shipped).not.toContain('Modular agency architecture connecting lead capture');
    expect(shipped).not.toContain('five flat tires');
    expect(shipped).not.toContain(QJ_VIDEO_ID);
  });
});

describe('buildStudioShipPackage (second-video XYMcBrFSJ4c)', () => {
  it('merges the XYMc App Builder sandbox and drops architecture files', () => {
    const pkg = buildStudioShipPackage({
      projectName: 'uvai-project',
      actions: [],
      videoPack: {
        videoId: XYMC_VIDEO_ID,
        sourceUrl: XYMC_SOURCE_URL,
        sourceHash: XYMC_SOURCE_HASH,
        packId: XYMC_PACK_ID,
        visual: {
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
        },
        requirements: XYMC_SOP_STEPS.map((step) => ({
          id: step.id,
          title: step.title,
          detail: step.description,
        })),
      },
      transcript: XYMC_TRANSCRIPT,
      packFormation: {
        architecture: {
          summary: XYMC_FORBIDDEN_ARCHITECTURE.summary,
          stages: XYMC_FORBIDDEN_ARCHITECTURE.stages.map((stage) => ({ ...stage })),
          mermaid: XYMC_FORBIDDEN_ARCHITECTURE.mermaid,
        },
        artifacts: [
          {
            path_hint: 'workflows/email_triage.ts',
            purpose: 'Invented type dump',
            interface: 'interface EmailClassification',
          },
        ],
      },
    });
    expect(pkg.files['startup.sh']).toContain('npm run dev');
    expect(pkg.files['scripts/browser-smoke.mjs']).toContain(XYMC_VIDEO_ID);
    expect(pkg.files['scripts/browser-smoke.mjs']).not.toContain(QJ_VIDEO_ID);
    expect(pkg.files['index.html']).toContain('unpaid invoices');
    expect(pkg.files['index.html']).toContain('Torty Gym');
    expect(pkg.files['index.html']).toContain('Email Triage Workflow');
    expect(pkg.files['index.html']).not.toContain('five flat tires');
    expect(pkg.files['ARCHITECTURE.md']).toBeUndefined();
    expect(pkg.files['artifacts.json']).toBeUndefined();
    expect(Object.values(pkg.files).join('\n')).not.toContain('email_triage.ts');
    expect(Object.values(pkg.files).join('\n')).not.toContain('EmailClassification');
  });
});
