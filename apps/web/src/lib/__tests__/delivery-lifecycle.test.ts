/**
 * Tests for the delivery run state machine.
 *
 * The central property under test is the audit-finding-F7 guarantee: a run can
 * only reach `delivered` when it carries a repository, passing tests, and a real
 * live deployment URL. Every attempt to shortcut that must land in `blocked`
 * with a reason, never in `delivered`.
 */

import { describe, expect, it } from 'vitest';
import {
  canTransition,
  createRun,
  isDelivered,
  isRealDeploymentUrl,
  missingDeliveryEvidence,
  reduceRun,
  type DeliveryEvent,
  type DeliveryRun,
} from '@/lib/delivery-lifecycle';

const NOW = () => '2026-01-01T00:00:00.000Z';

function fresh(): DeliveryRun {
  return createRun('r1', { kind: 'video', url: 'https://youtube.com/watch?v=auJzb1D-fag' }, NOW);
}

/** Drive a run through a list of events. */
function drive(run: DeliveryRun, events: DeliveryEvent[]): DeliveryRun {
  return events.reduce((acc, e) => reduceRun(acc, e, NOW), run);
}

/** The events that legitimately ship a product. */
const HAPPY_PATH: DeliveryEvent[] = [
  { type: 'SOURCE_VERIFIED', evidence: { transcriptChars: 4200 } },
  { type: 'REQUIREMENTS_DRAFTED', evidence: { requirements: 7 } },
  { type: 'PLAN_READY', evidence: { steps: 12 } },
  { type: 'APPROVED', approvedBy: 'founder@acme.test' },
  { type: 'BUILD_SUCCEEDED', repoUrl: 'https://github.com/acme/widget', evidence: { commit: 'abc123' } },
  { type: 'TESTS_PASSED', testsPassedAt: NOW(), evidence: { exitCode: 0, passed: 42 } },
  { type: 'DEPLOYED', deploymentUrl: 'https://widget.vercel.app', evidence: { status: 200 } },
];

describe('delivery lifecycle: happy path', () => {
  it('starts in sourcing with no evidence', () => {
    const r = fresh();
    expect(r.phase).toBe('sourcing');
    expect(r.evidence.gates).toEqual([]);
    expect(isDelivered(r)).toBe(false);
  });

  it('walks source → delivered and records a gate for each phase', () => {
    const r = drive(fresh(), HAPPY_PATH);
    expect(r.phase).toBe('delivered');
    expect(isDelivered(r)).toBe(true);
    expect(r.evidence.repoUrl).toBe('https://github.com/acme/widget');
    expect(r.evidence.deploymentUrl).toBe('https://widget.vercel.app');
    // Seven gates, all passing.
    expect(r.evidence.gates).toHaveLength(7);
    expect(r.evidence.gates.every((g) => g.result === 'pass')).toBe(true);
    expect(r.evidence.gates.map((g) => g.kind)).toEqual([
      'source_evidence',
      'requirements_complete',
      'plan_executable',
      'human_approved',
      'build_succeeded',
      'tests_passed',
      'deployment_live',
    ]);
  });

  it('passes through awaiting_approval rather than building unattended', () => {
    const upToPlan = drive(fresh(), HAPPY_PATH.slice(0, 3));
    expect(upToPlan.phase).toBe('awaiting_approval');
    // Without APPROVED it cannot start building.
    expect(canTransition('awaiting_approval', 'BUILD_SUCCEEDED')).toBe(false);
  });
});

