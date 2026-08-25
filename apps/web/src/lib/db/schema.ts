/**
 * Drizzle schema for the delivery pipeline.
 *
 * Models one *delivery run*: a source (video or idea) taken through
 * requirements, a plan, human approval, an agent build, verification, and
 * deployment — ending in a verified artifact the customer can use.
 *
 * The organising principle is that **evidence is a column, not a log line**. A
 * run may only reach `delivered` when the rows proving it are present, and that
 * is enforced by database CHECK constraints (see `drizzle/0000_delivery.sql`),
 * not by application code. Application code can be bypassed, redeployed, or
 * simply wrong; a CHECK constraint makes a false success mathematically
 * impossible to store.
 */

import { relations } from 'drizzle-orm';
import {
  index,
  integer,
  jsonb,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
  uuid,
} from 'drizzle-orm/pg-core';

/**
 * Run phases.
 *
 * Extends the six-phase transcript lifecycle in `@/lib/action-lifecycle`, which
 * stopped at `fulfilled` — meaning "actions were dispatched". That could not
 * express building, verifying, or deploying, so a run that merely handed work
 * off looked identical to one that shipped (audit finding F7).
 *
 * `blocked` is deliberately distinct from `failed`. `failed` is an unexpected
 * crash; `blocked` is the *expected* outcome when a quality gate correctly
 * refuses to pass — tests red, deployment not serving traffic. Collapsing the
 * two is how a system starts reporting success it cannot prove.
 */
export const runStatus = pgEnum('run_status', [
  'sourcing',
  'requirements',
  'planning',
  'awaiting_approval',
  'building',
  'verifying',
  'deploying',
  'delivered',
  'blocked',
  'failed',
  'cancelled',
]);

/** Which gate a piece of evidence belongs to. */
export const gateKind = pgEnum('gate_kind', [
  'source_evidence',
  'requirements_complete',
  'plan_executable',
  'human_approved',
  'build_succeeded',
  'tests_passed',
  'deployment_live',
]);

export const gateResult = pgEnum('gate_result', ['pass', 'fail', 'skipped']);

export const artifactKind = pgEnum('artifact_kind', [
  'repository',
  'deployment',
  'test_report',
  'build_log',
  'transcript',
]);

/**
 * One delivery run.
 *
 * The four `*_at` / `*_url` evidence columns are denormalised onto this row on
 * purpose. A CHECK constraint cannot reference another table, so promoting the
 * three delivery facts here is what lets the database itself refuse a
 * `delivered` row that has no repository, no passing tests, and no live URL.
 */
export const deliveryRuns = pgTable(
  'delivery_runs',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    /** Owner. Every query on this table must filter by it — there is no RLS. */
    userId: text('user_id').notNull(),
    /** Short human label, derived from the source. */
    title: text('title').notNull(),
    status: runStatus('status').notNull().default('sourcing'),

    /** `video` or `idea`. */
    sourceKind: text('source_kind').notNull(),
    /** Video URL, or null for an idea-only run. */
    sourceUrl: text('source_url'),

    /** Workflow DevKit run id, for correlating durable execution. */
    workflowRunId: text('workflow_run_id'),

    // ── Delivery evidence (guarded by CHECK constraints) ──
    /** Committed repository containing the generated product. */
    repoUrl: text('repo_url'),
    /** Set only when a real test command exited zero. */
    testsPassedAt: timestamp('tests_passed_at', { withTimezone: true }),
    /** Set only when the deployment actually served a 2xx. */
    deploymentUrl: text('deployment_url'),
    deliveredAt: timestamp('delivered_at', { withTimezone: true }),

    /** Which gate refused, when `status = 'blocked'`. */
    blockedReason: text('blocked_reason'),
    /**
     * The phase the run was in when it blocked, so it can be resumed from the
     * failing stage instead of restarting work that already succeeded.
     */
    blockedFrom: text('blocked_from'),
    /** Populated when `status = 'failed'` (an unexpected crash, not a gate). */
    error: text('error'),

    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    // Dashboard query: a user's runs, newest first.
    index('delivery_runs_user_created_idx').on(table.userId, table.createdAt),
    index('delivery_runs_status_idx').on(table.status),
  ],
);

/**
 * Versioned requirements + execution plan.
 *
 * Versioned rather than updated in place so an approval always points at the
 * exact text approved. Mutating a spec after approval would let a run build
 * something the customer never agreed to while still showing a valid approval.
 */
export const runSpecs = pgTable(
  'run_specs',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    runId: uuid('run_id')
      .notNull()
      .references(() => deliveryRuns.id, { onDelete: 'cascade' }),
    version: integer('version').notNull().default(1),
    /** Structured requirements produced from the source. */
    requirements: jsonb('requirements').notNull(),
    /** Ordered, executable build steps. */
    plan: jsonb('plan').notNull(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [uniqueIndex('run_specs_run_version_idx').on(table.runId, table.version)],
);

/**
 * Durable step log — the replayable record of what the run actually did.
 *
 * This is the table that replaces `data/training/*.json`. Those writes targeted
 * `process.cwd()`, which on Vercel is a read-only bundle: every write threw and
 * the record was lost (audit finding F4).
 */
export const runSteps = pgTable(
  'run_steps',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    runId: uuid('run_id')
      .notNull()
      .references(() => deliveryRuns.id, { onDelete: 'cascade' }),
    /** Monotonic ordering within the run. */
    seq: integer('seq').notNull(),
    phase: runStatus('phase').notNull(),
    name: text('name').notNull(),
    status: text('status').notNull().default('running'),
    detail: jsonb('detail'),
    startedAt: timestamp('started_at', { withTimezone: true }).notNull().defaultNow(),
    finishedAt: timestamp('finished_at', { withTimezone: true }),
  },
  (table) => [
    // Also the idempotency guard: a retried durable step cannot double-insert.
    uniqueIndex('run_steps_run_seq_idx').on(table.runId, table.seq),
  ],
);

