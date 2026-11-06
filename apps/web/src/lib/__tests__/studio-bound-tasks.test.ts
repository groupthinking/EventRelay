import assert from 'node:assert/strict';
import { test } from 'vitest';
import { specificationIssues, type ReviewInspection } from '../grounded-build-spec';
import { projectStudioBoundTasks } from '../studio-bound-tasks';

type AvailableInspection = Extract<ReviewInspection, { status: 'available' }>;

// Synthetic specification fixtures exercise the projection contract. They are
// not extracted video content and are never included in product output.
function inspectedSpec(): AvailableInspection {
  const videoId = 'auJzb1D-fag';
  const citation = {
    kind: 'transcript' as const, index: 0, videoId,
    startSeconds: 4, endSeconds: 8, quote: 'Keep a count in the browser.',
  };
  const requirement = {
    id: 'count', screenId: 'main', title: 'Counter', detail: 'Keep a count.',
    classification: 'observed' as const, required: true,
    capabilities: ['local-state' as const], rationale: '', citations: [citation],
  };
  return {
    status: 'available' as const, contentHash: 'b'.repeat(64), canonical: 'test-fixture',
    issues: [{ code: 'model-evidence', path: '', message: 'Not independently verified.', severity: 'warning' as const }],
    spec: {
      version: '1' as const, outputClass: 'browser-interactive' as const, sourceStatus: 'full' as const,
      confidence: 0.99, limitations: [], app: { name: 'Counter', purpose: 'Count' },
      source: { packId: `vp:v0:${videoId}`, videoId, sourceUrl: `https://www.youtube.com/watch?v=${videoId}`, sourceHash: 'a'.repeat(64) },
      screens: [{ id: 'main', name: 'Main', purpose: 'Count' }], state: [],
      requirements: [requirement, { ...requirement, id: 'reset', title: 'Counter', classification: 'proposed' as const, citations: [], rationale: 'Proposed convenience.' }],
      acceptanceCriteria: [
        { id: 'reset-check', requirementId: 'reset', given: 'Count is 2', when: 'Reset is clicked', then: 'Count is 0' },
        { id: 'count-check', requirementId: 'count', given: 'Count is 0', when: 'Increment is clicked', then: 'Count is 1' },
      ],
      unresolved: [], unsupported: [],
    },
  };
}

function available(view: ReturnType<typeof projectStudioBoundTasks>) {
  assert.equal(view.status, 'available');
  if (view.status !== 'available') throw new Error('expected an available view');
  return view;
}

test('binds criteria by requirement ID despite duplicate titles and different order', () => {
  const view = available(projectStudioBoundTasks(inspectedSpec()));
  assert.deepEqual(view.tasks.map((task) => task.checks.map((check) => check.id)), [['count-check'], ['reset-check']]);
  assert.equal(view.tasks[0].citations[0].videoId, 'auJzb1D-fag');
  assert.equal(view.tasks[0].citations[0].startSeconds, 4);
  assert.equal(view.tasks[0].citations[0].quote, 'Keep a count in the browser.');
  assert.equal(view.tasks[0].citations[0].sourceUrl, 'https://www.youtube.com/watch?v=auJzb1D-fag&t=4s');
  assert.deepEqual(view.tasks[1].citations, []);
  assert.equal(view.source.sourceHash, 'a'.repeat(64));
  assert.equal(view.contentHash, 'b'.repeat(64));
});

test('observed source, high confidence and proposed criteria never imply executed or verified', () => {
  const view = projectStudioBoundTasks(inspectedSpec());
  for (const task of view.tasks) {
    assert.equal(task.executionStatus, 'not_run');
    assert.equal(task.outputStatus, 'not_generated');
    assert.equal(task.verificationStatus, 'unverified');
    assert.ok(task.checks.every((check) => check.status === 'not_run'));
  }
  assert.equal(view.tasks[1].classification, 'proposed');
});

test('invalid, absent or source-unavailable inspections expose no task rows', () => {
  for (const status of ['invalid', 'unavailable', 'source-unavailable'] as const) {
    const issues = [{ code: 'invalid-citation', path: 'count', message: 'Wrong video.', severity: 'blocking' as const }];
    // Extra stale data must not survive the inspection's failed status.
    const view = projectStudioBoundTasks({ ...inspectedSpec(), status, issues } as unknown as ReviewInspection);
    assert.deepEqual(view.tasks, []);
    assert.deepEqual(view.issues, issues);
    assert.equal(view.status, status);
    assert.equal('source' in view, false);
  }
});

