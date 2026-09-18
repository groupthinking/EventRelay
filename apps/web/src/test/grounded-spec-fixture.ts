import { parseGroundedSpec } from '@/lib/grounded-build-spec';
import { applyExtractedSpec, buildIdentityPack } from '@/lib/video-pack';

export function reviewPackFixture(raw = browserSpecFixture()) {
  return applyExtractedSpec(buildIdentityPack('auJzb1D-fag'), {
    ...raw, grounded_spec: parseGroundedSpec(raw.grounded_spec, raw, 'auJzb1D-fag'),
  });
}

/** Synthetic UI/contract fixture, not an observation of the fixture video. */
export function browserSpecFixture() {
  return {
    transcript: {
      language: 'en',
      full_text: 'Select a task to mark it complete.',
      segments: [{ idx: 0, start_s: 4, end_s: 8, text: 'Select a task to mark it complete.' }],
    },
    keyframes: [], concepts: [], requirements: [], code_snippets: [],
    artifacts: [], stack: { tools: [] },
    visual_context: {
      visual_elements: [{ timestamp: 5, element_type: 'interface', content: 'A task list with checkboxes.' }],
    },
    grounded_spec: {
      version: '1', outputClass: 'browser-interactive',
      sourceStatus: 'partial', confidence: 0.8,
      limitations: ['Synthetic fixture; only one interaction is described.'],
      app: { name: 'Task checklist', purpose: 'Track completed tasks in the browser.' },
      screens: [{ id: 'tasks', name: 'Tasks', purpose: 'View and complete tasks.' }],
      state: [{ id: 'completion', name: 'Task completion', description: 'Checked task IDs.', persistence: 'memory' }],
      requirements: [{
        id: 'toggle', screenId: 'tasks', title: 'Mark a task complete', detail: 'Toggle the task checkbox.',
        classification: 'observed', required: true, capabilities: ['browser-ui', 'local-state'], rationale: '',
        citations: [{ kind: 'transcript', index: 0, videoId: 'auJzb1D-fag', startSeconds: 4, endSeconds: 8, quote: 'Select a task to mark it complete.' }],
      }],
      acceptanceCriteria: [{ id: 'toggle-check', requirementId: 'toggle', given: 'An unchecked task', when: 'Select its checkbox', then: 'The task is visibly checked.' }],
      unresolved: [] as Array<{ id: string; requirementIds: string[]; question: string; required: boolean }>,
      unsupported: [] as Array<{ id: string; requirementIds: string[]; capability: string; reason: string; required: boolean }>,
    },
  };
}
