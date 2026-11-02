import test from 'node:test';
import assert from 'node:assert/strict';
import { projectStudioBoundTasks } from '../studio-bound-tasks.ts';

// Synthetic specification fixtures exercise the projection contract. They are
// not extracted video content and are never included in product output.
function inspectedSpec() {
  const videoId = 'auJzb1D-fag';
  const citation = {
    kind: 'transcript', index: 0, videoId,
    startSeconds: 4, endSeconds: 8, quote: 'Keep a count in the browser.',
  };
  const requirement = {
    id: 'count', screenId: 'main', title: 'Counter', detail: 'Keep a count.',
    classification: 'observed', required: true,
    capabilities: ['local-state'], rationale: '', citations: [citation],
  };
  return {
    status: 'available', contentHash: 'b'.repeat(64), canonical: 'test-fixture',
    issues: [{ code: 'model-evidence', path: '', message: 'Not independently verified.', severity: 'warning' }],
    spec: {
      version: '1', outputClass: 'browser-interactive', sourceStatus: 'full',
      confidence: 0.99, limitations: [], app: { name: 'Counter', purpose: 'Count' },
      source: { packId: `vp:v0:${videoId}`, videoId, sourceUrl: `https://www.youtube.com/watch?v=${videoId}`, sourceHash: 'a'.repeat(64) },
      screens: [{ id: 'main', name: 'Main', purpose: 'Count' }], state: [],
      requirements: [requirement, { ...requirement, id: 'reset', title: 'Counter', classification: 'proposed', citations: [], rationale: 'Proposed convenience.' }],
      acceptanceCriteria: [
        { id: 'reset-check', requirementId: 'reset', given: 'Count is 2', when: 'Reset is clicked', then: 'Count is 0' },
        { id: 'count-check', requirementId: 'count', given: 'Count is 0', when: 'Increment is clicked', then: 'Count is 1' },
      ],
      unresolved: [], unsupported: [],
    },
  };
}

test('binds criteria by requirement ID despite duplicate titles and different order', () => {
  const view = projectStudioBoundTasks(inspectedSpec());
  assert.equal(view.status, 'available');
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
  for (const status of ['invalid', 'unavailable', 'source-unavailable']) {
    const issues = [{ code: 'invalid-citation', path: 'count', message: 'Wrong video.', severity: 'blocking' }];
    // Extra stale data must not survive the inspection's failed status.
    const view = projectStudioBoundTasks({ ...inspectedSpec(), status, issues });
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
  let view = projectStudioBoundTasks(inspection);
  assert.deepEqual(view.tasks[0].checks, []);
  assert.deepEqual(view.tasks[0].citations, []);
  inspection.spec.requirements = [];
  view = projectStudioBoundTasks(inspection);
  assert.deepEqual(view.tasks, []);
});

test('projected copies cannot mutate the inspected source or its check text', () => {
  const inspection = inspectedSpec();
  const before = structuredClone(inspection);
  const view = projectStudioBoundTasks(inspection);
  view.source.sourceHash = 'changed';
  view.tasks[0].citations[0].quote = 'changed';
  view.tasks[0].checks[0].then = 'changed';
  view.tasks[0].issues[0].message = 'changed';
  view.issues[0].message = 'changed';
  assert.deepEqual(inspection, before);
});

test('binds unresolved and unsupported blockers to their affected requirement IDs', () => {
  const inspection = inspectedSpec();
  inspection.spec.unresolved = [{ id: 'reset-question', requirementIds: ['reset'], question: 'What resets?', required: true }];
  inspection.spec.unsupported = [{ id: 'count-storage', requirementIds: ['count'], capability: 'shared-database', reason: 'Needs shared storage.', required: true }];
  inspection.issues.push(
    { code: 'unresolved-question', path: 'reset-question', message: 'What resets?', severity: 'blocking' },
    { code: 'unsupported-capability', path: 'count-storage', message: 'Needs shared storage.', severity: 'blocking' },
  );
  const view = projectStudioBoundTasks(inspection);
  assert.deepEqual(view.tasks[0].issues.map((issue) => issue.code), ['model-evidence', 'unsupported-capability']);
  assert.deepEqual(view.tasks[1].issues.map((issue) => issue.code), ['model-evidence', 'unresolved-question']);
});