test('does not manufacture missing criteria, source citations, or tasks', () => {
  const inspection = inspectedSpec();
  inspection.spec.acceptanceCriteria = [];
  inspection.spec.requirements[0].citations = [];
  let view = available(projectStudioBoundTasks(inspection));
  assert.deepEqual(view.tasks[0].checks, []);
  assert.deepEqual(view.tasks[0].citations, []);
  inspection.spec.requirements = [];
  view = available(projectStudioBoundTasks(inspection));
  assert.deepEqual(view.tasks, []);
});

test('projected copies cannot mutate the inspected source or its check text', () => {
  const inspection = inspectedSpec();
  const before = structuredClone(inspection);
  const view = available(projectStudioBoundTasks(inspection));
  view.source.sourceHash = 'changed';
  view.tasks[0].citations[0].quote = 'changed';
  view.tasks[0].checks[0].then = 'changed';
  view.tasks[0].issues[0].message = 'changed';
  view.issues[0].message = 'changed';
  assert.deepEqual(inspection, before);
});

function withSpecIssues(inspection: AvailableInspection): AvailableInspection {
  // Mirror inspectGroundedSpec: an available inspection's issues are the
  // specification issues of its spec.
  inspection.issues = specificationIssues(inspection.spec);
  return inspection;
}

test('binds unresolved and unsupported blockers to their affected requirement IDs', () => {
  const inspection = inspectedSpec();
  inspection.spec.unresolved = [{ id: 'reset-question', requirementIds: ['reset'], question: 'What resets?', required: true }];
  inspection.spec.unsupported = [{ id: 'count-storage', requirementIds: ['count'], capability: 'shared-database', reason: 'Needs shared storage.', required: true }];
  const view = available(projectStudioBoundTasks(withSpecIssues(inspection)));
  assert.deepEqual(view.tasks[0].issues.map((issue) => [issue.code, issue.path]), [
    ['model-evidence', ''], ['unsupported-capability', 'unsupported.count-storage'],
  ]);
  assert.deepEqual(view.tasks[1].issues.map((issue) => [issue.code, issue.path]), [
    ['model-evidence', ''], ['unresolved-choice', 'reset'], ['unresolved-question', 'unresolved.reset-question'],
  ]);
});

test('cross-collection ID collisions do not attach blockers to unrelated tasks', () => {
  // IDs are unique only within each collection: a question may share the ID
  // of a requirement it does not affect.
  const inspection = inspectedSpec();
  inspection.spec.unresolved = [{ id: 'count', requirementIds: ['reset'], question: 'What resets?', required: true }];
  inspection.spec.unsupported = [{ id: 'reset', requirementIds: ['count'], capability: 'shared-database', reason: 'Needs shared storage.', required: true }];
  const view = available(projectStudioBoundTasks(withSpecIssues(inspection)));
  const [count, reset] = view.tasks;
  assert.equal(count.id, 'count');
  assert.equal(reset.id, 'reset');
  // The question `count` affects only requirement `reset`.
  assert.equal(count.issues.some((issue) => issue.code === 'unresolved-question'), false);
  assert.deepEqual(reset.issues.filter((issue) => issue.code === 'unresolved-question').map((issue) => issue.message), ['What resets?']);
  // The capability `reset` affects only requirement `count`.
  assert.deepEqual(count.issues.filter((issue) => issue.code === 'unsupported-capability').map((issue) => issue.message), ['Needs shared storage.']);
  assert.equal(reset.issues.some((issue) => issue.message === 'Needs shared storage.'), false);
  // Limitation issues carry collection-qualified paths, never a bare requirement ID.
  assert.deepEqual(reset.issues.filter((issue) => issue.code === 'unresolved-question').map((issue) => issue.path), ['unresolved.count']);
  assert.deepEqual(count.issues.filter((issue) => issue.code === 'unsupported-capability').map((issue) => issue.path), ['unsupported.reset']);
  // Requirement `reset`'s own issue stays on `reset`, not on `count`.
  assert.equal(count.issues.some((issue) => issue.code === 'unresolved-choice'), false);
  assert.deepEqual(reset.issues.filter((issue) => issue.code === 'unresolved-choice').map((issue) => issue.path), ['reset']);
  // The full issue list (exported with the tasks) is unchanged.
  assert.deepEqual(view.issues, inspection.issues);
});

test('a limitation naming one requirement twice binds its issue once', () => {
  const inspection = inspectedSpec();
  inspection.spec.unresolved = [{ id: 'q', requirementIds: ['count', 'count'], question: 'How high?', required: false }];
  const view = available(projectStudioBoundTasks(withSpecIssues(inspection)));
  assert.equal(view.tasks[0].issues.filter((issue) => issue.code === 'unresolved-question').length, 1);
  assert.equal(view.tasks[1].issues.some((issue) => issue.code === 'unresolved-question'), false);
});