describe('delivery lifecycle: delivered requires real evidence (F7)', () => {
  it('blocks a DEPLOYED run that never built a repository', () => {
    // Skip BUILD_SUCCEEDED by forcing the phase forward illegally is not
    // possible, so instead reach `deploying` legitimately then strip the repo.
    const atDeploying = drive(fresh(), HAPPY_PATH.slice(0, 6));
    expect(atDeploying.phase).toBe('deploying');

    const noRepo: DeliveryRun = {
      ...atDeploying,
      evidence: { ...atDeploying.evidence, repoUrl: undefined },
    };
    const r = reduceRun(noRepo, HAPPY_PATH[6], NOW);

    expect(r.phase).toBe('blocked');
    expect(r.phase).not.toBe('delivered');
    expect(r.blockedReason).toContain('no repository was committed');
    expect(isDelivered(r)).toBe(false);
  });

  it('blocks a DEPLOYED run whose tests never passed', () => {
    const atDeploying = drive(fresh(), HAPPY_PATH.slice(0, 6));
    const noTests: DeliveryRun = {
      ...atDeploying,
      evidence: { ...atDeploying.evidence, testsPassedAt: undefined },
    };
    const r = reduceRun(noTests, HAPPY_PATH[6], NOW);

    expect(r.phase).toBe('blocked');
    expect(r.blockedReason).toContain('tests never passed');
  });

  it.each([
    ['http://localhost:3000', 'localhost'],
    ['http://127.0.0.1:8000', 'loopback IP'],
    ['https://example.com/app', 'example.com placeholder'],
    ['not-a-url', 'unparseable'],
    ['ftp://files.acme.test', 'non-http scheme'],
  ])('blocks delivery when the deployment URL is %s (%s)', (url) => {
    const atDeploying = drive(fresh(), HAPPY_PATH.slice(0, 6));
    const r = reduceRun(atDeploying, { type: 'DEPLOYED', deploymentUrl: url, evidence: {} }, NOW);

    expect(r.phase).toBe('blocked');
    expect(r.phase).not.toBe('delivered');
    expect(r.blockedReason).toMatch(/deployment URL is not a real live host|no live deployment/);
    // The failed gate is recorded with the reason, so the block is auditable.
    const last = r.evidence.gates.at(-1);
    expect(last?.kind).toBe('deployment_live');
    expect(last?.result).toBe('fail');
  });

  it('isRealDeploymentUrl accepts real https hosts and rejects placeholders', () => {
    expect(isRealDeploymentUrl('https://widget.vercel.app')).toBe(true);
    expect(isRealDeploymentUrl('https://api.uvai.io')).toBe(true);
    // https is required: a product served over plain http is not "shipped",
    // and the database CHECK has always required https.
    expect(isRealDeploymentUrl('http://api.uvai.io')).toBe(false);
    expect(isRealDeploymentUrl('http://localhost:3000')).toBe(false);
    expect(isRealDeploymentUrl('https://localhost')).toBe(false);
    expect(isRealDeploymentUrl('https://sub.localhost')).toBe(false);
    expect(isRealDeploymentUrl('https://example.org')).toBe(false);
    expect(isRealDeploymentUrl('https://docs.example.com/app')).toBe(false);
    expect(isRealDeploymentUrl(undefined)).toBe(false);
    expect(isRealDeploymentUrl('')).toBe(false);
  });

  it('missingDeliveryEvidence names every absent requirement', () => {
    const bare = fresh();
    expect(missingDeliveryEvidence(bare)).toEqual([
      'no repository was committed',
      'tests never passed',
      'no live deployment URL',
    ]);
  });

  it('isDelivered rejects a run whose phase was tampered to delivered', () => {
    // Defence in depth: even if something forced the phase string, the
    // evidence check still reports the truth.
    const forged: DeliveryRun = { ...fresh(), phase: 'delivered' };
    expect(forged.phase).toBe('delivered');
    expect(isDelivered(forged)).toBe(false);
  });
});

