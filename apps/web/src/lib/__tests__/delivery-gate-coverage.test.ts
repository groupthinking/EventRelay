/**
 * Gate-coverage regression suite.
 *
 * `delivery-lifecycle.test.ts` covers the artifact half of "delivered means
 * shipped": repo, passing tests, live URL. This file covers the process half —
 * that every required gate actually fired.
 *
 * The gap it closes: a run can hold all three artifacts while a gate in the
 * middle of the pipeline never ran. The most damaging instance is
 * `human_approved` — a build that shipped without anyone approving the spec is
 * exactly the "system reported success it could not prove" failure the whole
 * design exists to prevent, and the artifacts alone cannot detect it.
 */

import { describe, expect, it } from 'vitest';
import {
  auditDeliveredRun,
  createRun,
  isDelivered,
  missingRequiredGates,
  reduceRun,
  REQUIRED_GATES,
  type DeliveryEvent,
  type DeliveryGate,
  type DeliveryRun,
} from '@/lib/delivery-lifecycle';

const NOW = () => '2026-01-01T00:00:00.000Z';

const HAPPY_PATH: DeliveryEvent[] = [
  { type: 'SOURCE_VERIFIED', evidence: { transcriptChars: 4200 } },
  { type: 'REQUIREMENTS_DRAFTED', evidence: { requirements: 7 } },
  { type: 'PLAN_READY', evidence: { steps: 12 } },
  { type: 'APPROVED', approvedBy: 'founder@acme.test' },
  {
    type: 'BUILD_SUCCEEDED',
    repoUrl: 'https://github.com/acme/widget',
    evidence: { commit: 'abc123' },
  },
  { type: 'TESTS_PASSED', testsPassedAt: NOW(), evidence: { exitCode: 0, passed: 42 } },
  { type: 'DEPLOYED', deploymentUrl: 'https://widget.vercel.app', evidence: { status: 200 } },
];

function shipped(): DeliveryRun {
  return HAPPY_PATH.reduce(
    (run, event) => reduceRun(run, event, NOW),
    createRun('r1', { kind: 'video', url: 'https://youtube.com/watch?v=auJzb1D-fag' }, NOW),
  );
}

/** A gate row as it would be read back from `run_gates`. */
function gate(
  kind: DeliveryGate['kind'],
  result: DeliveryGate['result'] = 'pass',
): DeliveryGate {
  return { kind, result, evidence: { proof: true }, evaluatedAt: NOW() };
}

/** A row that *looks* delivered, with exactly the gates given. */
function forged(gates: DeliveryGate[]): DeliveryRun {
  return {
    id: 'forged',
    phase: 'delivered',
    sourceKind: 'idea',
    evidence: {
      repoUrl: 'https://github.com/acme/widget',
      testsPassedAt: NOW(),
      deploymentUrl: 'https://widget.vercel.app',
      gates,
    },
    startedAt: NOW(),
    updatedAt: NOW(),
  };
}

describe('gate coverage: an honest delivery passed every gate', () => {
  it('a genuinely shipped run is missing none of them', () => {
    const run = shipped();
    expect(missingRequiredGates(run)).toEqual([]);
    expect(auditDeliveredRun(run)).toEqual([]);
    expect(isDelivered(run)).toBe(true);
  });

  it('the required list matches the gates the pipeline actually records', () => {
    // Guards against a gate being added to the enum and silently never
    // required, which would reopen the hole this suite exists to close.
    expect([...REQUIRED_GATES].sort()).toEqual(
      shipped()
        .evidence.gates.map((g) => g.kind)
        .sort(),
    );
  });
});

describe('gate coverage: artifacts without process are not delivery', () => {
  it.each(REQUIRED_GATES)('rejects a run whose %s gate never passed', (skipped) => {
    const run = forged(REQUIRED_GATES.filter((k) => k !== skipped).map((k) => gate(k)));

    expect(missingRequiredGates(run)).toEqual([skipped]);
    expect(auditDeliveredRun(run)).toContain(`gates never passed: ${skipped}`);
    // The artifacts are all present and still this is not a delivery.
    expect(isDelivered(run)).toBe(false);
  });

  it('rejects a run with full artifacts and no gates at all', () => {
    const run = forged([]);
    expect(missingRequiredGates(run)).toEqual([...REQUIRED_GATES]);
    expect(isDelivered(run)).toBe(false);
  });

  it('a failed gate does not count as passed', () => {
    const run = forged(
      REQUIRED_GATES.map((k) => gate(k, k === 'tests_passed' ? 'fail' : 'pass')),
    );
    expect(missingRequiredGates(run)).toEqual(['tests_passed']);
    expect(isDelivered(run)).toBe(false);
  });

  it('a skipped gate does not count as passed', () => {
    const run = forged(
      REQUIRED_GATES.map((k) => gate(k, k === 'human_approved' ? 'skipped' : 'pass')),
    );
    expect(missingRequiredGates(run)).toEqual(['human_approved']);
    expect(isDelivered(run)).toBe(false);
  });

  it('a gate that failed and was later re-evaluated green counts as passed', () => {
    // Re-running a fixed gate is legitimate; the failure stays in the history
    // as the audit trail rather than permanently poisoning the run.
    const run = forged([
      ...REQUIRED_GATES.map((k) => gate(k, k === 'tests_passed' ? 'fail' : 'pass')),
      gate('tests_passed', 'pass'),
    ]);
    expect(missingRequiredGates(run)).toEqual([]);
    expect(isDelivered(run)).toBe(true);
  });
});

describe('gate coverage: the audit reports artifacts and process together', () => {
  it('names both the missing artifact and the missing gate', () => {
    const run: DeliveryRun = {
      ...forged([gate('source_evidence')]),
      evidence: {
        repoUrl: undefined,
        testsPassedAt: NOW(),
        deploymentUrl: 'https://widget.vercel.app',
        gates: [gate('source_evidence')],
      },
    };
    const problems = auditDeliveredRun(run);
    expect(problems).toContain('no repository was committed');
    expect(problems.some((p) => p.startsWith('gates never passed:'))).toBe(true);
  });

  it('a placeholder deployment URL fails the audit even with every gate green', () => {
    const run: DeliveryRun = {
      ...forged(REQUIRED_GATES.map((k) => gate(k))),
      evidence: {
        repoUrl: 'https://github.com/acme/widget',
        testsPassedAt: NOW(),
        deploymentUrl: 'https://localhost:3000',
        gates: REQUIRED_GATES.map((k) => gate(k)),
      },
    };
    expect(missingRequiredGates(run)).toEqual([]);
    expect(auditDeliveredRun(run).join(' ')).toContain('not a real live host');
    expect(isDelivered(run)).toBe(false);
  });
});
