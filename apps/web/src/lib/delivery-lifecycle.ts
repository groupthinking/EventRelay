/**
 * Lifecycle state machine for a delivery run.
 *
 * A run carries a source (a video or a written idea) through to a verified,
 * shipped product:
 *
 *   sourcing → requirements → planning → awaiting_approval
 *            → building → verifying → deploying → delivered
 *
 * ## Why this is a separate module from `action-lifecycle.ts`
 *
 * `action-lifecycle.ts` models something different: a single *voice prompt*
 * session (`idle → capturing → transcribing → extracting → dispatching →
 * fulfilled`). Its `fulfilled` means "the extracted tool calls were dispatched",
 * and it has microphone-capture phases that have no meaning for a delivery run.
 *
 * Audit finding F7 was that no state machine could express building, verifying,
 * or deploying — so a run that merely *handed work off* was indistinguishable
 * from one that actually shipped. Widening the voice-prompt machine to cover
 * deployment would have conflated two unrelated domains (a `capturing` delivery
 * run is meaningless, and so is a `deploying` microphone session). Instead this
 * is a sibling machine that reuses the proven patterns from that module — pure
 * reducer, explicit transition table, `canTransition` guard, terminal states
 * that refuse to be clobbered — and drops the ones that do not apply.
 *
 * ## `blocked` is not `failed`
 *
 * These are deliberately distinct terminal-ish states:
 *
 * - `failed` — the system broke. An exception, a crash, infrastructure trouble.
 *   Nothing is known about the product.
 * - `blocked` — the system worked correctly and *refused to claim success*
 *   because a gate had no evidence. The tests did not pass; the deployment did
 *   not return 200. A `blocked` run always carries a reason naming the gate,
 *   and is resumable once the underlying problem is fixed.
 *
 * Collapsing the two would recreate the exact failure this pipeline exists to
 * prevent: a run reporting "done" when nothing verifiable happened.
 *
 * The phase names match the `run_status` enum in `@/lib/db/schema` one-for-one
 * so a persisted row and an in-memory reduction can never disagree.
 */

import type { GateKind, RunStatus } from '@/lib/db/schema';

// ── States ──

/**
 * Run phases. Structurally identical to the DB `run_status` enum — the
 * satisfies check below fails the build if the two ever drift apart.
 */
export type DeliveryPhase =
  | 'sourcing'
  | 'requirements'
  | 'planning'
  | 'awaiting_approval'
  | 'building'
  | 'verifying'
  | 'deploying'
  | 'delivered'
  | 'blocked'
  | 'failed'
  | 'cancelled';

// Compile-time proof that this union and the database enum stay in sync. If a
// phase is added to one and not the other, this stops type-checking.
type _PhaseMatchesDb = DeliveryPhase extends RunStatus
  ? RunStatus extends DeliveryPhase
    ? true
    : never
  : never;
const _phaseParity: _PhaseMatchesDb = true;
void _phaseParity;

/** Phases from which no further progress is possible without operator action. */
const TERMINAL: ReadonlySet<DeliveryPhase> = new Set<DeliveryPhase>([
  'delivered',
  'failed',
  'cancelled',
]);

/**
 * The evidence a run has accumulated.
 *
 * Mirrors the guarded columns on `delivery_runs`. Every field starts absent and
 * may only be filled by an event carrying real proof.
 */
export interface DeliveryEvidence {
  /** Committed repository containing the generated product. */
  repoUrl?: string;
  /** Set only when a real test command exited zero. */
  testsPassedAt?: string;
  /** Set only when the deployment answered a live request. */
  deploymentUrl?: string;
  /** Gate outcomes recorded so far, newest last. */
  gates: DeliveryGate[];
}

/** One gate evaluation and the proof behind it. */
export interface DeliveryGate {
  kind: GateKind;
  result: 'pass' | 'fail' | 'skipped';
  /** Proof: exit codes, counts, status codes, commit SHAs. */
  evidence: Record<string, unknown>;
  evaluatedAt: string;
}

/** The full record tracked for one delivery run. */
export interface DeliveryRun {
  id: string;
  phase: DeliveryPhase;
  /** `video` or `idea`. */
  sourceKind: 'video' | 'idea';
  /** Video URL, or undefined for an idea-only run. */
  sourceUrl?: string;
  evidence: DeliveryEvidence;
  /**
   * Why the run is blocked. Required whenever `phase === 'blocked'`, so a
   * blocked run can never be silent about the reason.
   */
  blockedReason?: string;
  /** The phase the run was in when it became blocked, for resumption. */
  blockedFrom?: DeliveryPhase;
  /** Populated when `phase === 'failed'`. */
  error?: string;
  startedAt: string;
  updatedAt: string;
}

// ── Events ──

