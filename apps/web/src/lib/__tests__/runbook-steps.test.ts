import { describe, expect, it } from 'vitest';
import {
  clampRunbookStep,
  compileRunbook,
  parseRunbookStepHash,
  renderRunbookMarkdown,
  runbookStepForTime,
  runbookStepHash,
  type Runbook,
} from '@/lib/runbook-steps';
import { RUNBOOK_SOURCE_HASH, RUNBOOK_VIDEO_ID, runbookPackFixture } from '@/lib/__fixtures__/aujzb1d-fag-runbook';
import type { LinkedSop } from '@/lib/linked-sop';

function stepById(runbook: Runbook, sourceId: string) {
  const step = runbook.steps.find((row) => row.source.id === sourceId);
  if (!step) throw new Error(`Missing step for ${sourceId}`);
  return step;
}

describe('compileRunbook on the saved auJzb1D-fag pack', () => {
  const pack = runbookPackFixture();
  const runbook = compileRunbook({ pack });

  it('keeps the saved identity and compiles each source step once', () => {
    expect(runbook.version).toBe('runbook-v1');
    expect(runbook.videoId).toBe(RUNBOOK_VIDEO_ID);
    expect(runbook.sourceHash).toBe(RUNBOOK_SOURCE_HASH);
    expect(runbook.packId).toBe(`vp:v0:${RUNBOOK_VIDEO_ID}`);
    expect(runbook.steps.map((step) => step.step_number)).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
    expect(new Set(runbook.steps.map((step) => step.id)).size).toBe(8);
    expect(runbook.steps.map((step) => step.source.id)).toEqual([
      'REQ-01', 'REQ-02', 'REQ-03', 'REQ-04', 'REQ-05', 'ACT-01', 'ACT-02', 'ACT-03',
    ]);
    expect(runbook.durationSeconds).toBe(481);
    expect(runbook.coverage).toEqual({ anchored: 8, total: 8 });
  });

  it('anchors steps to transcript and validated grounded citations', () => {
    const ingestion = stepById(runbook, 'REQ-01');
    expect(ingestion.timestamp_range).toEqual([102, 148]);
    expect(ingestion.anchor).toBe('transcript');
    expect(ingestion.evidence.quote).toContain('long context text capabilities');

    const spatial = stepById(runbook, 'REQ-05');
    expect(spatial.timestamp_range).toEqual([414, 454]);
    expect(spatial.anchor).toBe('grounded_spec');
    expect(spatial.evidence.quote).toContain('2D bounding boxes');
    expect(spatial.evidence.keyframe?.image_path).toBe('/api/video/pack/frames/auJzb1D-fag/435');
  });

  it('anchors action items using the same evidence rules', () => {
    expect(stepById(runbook, 'ACT-01').timestamp_range).toEqual([332, 353]);
    expect(stepById(runbook, 'ACT-01').anchor).toBe('grounded_spec');
    expect(stepById(runbook, 'ACT-02').timestamp_range).toEqual([379, 395]);
    expect(stepById(runbook, 'ACT-02').anchor).toBe('grounded_spec');
    expect(stepById(runbook, 'ACT-03').timestamp_range).toEqual([406, 438]);
  });

  it('derives verification from acceptance criteria, stack checks, or an explicit gap', () => {
    const spatial = stepById(runbook, 'REQ-05');
    expect(spatial.verification_source).toBe('grounded_spec');
    expect(spatial.verification).toContain('Origami objects in the window frame image');

    const prompting = stepById(runbook, 'REQ-03');
    expect(prompting.verification_source).toBe('stack_check');
    expect(prompting.verification).toContain('Imagen: Inspect Imagen prompt modal');

    const ingestion = stepById(runbook, 'REQ-01');
    expect(ingestion.verification_source).toBe('none');
    expect(ingestion.verification).toContain('1:42–2:28');
  });

  it('classifies the saved code and verification steps from source fields', () => {
    const spatial = stepById(runbook, 'REQ-05');
    expect(spatial.kind).toBe('code_snippet');
    expect(spatial.snippet?.path_hint).toBe('google-ai-studio/spatial-understanding/app.tsx');
    expect(spatial.content_markdown).toContain('```');
    expect(stepById(runbook, 'ACT-03').kind).toBe('verification_check');
  });

  it('builds Step 0 prerequisites from the saved tool checks', () => {
    expect(runbook.prerequisites.map((row) => row.title)).toEqual([
      'Google AI Studio', 'Gemini 2.5 Pro Preview', 'Gemini Flash / Gemini 2.0 Flash', 'Imagen', 'Veo',
    ]);
    expect(runbook.prerequisites.every((row) => row.kind === 'tool')).toBe(true);
    expect(runbook.prerequisites[0].detail).toBe('Navigate to Google AI Studio web application');
    expect(new Set(runbook.prerequisites.map((row) => row.id)).size).toBe(5);
  });

  it('resolves a playing step and parses step hashes', () => {
    expect(runbookStepForTime(runbook, 340)?.source.id).toBe('ACT-01');
    expect(runbookStepForTime(runbook, 10)).toBeNull();
    expect(runbookStepHash(3)).toBe('#step-3');
    expect(parseRunbookStepHash('#step-3')).toBe(3);
    expect(parseRunbookStepHash('#step-0')).toBe(0);
    expect(parseRunbookStepHash('#foo')).toBeNull();
    expect(parseRunbookStepHash('')).toBeNull();
    expect(clampRunbookStep(99, runbook.steps.length)).toBe(8);
    expect(clampRunbookStep(-4, runbook.steps.length)).toBe(0);
  });

  it('renders RUNBOOK.md with source timestamps, prerequisites, and progress', () => {
    const markdown = renderRunbookMarkdown(runbook, {
      checkedPrerequisites: [runbook.prerequisites[0].id],
      completedSteps: [stepById(runbook, 'REQ-01').id],
    });
    expect(markdown).toContain(`# Runbook — ${RUNBOOK_VIDEO_ID}`);
    expect(markdown).toContain('## Step 0 — Prerequisites & Environment');
    expect(markdown).toContain('- [x] Google AI Studio — Navigate to Google AI Studio web application');
    expect(markdown).toContain('## Step 1 — Long Context Video Ingestion [1:42–2:28] ✓');
    expect(markdown).toContain('## Step 5 — Spatial Understanding & Bounding Boxes [6:54–7:34]');
    expect(markdown).toContain('Verification: Given: User is on the Spatial Understanding Demo screen');
    expect(markdown).toContain('Steps anchored to video evidence: 8 / 8');
    expect(markdown).not.toContain('[No verified timestamp]');
  });
});

