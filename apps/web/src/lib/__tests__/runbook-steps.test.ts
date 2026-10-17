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
import { PBST6V_SOURCE_HASH, PBST6V_VIDEO_ID, pbst6vPackFixture } from '@/lib/__fixtures__/pbst6v-cio8-runbook';
import type { LinkedSop } from '@/lib/linked-sop';

function stepById(runbook: Runbook, sourceId: string) {
  const step = runbook.steps.find((row) => row.source.id === sourceId);
  if (!step) throw new Error(`Missing step for ${sourceId}`);
  return step;
}

describe('compileRunbook on the live pBsT6v-ciO8 pack', () => {
  const pack = pbst6vPackFixture();
  const runbook = compileRunbook({ pack });

  it('emits identity, sequential step numbers, and unique ids', () => {
    expect(runbook.version).toBe('runbook-v1');
    expect(runbook.videoId).toBe(PBST6V_VIDEO_ID);
    expect(runbook.sourceHash).toBe(PBST6V_SOURCE_HASH);
    expect(runbook.packId).toBe(`vp:v0:${PBST6V_VIDEO_ID}`);
    expect(runbook.steps.map((step) => step.step_number)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(new Set(runbook.steps.map((step) => step.id)).size).toBe(7);
    // Requirements (SOP order) first, then ship action_items that do not collide.
    expect(runbook.steps.map((step) => step.source.id)).toEqual([
      'REQ-01', 'REQ-02', 'REQ-03', 'REQ-04', 'ACT-01', 'ACT-02', 'ACT-03',
    ]);
    expect(runbook.durationSeconds).toBe(474);
    expect(runbook.coverage).toEqual({ anchored: 7, total: 7 });
  });

  it('anchors a step on the transcript segment that quotes the named tool evidence', () => {
    const step = stepById(runbook, 'REQ-01');
    // stack.tools[SeaDance 2.5].evidence quotes 'search up SeaDance 2.5, find any provider' → segment 31.
    expect(step.timestamp_range).toEqual([247, 254.5]);
    expect(step.anchor).toBe('transcript');
    expect(step.evidence.quote).toContain('search up SeaDance 2.5');
    expect(step.inputs).toEqual(['SeaDance 2.5']);
    expect(step.evidence.keyframe?.t_s).toBe(249);
    expect(step.evidence.keyframe?.image_path).toBe('/api/video/pack/frames/pBsT6v-ciO8/249');
  });

  it('upgrades the anchor to grounded_spec when the matched segment is a validated citation', () => {
    const prospects = stepById(runbook, 'REQ-02');
    expect(prospects.timestamp_range).toEqual([254.5, 261]);
    expect(prospects.anchor).toBe('grounded_spec');
    expect(prospects.evidence.quote).toContain('Step two: find 100 software companies');

    const outreach = stepById(runbook, 'REQ-03');
    // Segment 34 is cited; 35 ("put me on a retainer… $10,000 a month") and 36 ("ignore this
    // email… Email them that same thing every single day") continue the match, so the clip
    // extends over the contiguous candidates (max two per side, 60s cap).
    expect(outreach.timestamp_range).toEqual([268, 290.5]);
    expect(outreach.anchor).toBe('grounded_spec');
    expect(outreach.evidence.quote).toContain('Step four: email every single one');

    const taste = stepById(runbook, 'REQ-04');
    // Segment 43 is cited; segment 44 continues the same match, so the range extends.
    expect(taste.timestamp_range).toEqual([337, 352]);
    expect(taste.anchor).toBe('grounded_spec');
    expect(taste.evidence.keyframe?.t_s).toBe(330);
  });

  it('anchors ship action_items with the same evidence rules', () => {
    expect(stepById(runbook, 'ACT-01').timestamp_range).toEqual([247, 254.5]);
    expect(stepById(runbook, 'ACT-02').timestamp_range).toEqual([254.5, 261]);
    expect(stepById(runbook, 'ACT-02').anchor).toBe('grounded_spec');
    const meta = stepById(runbook, 'ACT-03');
    // Meta Ad Library evidence quote lives verbatim in segment 49.
    expect(meta.timestamp_range).toEqual([384, 393]);
    expect(meta.anchor).toBe('transcript');
    expect(meta.inputs).toEqual(['Meta Ad Library']);
  });

  it('derives verification from grounded acceptance criteria, then stack checks, else states the gap', () => {
    const prospects = stepById(runbook, 'REQ-02');
    expect(prospects.verification_source).toBe('grounded_spec');
    expect(prospects.verification).toContain('Given: A user enters a company name with funding of $12M');
    expect(prospects.verification).toContain('Then: The company is saved in local storage');

    const tooling = stepById(runbook, 'REQ-01');
    expect(tooling.verification_source).toBe('stack_check');
    expect(tooling.verification).toBe('SeaDance 2.5: sea-dance model search');

    const outreach = stepById(runbook, 'REQ-03');
    expect(outreach.verification_source).toBe('none');
    expect(outreach.verification).toContain('4:28–4:50');
    expect(outreach.verification).toMatch(/no explicit check/i);
  });

  it('classifies kinds only from pack fields and attaches matched snippets', () => {
    const outreach = stepById(runbook, 'REQ-03');
    expect(outreach.kind).toBe('code_snippet');
    expect(outreach.snippet?.path_hint).toBe('scripts/outreach_template.ts');
    expect(outreach.content_markdown).toContain('```typescript');
    expect(outreach.content_markdown).toContain('interface SpecAdPitch');

    const prospects = stepById(runbook, 'REQ-02');
    expect(prospects.kind).toBe('action');
    expect(prospects.architecture_stage).toBe('Target Discovery');
    expect(prospects.snippet).toBeNull();
  });

  it('builds Step 0 prerequisites from stack.tools without inventing access or runtime rows', () => {
    expect(runbook.prerequisites.map((row) => row.title)).toEqual([
      'SeaDance 2.5',
      'Meta Ad Library',
      'ChatGPT',
    ]);
    expect(runbook.prerequisites.every((row) => row.kind === 'tool')).toBe(true);
    expect(runbook.prerequisites[0].detail).toBe('sea-dance model search');
    expect(new Set(runbook.prerequisites.map((row) => row.id)).size).toBe(3);
  });

  it('resolves the step playing at a given time and parses step hashes', () => {
    expect(runbookStepForTime(runbook, 258)?.source.id).toBe('REQ-02');
    expect(runbookStepForTime(runbook, 100)).toBeNull();
    expect(runbookStepHash(3)).toBe('#step-3');
    expect(parseRunbookStepHash('#step-3')).toBe(3);
    expect(parseRunbookStepHash('#step-0')).toBe(0);
    expect(parseRunbookStepHash('#foo')).toBeNull();
    expect(parseRunbookStepHash('')).toBeNull();
    expect(clampRunbookStep(99, runbook.steps.length)).toBe(7);
    expect(clampRunbookStep(-4, runbook.steps.length)).toBe(0);
  });

  it('renders RUNBOOK.md with anchored timestamps, prerequisites and progress marks', () => {
    const markdown = renderRunbookMarkdown(runbook, {
      checkedPrerequisites: [runbook.prerequisites[0].id],
      completedSteps: [stepById(runbook, 'REQ-01').id],
    });
    expect(markdown).toContain(`# Runbook — ${PBST6V_VIDEO_ID}`);
    expect(markdown).toContain('## Step 0 — Prerequisites & Environment');
    expect(markdown).toContain('- [x] SeaDance 2.5 — sea-dance model search');
    expect(markdown).toContain('- [ ] Meta Ad Library — facebook ad library url lookup');
    expect(markdown).toContain('## Step 1 — AI Video Generation Tooling [4:07–4:14] ✓');
    expect(markdown).toContain('## Step 2 — Target Prospect List Building [4:14–4:21]');
    expect(markdown).toContain('Verification: Given: A user enters a company name');
    expect(markdown).toContain('Steps anchored to video evidence: 7 / 7');
    expect(markdown).not.toContain('[No verified timestamp]');
    expect(markdown).toContain('## Step 3 — Spec Ad Creation and Daily Email Outreach [4:28–4:50]');
    expect(markdown).toContain('Snippet: scripts/outreach_template.ts\n```typescript');
  });
});

describe('compileRunbook honesty and fallbacks', () => {
  it('keeps a step unanchored when no pack evidence matches it', () => {
    const pack = pbst6vPackFixture();
    pack.requirements = [
      ...pack.requirements,
      { id: 'REQ-99', title: 'Rotate the quarterly budget spreadsheet', detail: 'Unrelated to anything spoken.' },
    ];
    const runbook = compileRunbook({ pack });
    const orphan = runbook.steps.find((step) => step.source.id === 'REQ-99');
    expect(orphan?.timestamp_range).toBeNull();
    expect(orphan?.anchor).toBe('none');
    expect(orphan?.evidence.quote).toBeUndefined();
    expect(runbook.coverage).toEqual({ anchored: 7, total: 8 });
    const markdown = renderRunbookMarkdown(runbook);
    expect(markdown).toContain('## Step 5 — Rotate the quarterly budget spreadsheet [No verified timestamp]');
  });

  it('prefers explicit extractor start_s/end_s over derived anchors', () => {
    const pack = pbst6vPackFixture();
    pack.requirements = pack.requirements.map((row) =>
      row.id === 'REQ-01' ? { ...row, start_s: 30, end_s: 42 } : row,
    );
    const runbook = compileRunbook({ pack });
    const step = runbook.steps.find((row) => row.source.id === 'REQ-01');
    expect(step?.timestamp_range).toEqual([30, 42]);
    expect(step?.anchor).toBe('extracted');
  });

  it('labels terminal commands and fences them as bash', () => {
    const pack = pbst6vPackFixture();
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
    const pack = pbst6vPackFixture();
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
    const pack = pbst6vPackFixture();
    pack.requirements = [];
    pack.action_items = [];
    const linkedSop: LinkedSop = {
      entities: [],
      checklist: [
        { id: 'chk_vercel_1', source: 'stack', stack: 'vercel', title: 'Hold production until Deployment Checks pass', href: 'https://vercel.com/docs/deployment-checks' },
      ],
      steps: [
        { id: 'sop_1', order: 1, title: 'Find 100 funded software companies', description: 'From the spoken step two.', timestamp: 256, entityNames: [] },
        { id: 'sop_2', order: 2, title: 'A step with no timestamp', description: '', entityNames: [] },
      ],
    };
    const runbook = compileRunbook({ pack, linkedSop });
    expect(runbook.steps).toHaveLength(2);
    expect(runbook.steps[0].timestamp_range).toEqual([254.5, 261]);
    expect(runbook.steps[0].anchor).toBe('event');
    expect(runbook.steps[1].anchor).toBe('none');
    // Stack checks from the linked SOP become prerequisites after the pack tools.
    expect(runbook.prerequisites.map((row) => row.title)).toEqual([
      'SeaDance 2.5',
      'Meta Ad Library',
      'ChatGPT',
      'Hold production until Deployment Checks pass',
    ]);
    expect(runbook.prerequisites[3].kind).toBe('stack_check');
    expect(runbook.prerequisites[3].href).toBe('https://vercel.com/docs/deployment-checks');
  });

  it('adds access and runtime prerequisites only when the pack text names them', () => {
    const pack = pbst6vPackFixture();
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
    const pack = pbst6vPackFixture();
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
