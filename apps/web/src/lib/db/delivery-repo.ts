/**
 * Persistence for delivery runs.
 *
 * This is the only module that writes to `delivery_runs`, `run_gates`, and
 * `run_approvals`. It exists so the workflow in `@/workflows/delivery-run.ts`
 * can record phase transitions and gate evidence from step functions without
 * embedding SQL in orchestration logic.
 *
 * ## Every write records evidence
 *
 * The database CHECK constraints (see `drizzle/0000_delivery.sql`) make a
 * `delivered` row without repo + passing tests + a real https deployment URL
 * *unstorable*, and a `pass` gate with `{}` evidence likewise. This module
 * never tries to work around those constraints — when one fires, that is the
 * design working, and the error propagates so the run lands in `blocked`
 * rather than silently reporting success.
 */

import { and, desc, eq } from 'drizzle-orm';
import { getDb, requireDb, type DeliveryDatabase } from '@/lib/db/client';
import {
  deliveryRuns,
  runApprovals,
  runGates,
  type GateKind,
  type RunStatus,
} from '@/lib/db/schema';
import {
  missingDeliveryEvidence,
  type DeliveryGate,
  type DeliveryPhase,
  type DeliveryRun,
} from '@/lib/delivery-lifecycle';

/** Row shape returned from `delivery_runs`. */
type RunRow = typeof deliveryRuns.$inferSelect;

