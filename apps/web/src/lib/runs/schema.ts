import { pgTable, text, integer, jsonb, timestamp, primaryKey, uniqueIndex } from 'drizzle-orm/pg-core';

export interface BuildSpec {
  objective: string;
  acceptanceCriteria: string[];
  deploymentTarget: string;
  budgetCents: number;
  capabilities: string[];
}

// Membership must be provisioned by a trusted organization administrator.
// Request bodies are never an authority source for these records.
export const runMembers = pgTable('uvai_run_members', {
  tenantId: text('tenant_id').notNull(),
  userId: text('user_id').notNull(),
  role: text('role', { enum: ['owner', 'author', 'viewer'] }).notNull(),
}, (t) => [primaryKey({ columns: [t.tenantId, t.userId] })]);

export const runs = pgTable('uvai_runs', {
  id: text('id').primaryKey(),
  tenantId: text('tenant_id').notNull(),
  projectId: text('project_id').notNull(),
  status: text('status', { enum: ['awaiting_spec_approval', 'approved', 'planning'] }).notNull(),
  revision: integer('revision').notNull().default(1),
  spec: jsonb('spec').$type<BuildSpec>().notNull(),
  specHash: text('spec_hash').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const runApprovals = pgTable('uvai_run_approvals', {
  runId: text('run_id').notNull().references(() => runs.id),
  specHash: text('spec_hash').notNull(),
  specRevision: integer('spec_revision').notNull(),
  approverId: text('approver_id').notNull(),
  approvedSpec: jsonb('approved_spec').$type<BuildSpec>().notNull(),
  approvedAt: timestamp('approved_at', { withTimezone: true }).defaultNow().notNull(),
}, (t) => [primaryKey({ columns: [t.runId, t.specRevision] })]);

export const runEvents = pgTable('uvai_run_events', {
  id: text('id').primaryKey(),
  runId: text('run_id').notNull().references(() => runs.id),
  revision: integer('revision').notNull(),
  kind: text('kind').notNull(),
  actorId: text('actor_id').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
}, (t) => [uniqueIndex('uvai_run_event_revision').on(t.runId, t.revision)]);