/**
 * Gate evaluations and the evidence behind them.
 *
 * `evidence` is NOT NULL for a reason: a gate that passes without recording why
 * is indistinguishable from one that was never run. This mirrors the existing
 * `assessAnalysisEvidence` discipline in the analysis phase and extends it
 * across build, test, and deploy.
 */
export const runGates = pgTable(
  'run_gates',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    runId: uuid('run_id')
      .notNull()
      .references(() => deliveryRuns.id, { onDelete: 'cascade' }),
    kind: gateKind('kind').notNull(),
    result: gateResult('result').notNull(),
    /** Proof: exit codes, counts, status codes, commit SHAs. */
    evidence: jsonb('evidence').notNull(),
    evaluatedAt: timestamp('evaluated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [uniqueIndex('run_gates_run_kind_idx').on(table.runId, table.kind)],
);

/** Produced artifacts: repository, deployment, test report, logs. */
export const runArtifacts = pgTable(
  'run_artifacts',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    runId: uuid('run_id')
      .notNull()
      .references(() => deliveryRuns.id, { onDelete: 'cascade' }),
    kind: artifactKind('kind').notNull(),
    uri: text('uri').notNull(),
    meta: jsonb('meta'),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index('run_artifacts_run_idx').on(table.runId)],
);

/**
 * Human approval of a specific spec version.
 *
 * `specId` rather than just `runId`: the approval must be traceable to the exact
 * requirements text the human read.
 */
export const runApprovals = pgTable(
  'run_approvals',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    runId: uuid('run_id')
      .notNull()
      .references(() => deliveryRuns.id, { onDelete: 'cascade' }),
    specId: uuid('spec_id')
      .notNull()
      .references(() => runSpecs.id, { onDelete: 'cascade' }),
    /** `approved` | `rejected` | `changes_requested`. */
    decision: text('decision').notNull(),
    decidedBy: text('decided_by').notNull(),
    note: text('note'),
    decidedAt: timestamp('decided_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [index('run_approvals_run_idx').on(table.runId)],
);

/**
 * Training dataset for fine-tuning.
 *
 * Replaces `data/training/video-analysis.jsonl`. The unique index on `videoUrl`
 * is the dedup guarantee — see `drizzle/0001_training.sql` for why the previous
 * application-level check was unsafe under concurrency.
 */
export const trainingExamples = pgTable(
  'training_examples',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    videoUrl: text('video_url').notNull(),
    videoTitle: text('video_title').notNull().default('Unknown'),
    /** Vertex AI SFT-formatted example. */
    example: jsonb('example').notNull(),
    /** Raw analysis output, so examples can be regenerated without re-analysing. */
    analysis: jsonb('analysis').notNull(),
    exportedAt: timestamp('exported_at', { withTimezone: true }),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    uniqueIndex('training_examples_video_url_idx').on(table.videoUrl),
    index('training_examples_created_idx').on(table.createdAt),
  ],
);

/** Singleton row tracking fine-tuning job state. */
export const trainingRuns = pgTable('training_runs', {
  id: integer('id').primaryKey().default(1),
  tuningTriggeredAt: timestamp('tuning_triggered_at', { withTimezone: true }),
  tuningJobId: text('tuning_job_id'),
});

// ── Relations ──

export const deliveryRunsRelations = relations(deliveryRuns, ({ many }) => ({
  specs: many(runSpecs),
  steps: many(runSteps),
  gates: many(runGates),
  artifacts: many(runArtifacts),
  approvals: many(runApprovals),
}));

export const runSpecsRelations = relations(runSpecs, ({ one, many }) => ({
  run: one(deliveryRuns, { fields: [runSpecs.runId], references: [deliveryRuns.id] }),
  approvals: many(runApprovals),
}));

export const runStepsRelations = relations(runSteps, ({ one }) => ({
  run: one(deliveryRuns, { fields: [runSteps.runId], references: [deliveryRuns.id] }),
}));

export const runGatesRelations = relations(runGates, ({ one }) => ({
  run: one(deliveryRuns, { fields: [runGates.runId], references: [deliveryRuns.id] }),
}));

export const runArtifactsRelations = relations(runArtifacts, ({ one }) => ({
  run: one(deliveryRuns, { fields: [runArtifacts.runId], references: [deliveryRuns.id] }),
}));

export const runApprovalsRelations = relations(runApprovals, ({ one }) => ({
  run: one(deliveryRuns, { fields: [runApprovals.runId], references: [deliveryRuns.id] }),
  spec: one(runSpecs, { fields: [runApprovals.specId], references: [runSpecs.id] }),
}));

// ── Inferred types ──

export type DeliveryRun = typeof deliveryRuns.$inferSelect;
export type NewDeliveryRun = typeof deliveryRuns.$inferInsert;
export type RunSpec = typeof runSpecs.$inferSelect;
export type RunStep = typeof runSteps.$inferSelect;
export type RunGate = typeof runGates.$inferSelect;
export type RunArtifact = typeof runArtifacts.$inferSelect;
export type RunApproval = typeof runApprovals.$inferSelect;
export type RunStatus = (typeof runStatus.enumValues)[number];
export type GateKind = (typeof gateKind.enumValues)[number];