export type DeliveryEvent =
  | { type: 'SOURCE_VERIFIED'; evidence: Record<string, unknown> }
  | { type: 'REQUIREMENTS_DRAFTED'; evidence: Record<string, unknown> }
  | { type: 'PLAN_READY'; evidence: Record<string, unknown> }
  | { type: 'APPROVED'; approvedBy: string }
  | { type: 'REJECTED'; reason: string }
  | { type: 'BUILD_SUCCEEDED'; repoUrl: string; evidence: Record<string, unknown> }
  | { type: 'TESTS_PASSED'; testsPassedAt: string; evidence: Record<string, unknown> }
  | { type: 'DEPLOYED'; deploymentUrl: string; evidence: Record<string, unknown> }
  /** A gate had insufficient evidence. Moves to `blocked`, never to delivered. */
  | { type: 'GATE_FAILED'; gate: GateKind; reason: string; evidence?: Record<string, unknown> }
  /** Resume a blocked run from where it stopped. */
  | { type: 'RESUME' }
  | { type: 'ERROR'; error: string }
  | { type: 'CANCEL'; reason?: string };

// ── Transition table ──

/**
 * Allowed happy-path transitions. `GATE_FAILED`, `ERROR`, `CANCEL`, and
 * `RESUME` are handled separately because they are valid from many phases.
 */
const TRANSITIONS: Record<
  DeliveryPhase,
  Partial<Record<DeliveryEvent['type'], DeliveryPhase>>
> = {
  sourcing: { SOURCE_VERIFIED: 'requirements' },
  requirements: { REQUIREMENTS_DRAFTED: 'planning' },
  planning: { PLAN_READY: 'awaiting_approval' },
  awaiting_approval: { APPROVED: 'building', REJECTED: 'cancelled' },
  building: { BUILD_SUCCEEDED: 'verifying' },
  verifying: { TESTS_PASSED: 'deploying' },
  deploying: { DEPLOYED: 'delivered' },
  delivered: {},
  blocked: {},
  failed: {},
  cancelled: {},
};

/** Returns true if `event` is a legal transition from `phase`. */
export function canTransition(phase: DeliveryPhase, event: DeliveryEvent['type']): boolean {
  // A terminal outcome is never overwritten by a late event.
  if (TERMINAL.has(phase)) return false;
  // Gate failure, error, and cancel are valid from any non-terminal phase.
  if (event === 'GATE_FAILED' || event === 'ERROR' || event === 'CANCEL') return true;
  // Only a blocked run can resume.
  if (event === 'RESUME') return phase === 'blocked';
  return TRANSITIONS[phase]?.[event] !== undefined;
}

// ── Delivery evidence guard ──

/**
 * Hostnames that are never proof of a live deployment.
 *
 * Kept in lockstep with the `delivery_runs_deployment_url_real` CHECK
 * constraint in `drizzle/0000_delivery.sql`. A local dev server answering 200
 * is not a shipped product, and `localhost` was the exact placeholder that let
 * the old backend resolver look healthy while nothing was reachable.
 */
export const PLACEHOLDER_HOSTS = [
  'localhost',
  '127.0.0.1',
  '0.0.0.0',
  '[::1]',
  'example.com',
  'example.org',
  'example.net',
] as const;

/**
 * True when `url` is a real, live, absolute **https** deployment URL.
 *
 * https is required, not merely preferred: a delivered product served over
 * plain http is not something to claim as shipped, and the database CHECK has
 * always enforced https. This function previously also accepted `http:`, which
 * meant the two layers disagreed — caught by the parity suite in
 * `delivery-guard-parity.integration.test.ts`.
 */
export function isRealDeploymentUrl(url: string | undefined): boolean {
  if (!url) return false;
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (parsed.protocol !== 'https:') return false;
  const host = parsed.hostname.toLowerCase();
  return !PLACEHOLDER_HOSTS.some((bad) => host === bad || host.endsWith(`.${bad}`));
}

/**
 * The three facts that must all hold before a run may be called `delivered`.
 *
 * Returns the list of missing requirements — empty means deliverable. This is
 * the application-layer twin of the `delivery_runs_delivered_needs_evidence`
 * CHECK constraint: the database is the last line of defence, and this gives a
 * readable reason instead of a constraint-violation error string.
 */
export function missingDeliveryEvidence(run: DeliveryRun): string[] {
  const missing: string[] = [];
  if (!run.evidence.repoUrl) missing.push('no repository was committed');
  if (!run.evidence.testsPassedAt) missing.push('tests never passed');
  if (!isRealDeploymentUrl(run.evidence.deploymentUrl)) {
    missing.push(
      run.evidence.deploymentUrl
        ? `deployment URL is not a real live host (${run.evidence.deploymentUrl})`
        : 'no live deployment URL',
    );
  }
  return missing;
}

// ── Construction ──

export function createRun(
  id: string,
  source: { kind: 'video'; url: string } | { kind: 'idea' },
  now: () => string = () => new Date().toISOString(),
): DeliveryRun {
  const ts = now();
  return {
    id,
    phase: 'sourcing',
    sourceKind: source.kind,
    sourceUrl: source.kind === 'video' ? source.url : undefined,
    evidence: { gates: [] },
    startedAt: ts,
    updatedAt: ts,
  };
}

// ── Reducer ──