describe('delivery lifecycle: blocked is distinct from failed', () => {
  it('GATE_FAILED blocks with a gate-qualified reason and remembers the phase', () => {
    const building = drive(fresh(), HAPPY_PATH.slice(0, 4));
    expect(building.phase).toBe('building');

    const r = reduceRun(
      building,
      { type: 'GATE_FAILED', gate: 'tests_passed', reason: '3 of 42 tests failed', evidence: { failed: 3 } },
      NOW,
    );

    expect(r.phase).toBe('blocked');
    expect(r.blockedReason).toBe('tests_passed: 3 of 42 tests failed');
    expect(r.blockedFrom).toBe('building');
    expect(r.error).toBeUndefined(); // not a system fault
  });

  it('ERROR fails the run and is not conflated with a gate refusal', () => {
    const building = drive(fresh(), HAPPY_PATH.slice(0, 4));
    const r = reduceRun(building, { type: 'ERROR', error: 'sandbox OOM' }, NOW);

    expect(r.phase).toBe('failed');
    expect(r.error).toBe('sandbox OOM');
    expect(r.blockedReason).toBeUndefined();
  });

  it('a blocked run always carries a reason', () => {
    const illegal = reduceRun(fresh(), { type: 'TESTS_PASSED', testsPassedAt: NOW(), evidence: {} }, NOW);
    expect(illegal.phase).toBe('blocked');
    expect(illegal.blockedReason).toContain('Illegal transition: TESTS_PASSED from sourcing');
  });

  it('RESUME returns a blocked run to the phase it stopped in', () => {
    const building = drive(fresh(), HAPPY_PATH.slice(0, 4));
    const blocked = reduceRun(
      building,
      { type: 'GATE_FAILED', gate: 'build_succeeded', reason: 'tsc failed' },
      NOW,
    );
    expect(blocked.phase).toBe('blocked');

    const resumed = reduceRun(blocked, { type: 'RESUME' }, NOW);
    expect(resumed.phase).toBe('building');
    expect(resumed.blockedReason).toBeUndefined();
    expect(resumed.blockedFrom).toBeUndefined();
  });

  it('RESUME is only valid from blocked', () => {
    const building = drive(fresh(), HAPPY_PATH.slice(0, 4));
    expect(reduceRun(building, { type: 'RESUME' }, NOW)).toBe(building);
    expect(canTransition('building', 'RESUME')).toBe(false);
    expect(canTransition('blocked', 'RESUME')).toBe(true);
  });

  it('repeated GATE_FAILED keeps the original blockedFrom', () => {
    const verifying = drive(fresh(), HAPPY_PATH.slice(0, 5));
    expect(verifying.phase).toBe('verifying');
    const once = reduceRun(verifying, { type: 'GATE_FAILED', gate: 'tests_passed', reason: 'a' }, NOW);
    const twice = reduceRun(once, { type: 'GATE_FAILED', gate: 'tests_passed', reason: 'b' }, NOW);
    expect(twice.blockedFrom).toBe('verifying');
  });
});

describe('delivery lifecycle: terminal states are immutable', () => {
  it('a delivered run ignores every later event', () => {
    const delivered = drive(fresh(), HAPPY_PATH);
    expect(delivered.phase).toBe('delivered');

    for (const event of [
      { type: 'ERROR', error: 'late' },
      { type: 'GATE_FAILED', gate: 'tests_passed', reason: 'late' },
      { type: 'CANCEL' },
    ] as DeliveryEvent[]) {
      const after = reduceRun(delivered, event, NOW);
      expect(after).toBe(delivered); // identical reference — true no-op
    }
  });

  it('a failed run cannot be revived into delivered', () => {
    const failed = reduceRun(fresh(), { type: 'ERROR', error: 'boom' }, NOW);
    const after = drive(failed, HAPPY_PATH);
    expect(after.phase).toBe('failed');
    expect(isDelivered(after)).toBe(false);
  });

  it('REJECTED at approval cancels the run', () => {
    const awaiting = drive(fresh(), HAPPY_PATH.slice(0, 3));
    const r = reduceRun(awaiting, { type: 'REJECTED', reason: 'wrong scope' }, NOW);
    expect(r.phase).toBe('cancelled');
    expect(r.blockedReason).toBe('wrong scope');
  });

  it('CANCEL works from any non-terminal phase', () => {
    const building = drive(fresh(), HAPPY_PATH.slice(0, 4));
    const r = reduceRun(building, { type: 'CANCEL', reason: 'customer withdrew' }, NOW);
    expect(r.phase).toBe('cancelled');
  });
});

describe('delivery lifecycle: idea-sourced runs', () => {
  it('an idea run has no source URL but still ships with full evidence', () => {
    const r = drive(createRun('r2', { kind: 'idea' }, NOW), HAPPY_PATH);
    expect(r.sourceKind).toBe('idea');
    expect(r.sourceUrl).toBeUndefined();
    expect(r.phase).toBe('delivered');
    expect(isDelivered(r)).toBe(true);
  });
});