describe('compileRunbook honesty and fallbacks', () => {
  it('keeps a step unanchored when no pack evidence matches it', () => {
    const pack = runbookPackFixture();
    pack.requirements = [
      ...pack.requirements,
      { id: 'REQ-99', title: 'Rotate the quarterly budget spreadsheet', detail: 'Unrelated to anything spoken.' },
    ];
    const runbook = compileRunbook({ pack });
    const orphan = runbook.steps.find((step) => step.source.id === 'REQ-99');
    expect(orphan?.timestamp_range).toBeNull();
    expect(orphan?.anchor).toBe('none');
    expect(orphan?.evidence.quote).toBeUndefined();
    expect(runbook.coverage).toEqual({ anchored: 8, total: 9 });
    const markdown = renderRunbookMarkdown(runbook);
    expect(markdown).toContain('## Step 6 — Rotate the quarterly budget spreadsheet [No verified timestamp]');
  });

  it('prefers explicit extractor start_s/end_s over derived anchors', () => {
    const pack = runbookPackFixture();
    pack.requirements = pack.requirements.map((row) =>
      row.id === 'REQ-05' ? { ...row, start_s: 30, end_s: 42 } : row,
    );
    const runbook = compileRunbook({ pack });
    const step = runbook.steps.find((row) => row.source.id === 'REQ-05');
    expect(step?.timestamp_range).toEqual([30, 42]);
    expect(step?.anchor).toBe('extracted');
    expect(step?.verification_source).toBe('grounded_spec');
    expect(step?.verification).toContain('Origami objects in the window frame image');
  });

  it('bounds long source ids to the chat schema and preserves unique ids', () => {
    const pack = runbookPackFixture();
    pack.requirements = [
      { id: `same-${'x'.repeat(90)}-one`, title: 'First step', detail: 'First detail' },
      { id: `same-${'x'.repeat(90)}-two`, title: 'Second step', detail: 'Second detail' },
    ];
    pack.action_items = [];
    const steps = compileRunbook({ pack }).steps;
    expect(steps).toHaveLength(2);
    expect(steps.every((step) => step.id.length <= 64)).toBe(true);
    expect(new Set(steps.map((step) => step.id)).size).toBe(2);
  });

  it('labels terminal commands and fences them as bash', () => {
    const pack = runbookPackFixture();
    pack.requirements = [
      { id: 'REQ-CLI', title: 'Install the Vercel CLI', detail: 'Run `npm install -g vercel` before linking the project.' },
    ];
    pack.action_items = [];
    const runbook = compileRunbook({ pack });
    const step = runbook.steps[0];
    expect(step.kind).toBe('terminal_command');
    expect(step.content_markdown).toContain('```bash\nnpm install -g vercel\n```');
  });

  it('labels verification checks and architecture decisions from the step text', () => {
    const pack = runbookPackFixture();
    pack.requirements = [
      { id: 'REQ-V', title: 'Verify the retainer email was delivered', detail: 'Confirm the prospect received the spec ad.' },
      { id: 'REQ-A', title: 'Decide the outreach architecture', detail: 'Choose between daily email and a scheduler service.' },
    ];
    pack.action_items = [];
    const runbook = compileRunbook({ pack });
    expect(runbook.steps[0].kind).toBe('verification_check');
    expect(runbook.steps[1].kind).toBe('architecture_decision');
  });

  it('falls back to linked SOP steps (with event timestamps) when the pack has no requirements or actions', () => {
    const pack = runbookPackFixture();
    pack.requirements = [];
    pack.action_items = [];
    const linkedSop: LinkedSop = {
      entities: [],
      checklist: [
        { id: 'chk_vercel_1', source: 'stack', stack: 'vercel', title: 'Hold production until Deployment Checks pass', href: 'https://vercel.com/docs/deployment-checks' },
      ],
      steps: [
        { id: 'sop_1', order: 1, title: 'Generate a video with Veo', description: 'From the spoken demonstration.', timestamp: 256, entityNames: [] },
        { id: 'sop_2', order: 2, title: 'A step with no timestamp', description: '', entityNames: [] },
      ],
    };
    const runbook = compileRunbook({ pack, linkedSop });
    expect(runbook.steps).toHaveLength(2);
    expect(runbook.steps[0].timestamp_range).toEqual([252, 260]);
    expect(runbook.steps[0].anchor).toBe('event');
    expect(runbook.steps[1].anchor).toBe('none');
    // Stack checks from the linked SOP become prerequisites after the pack tools.
    expect(runbook.prerequisites.map((row) => row.title)).toEqual([
      'Google AI Studio',
      'Gemini 2.5 Pro Preview',
      'Gemini Flash / Gemini 2.0 Flash',
      'Imagen',
      'Veo',
      'Hold production until Deployment Checks pass',
    ]);
    expect(runbook.prerequisites[5].kind).toBe('stack_check');
    expect(runbook.prerequisites[5].href).toBe('https://vercel.com/docs/deployment-checks');
  });

  it('adds access and runtime prerequisites only when the pack text names them', () => {
    const pack = runbookPackFixture();
    pack.requirements = [
      { id: 'REQ-KEY', title: 'Configure the Gemini API key', detail: 'Export GEMINI_API_KEY in the shell before running.' },
      { id: 'REQ-NODE', title: 'Install Node 22', detail: 'The demo uses Node.js v22.14 for the CLI.' },
    ];
    pack.action_items = [];
    const runbook = compileRunbook({ pack });
    const kinds = runbook.prerequisites.map((row) => row.kind);
    expect(kinds.filter((kind) => kind === 'access')).toHaveLength(1);
    expect(kinds.filter((kind) => kind === 'runtime')).toHaveLength(1);
    const access = runbook.prerequisites.find((row) => row.kind === 'access');
    expect(access?.title).toBe('Access: Gemini API key');
    const runtime = runbook.prerequisites.find((row) => row.kind === 'runtime');
    expect(runtime?.title).toBe('Runtime: Node.js v22.14');
  });

  it('returns an empty runbook for an identity-only pack', () => {
    const pack = runbookPackFixture();
    const runbook = compileRunbook({
      pack: {
        ...pack,
        transcript: { language: null, full_text: '', segments: [] },
        requirements: [],
        action_items: [],
        stack: { tools: [] },
        chapters: [],
        keyframes: [],
        visual_context: null,
        code_snippets: [],
        architecture: null,
        artifacts: [],
      },
    });
    expect(runbook.steps).toEqual([]);
    expect(runbook.prerequisites).toEqual([]);
    expect(runbook.durationSeconds).toBeNull();
    expect(runbook.coverage).toEqual({ anchored: 0, total: 0 });
  });
});