function withGate(
  evidence: DeliveryEvidence,
  kind: GateKind,
  result: DeliveryGate['result'],
  proof: Record<string, unknown>,
  at: string,
): DeliveryEvidence {
  return { ...evidence, gates: [...evidence.gates, { kind, result, evidence: proof, evaluatedAt: at }] };
}

/**
 * Pure reducer. Applies `event` to `run`, returning a new run.
 *
 * Illegal transitions become `blocked` (not `failed`): an unexpected event
 * ordering means the pipeline could not prove it should advance, which is a
 * refusal to claim success rather than a system fault.
 */
export function reduceRun(
  run: DeliveryRun,
  event: DeliveryEvent,
  now: () => string = () => new Date().toISOString(),
): DeliveryRun {
  const updatedAt = now();

  // A terminal run ignores everything. Never clobber a recorded outcome.
  if (TERMINAL.has(run.phase)) return run;

  if (event.type === 'ERROR') {
    return { ...run, phase: 'failed', error: event.error, updatedAt };
  }

  if (event.type === 'CANCEL') {
    return { ...run, phase: 'cancelled', blockedReason: event.reason, updatedAt };
  }

  if (event.type === 'GATE_FAILED') {
    return {
      ...run,
      phase: 'blocked',
      blockedReason: `${event.gate}: ${event.reason}`,
      // Remember where to resume from, unless already blocked.
      blockedFrom: run.phase === 'blocked' ? run.blockedFrom : run.phase,
      evidence: withGate(run.evidence, event.gate, 'fail', event.evidence ?? {}, updatedAt),
      updatedAt,
    };
  }

  if (event.type === 'RESUME') {
    if (!canTransition(run.phase, 'RESUME')) return run;
    return {
      ...run,
      phase: run.blockedFrom ?? 'sourcing',
      blockedReason: undefined,
      blockedFrom: undefined,
      updatedAt,
    };
  }

  if (!canTransition(run.phase, event.type)) {
    return {
      ...run,
      phase: 'blocked',
      blockedReason: `Illegal transition: ${event.type} from ${run.phase}`,
      blockedFrom: run.phase,
      updatedAt,
    };
  }

  const phase = TRANSITIONS[run.phase][event.type] as DeliveryPhase;

  switch (event.type) {
    case 'SOURCE_VERIFIED':
      return {
        ...run,
        phase,
        evidence: withGate(run.evidence, 'source_evidence', 'pass', event.evidence, updatedAt),
        updatedAt,
      };

    case 'REQUIREMENTS_DRAFTED':
      return {
        ...run,
        phase,
        evidence: withGate(run.evidence, 'requirements_complete', 'pass', event.evidence, updatedAt),
        updatedAt,
      };

    case 'PLAN_READY':
      return {
        ...run,
        phase,
        evidence: withGate(run.evidence, 'plan_executable', 'pass', event.evidence, updatedAt),
        updatedAt,
      };

    case 'APPROVED':
      return {
        ...run,
        phase,
        evidence: withGate(
          run.evidence,
          'human_approved',
          'pass',
          { approvedBy: event.approvedBy },
          updatedAt,
        ),
        updatedAt,
      };

    case 'REJECTED':
      return { ...run, phase, blockedReason: event.reason, updatedAt };

    case 'BUILD_SUCCEEDED':
      return {
        ...run,
        phase,
        evidence: {
          ...withGate(run.evidence, 'build_succeeded', 'pass', event.evidence, updatedAt),
          repoUrl: event.repoUrl,
        },
        updatedAt,
      };

    case 'TESTS_PASSED':
      return {
        ...run,
        phase,
        evidence: {
          ...withGate(run.evidence, 'tests_passed', 'pass', event.evidence, updatedAt),
          testsPassedAt: event.testsPassedAt,
        },
        updatedAt,
      };

    case 'DEPLOYED': {
      // The final guard. Even a legal DEPLOYED event cannot produce a
      // `delivered` run unless every piece of evidence is actually present —
      // this is what makes "shipped" mean shipped. A run that reaches here
      // without proof becomes `blocked`, never `delivered`.
      const candidate: DeliveryRun = {
        ...run,
        evidence: {
          ...withGate(run.evidence, 'deployment_live', 'pass', event.evidence, updatedAt),
          deploymentUrl: event.deploymentUrl,
        },
      };
      const missing = missingDeliveryEvidence(candidate);
      if (missing.length > 0) {
        return {
          ...candidate,
          phase: 'blocked',
          blockedReason: `Cannot mark delivered: ${missing.join('; ')}`,
          blockedFrom: run.phase,
          evidence: withGate(
            candidate.evidence,
            'deployment_live',
            'fail',
            { ...event.evidence, missing },
            updatedAt,
          ),
          updatedAt,
        };
      }
      return { ...candidate, phase, updatedAt };
    }

    default:
      return { ...run, phase, updatedAt };
  }
}

/** True once the run has shipped with complete evidence. */
export function isDelivered(run: DeliveryRun): boolean {
  return run.phase === 'delivered' && missingDeliveryEvidence(run).length === 0;
}
