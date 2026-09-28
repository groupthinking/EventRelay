import { createHash, randomUUID } from 'node:crypto';
import { and, eq, inArray } from 'drizzle-orm';
import type { PgDatabase, PgQueryResultHKT } from 'drizzle-orm/pg-core';
import * as schema from './schema';
import { runMembers, runs, runApprovals, runEvents, type BuildSpec } from './schema';

export type RunPrincipal = { tenantId: string; userId: string };

export function hashBuildSpec(spec: BuildSpec): string {
  if (!spec.objective?.trim() || !spec.deploymentTarget?.trim()
    || !Number.isSafeInteger(spec.budgetCents) || spec.budgetCents < 0
    || !Array.isArray(spec.acceptanceCriteria) || !spec.acceptanceCriteria.length
    || spec.acceptanceCriteria.some((s) => typeof s !== 'string' || !s.trim())
    || !Array.isArray(spec.capabilities)
    || spec.capabilities.some((s) => typeof s !== 'string' || !s.trim())) {
    throw new Error('Invalid build specification');
  }
  // Fixed field order; array order is significant. No implicit scope rewriting.
  return createHash('sha256').update(JSON.stringify({
    objective: spec.objective, acceptanceCriteria: spec.acceptanceCriteria,
    deploymentTarget: spec.deploymentTarget, budgetCents: spec.budgetCents,
    capabilities: spec.capabilities,
  })).digest('hex');
}

/** Internal service only. Resolve userId from authentication, never request JSON.
 * Membership is checked inside each transaction. No deployment side effects here.
 */
export function createRunStore<Q extends PgQueryResultHKT>(db: PgDatabase<Q, typeof schema>) {
  async function authorize(tx: PgDatabase<Q, typeof schema>, actor: RunPrincipal, write: boolean) {
    const [member] = await tx.select().from(runMembers).where(and(
      eq(runMembers.tenantId, actor.tenantId), eq(runMembers.userId, actor.userId),
    ));
    if (!member || (write && !['owner', 'author'].includes(member.role))) {
      throw new Error('Run access denied');
    }
  }
  const scope = (actor: RunPrincipal, id: string) => and(eq(runs.id, id), eq(runs.tenantId, actor.tenantId));

  return {
    async create(actor: RunPrincipal, projectId: string, spec: BuildSpec) {
      if (!projectId.trim()) throw new Error('Project id required');
      spec = structuredClone(spec);
      const specHash = hashBuildSpec(spec);
      return db.transaction(async (tx) => {
        await authorize(tx, actor, true);
        const [run] = await tx.insert(runs).values({ id: randomUUID(), tenantId: actor.tenantId,
          projectId, status: 'awaiting_spec_approval', spec, specHash }).returning();
        await tx.insert(runEvents).values({ id: randomUUID(), runId: run.id, revision: 1,
          kind: 'spec.awaiting_approval', actorId: actor.userId });
        return run;
      });
    },
    async revise(actor: RunPrincipal, id: string, revision: number, spec: BuildSpec) {
      spec = structuredClone(spec);
      const specHash = hashBuildSpec(spec);
      return db.transaction(async (tx) => {
        await authorize(tx, actor, true);
        const [run] = await tx.update(runs).set({ spec, specHash,
          status: 'awaiting_spec_approval', revision: revision + 1 }).where(and(
          scope(actor, id), eq(runs.revision, revision),
          inArray(runs.status, ['awaiting_spec_approval', 'approved']),
        )).returning();
        if (!run) throw new Error('Cannot revise stale or executing run');
        await tx.insert(runEvents).values({ id: randomUUID(), runId: id, revision: run.revision,
          kind: 'spec.revised', actorId: actor.userId });
        return run;
      });
    },
    async read(actor: RunPrincipal, id: string) {
      return db.transaction(async (tx) => {
        await authorize(tx, actor, false);
        const [run] = await tx.select().from(runs).where(scope(actor, id));
        if (!run) throw new Error('Run not found');
        const events = await tx.select().from(runEvents).where(eq(runEvents.runId, id)).orderBy(runEvents.revision);
        return { ...run, events };
      });
    },
    async approve(actor: RunPrincipal, id: string, revision: number, specHash: string) {
      return db.transaction(async (tx) => {
        await authorize(tx, actor, true);
        const [run] = await tx.update(runs).set({ status: 'approved', revision: revision + 1 }).where(and(
          scope(actor, id), eq(runs.status, 'awaiting_spec_approval'),
          eq(runs.revision, revision), eq(runs.specHash, specHash),
        )).returning();
        if (!run) throw new Error('Stale or unauthorized approval');
        if (hashBuildSpec(run.spec) !== specHash) throw new Error('Specification integrity failure');
        await tx.insert(runApprovals).values({ runId: id, specHash, specRevision: revision,
          approverId: actor.userId, approvedSpec: run.spec });
        await tx.insert(runEvents).values({ id: randomUUID(), runId: id, revision: run.revision,
          kind: 'spec.approved', actorId: actor.userId });
        return run;
      });
    },
    async beginPlanning(actor: RunPrincipal, id: string, revision: number) {
      return db.transaction(async (tx) => {
        await authorize(tx, actor, true);
        const [run] = await tx.update(runs).set({ status: 'planning', revision: revision + 1 }).where(and(
          scope(actor, id), eq(runs.status, 'approved'), eq(runs.revision, revision),
        )).returning();
        if (!run) throw new Error('Run is not approved at the expected revision');
        const [approval] = await tx.select().from(runApprovals).where(and(
          eq(runApprovals.runId, id), eq(runApprovals.specRevision, revision - 1),
        ));
        if (!approval || approval.specHash !== run.specHash
          || hashBuildSpec(run.spec) !== run.specHash
          || hashBuildSpec(approval.approvedSpec) !== run.specHash) {
          throw new Error('Matching specification approval required');
        }
        await tx.insert(runEvents).values({ id: randomUUID(), runId: id, revision: run.revision,
          kind: 'planning.started', actorId: actor.userId });
        return run;
      });
    },
  };
}