/** Convert a persisted row into the in-memory lifecycle shape. */
function toDeliveryRun(row: RunRow, gates: DeliveryGate[]): DeliveryRun {
  return {
    id: row.id,
    phase: row.status as DeliveryPhase,
    sourceKind: row.sourceKind as 'video' | 'idea',
    sourceUrl: row.sourceUrl ?? undefined,
    evidence: {
      repoUrl: row.repoUrl ?? undefined,
      testsPassedAt: row.testsPassedAt?.toISOString(),
      deploymentUrl: row.deploymentUrl ?? undefined,
      gates,
    },
    blockedReason: row.blockedReason ?? undefined,
    blockedFrom: (row.blockedFrom as DeliveryPhase | null) ?? undefined,
    error: row.error ?? undefined,
    startedAt: row.startedAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export interface CreateRunInput {
  userId: string;
  title: string;
  sourceKind: 'video' | 'idea';
  sourceUrl?: string;
}

/** Insert a new run in `sourcing`. Returns its id. */
export async function createRun(input: CreateRunInput): Promise<string> {
  const db = requireDb('create a delivery run');
  const [row] = await db
    .insert(deliveryRuns)
    .values({
      userId: input.userId,
      title: input.title,
      sourceKind: input.sourceKind,
      sourceUrl: input.sourceUrl,
      status: 'sourcing',
    })
    .returning({ id: deliveryRuns.id });
  return row.id;
}

/** Load a run with its gate history, or null if absent. */
export async function loadRun(runId: string): Promise<DeliveryRun | null> {
  const db = getDb();
  if (!db) return null;

  const [row] = await db.select().from(deliveryRuns).where(eq(deliveryRuns.id, runId)).limit(1);
  if (!row) return null;

  const gateRows = await db
    .select()
    .from(runGates)
    .where(eq(runGates.runId, runId))
    .orderBy(runGates.evaluatedAt);

  const gates: DeliveryGate[] = gateRows.map((g) => ({
    kind: g.kind as GateKind,
    result: g.result as DeliveryGate['result'],
    evidence: (g.evidence ?? {}) as Record<string, unknown>,
    evaluatedAt: g.evaluatedAt.toISOString(),
  }));

  return toDeliveryRun(row, gates);
}

/**
 * Record a gate evaluation.
 *
 * `evidence` must be non-empty for a `pass` — the `run_gates_pass_needs_evidence`
 * constraint rejects `{}`, so a gate cannot be marked passed without proof.
 */
export async function recordGate(
  runId: string,
  kind: GateKind,
  result: DeliveryGate['result'],
  evidence: Record<string, unknown>,
): Promise<void> {
  const db = requireDb('record a gate result');
  await db.insert(runGates).values({ runId, kind, result, evidence });
}

/** Fields a phase transition may update alongside `status`. */
export interface PhasePatch {
  repoUrl?: string;
  testsPassedAt?: Date;
  deploymentUrl?: string;
  blockedReason?: string;
  blockedFrom?: DeliveryPhase;
  error?: string;
  deliveredAt?: Date;
}

/**
 * Move a run to `phase`, applying `patch`.
 *
 * Guarded so a caller cannot ask for `delivered` without the evidence being
 * present in the same write. The database would reject it anyway; failing here
 * produces a readable reason instead of a raw constraint violation.
 */
export async function setPhase(
  runId: string,
  phase: DeliveryPhase,
  patch: PhasePatch = {},
): Promise<void> {
  const db = requireDb('update a delivery run phase');

  if (phase === 'delivered') {
    const current = await loadRun(runId);
    if (!current) throw new Error(`Cannot deliver unknown run ${runId}`);
    const merged: DeliveryRun = {
      ...current,
      evidence: {
        ...current.evidence,
        repoUrl: patch.repoUrl ?? current.evidence.repoUrl,
        testsPassedAt: patch.testsPassedAt?.toISOString() ?? current.evidence.testsPassedAt,
        deploymentUrl: patch.deploymentUrl ?? current.evidence.deploymentUrl,
      },
    };
    const missing = missingDeliveryEvidence(merged);
    if (missing.length > 0) {
      throw new Error(`Refusing to mark run ${runId} delivered: ${missing.join('; ')}`);
    }
  }

  await db
    .update(deliveryRuns)
    .set({
      status: phase as RunStatus,
      updatedAt: new Date(),
      ...(patch.repoUrl !== undefined ? { repoUrl: patch.repoUrl } : {}),
      ...(patch.testsPassedAt !== undefined ? { testsPassedAt: patch.testsPassedAt } : {}),
      ...(patch.deploymentUrl !== undefined ? { deploymentUrl: patch.deploymentUrl } : {}),
      ...(patch.blockedReason !== undefined ? { blockedReason: patch.blockedReason } : {}),
      ...(patch.blockedFrom !== undefined ? { blockedFrom: patch.blockedFrom } : {}),
      ...(patch.error !== undefined ? { error: patch.error } : {}),
      ...(patch.deliveredAt !== undefined ? { deliveredAt: patch.deliveredAt } : {}),
    })
    .where(eq(deliveryRuns.id, runId));
}

/**
 * Move a run to `blocked` with a reason, remembering where it stopped.
 *
 * The reason is mandatory at the type level and by CHECK constraint: a blocked
 * run that cannot say why is indistinguishable from a silent failure.
 */
export async function blockRun(
  runId: string,
  from: DeliveryPhase,
  reason: string,
): Promise<void> {
  await setPhase(runId, 'blocked', { blockedReason: reason, blockedFrom: from });
}

/** Record a human approval decision. */
export async function recordApproval(
  runId: string,
  decision: 'approved' | 'rejected',
  decidedBy: string,
  note?: string,
): Promise<void> {
  const db = requireDb('record an approval');
  await db.insert(runApprovals).values({ runId, decision, decidedBy, note });
}

/** Most recent approval decision for a run, if any. */
export async function latestApproval(
  runId: string,
): Promise<{ decision: string; decidedBy: string } | null> {
  const db = getDb();
  if (!db) return null;
  const [row] = await db
    .select({ decision: runApprovals.decision, decidedBy: runApprovals.decidedBy })
    .from(runApprovals)
    .where(eq(runApprovals.runId, runId))
    .orderBy(desc(runApprovals.decidedAt))
    .limit(1);
  return row ?? null;
}

/** List a user's runs, newest first. */
export async function listRuns(userId: string, limit = 50): Promise<DeliveryRun[]> {
  const db = getDb();
  if (!db) return [];
  const rows = await db
    .select()
    .from(deliveryRuns)
    .where(eq(deliveryRuns.userId, userId))
    .orderBy(desc(deliveryRuns.startedAt))
    .limit(limit);
  return rows.map((row) => toDeliveryRun(row, []));
}

/** Find a run by user and source URL, used to avoid duplicate work. */
export async function findRunBySource(
  userId: string,
  sourceUrl: string,
): Promise<DeliveryRun | null> {
  const db = getDb();
  if (!db) return null;
  const [row] = await db
    .select()
    .from(deliveryRuns)
    .where(and(eq(deliveryRuns.userId, userId), eq(deliveryRuns.sourceUrl, sourceUrl)))
    .orderBy(desc(deliveryRuns.startedAt))
    .limit(1);
  return row ? toDeliveryRun(row, []) : null;
}

export type { DeliveryDatabase };
