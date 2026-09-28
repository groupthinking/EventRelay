import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { PGlite } from '@electric-sql/pglite';
import { drizzle } from 'drizzle-orm/pglite';
import { migrate } from 'drizzle-orm/pglite/migrator';
import { eq } from 'drizzle-orm';
import * as schema from './schema';
import { createRunStore, hashBuildSpec } from './store';

const author = { tenantId: 'tenant-a', userId: 'author-a' };
const outsider = { tenantId: 'tenant-b', userId: 'author-b' };
const viewer = { tenantId: 'tenant-a', userId: 'viewer-a' };
const spec = { objective: 'Build an approved website', acceptanceCriteria: ['Home page renders'],
  deploymentTarget: 'preview-project', budgetCents: 100, capabilities: ['build'] };

describe('durable run approval transactions', () => {
  let pg: PGlite;
  let directory: string;
  let db: ReturnType<typeof drizzle<typeof schema>>;
  let store: ReturnType<typeof createRunStore>;
  beforeEach(async () => {
    directory = await mkdtemp(join(tmpdir(), 'uvai-run-test-'));
    pg = new PGlite(directory);
    db = drizzle(pg, { schema });
    await migrate(db, { migrationsFolder: './drizzle/runs' });
    await db.insert(schema.runMembers).values([
      { ...author, role: 'author' }, { ...outsider, role: 'owner' }, { ...viewer, role: 'viewer' },
    ]);
    store = createRunStore(db);
  });
  afterEach(async () => { await pg?.close(); await rm(directory, { recursive: true, force: true }); });

  it('requires approval, then persists the approved scope and ordered events', async () => {
    const run = await store.create(author, 'project', spec);
    await expect(store.beginPlanning(author, run.id, 1)).rejects.toThrow('not approved');
    await store.approve(author, run.id, 1, run.specHash);
    await store.beginPlanning(author, run.id, 2);
    const result = await store.read(author, run.id);
    expect(result.status).toBe('planning');
    expect(result.events.map((e) => e.revision)).toEqual([1, 2, 3]);
    const [approval] = await db.select().from(schema.runApprovals);
    expect(approval.approvedSpec).toEqual(spec);
    expect(approval.approverId).toBe(author.userId);
  });

  it('retains approval and run state after database restart', async () => {
    const run = await store.create(author, 'project', spec);
    await store.approve(author, run.id, 1, run.specHash);
    await pg.close();
    pg = new PGlite(directory);
    db = drizzle(pg, { schema });
    store = createRunStore(db);
    expect((await store.read(author, run.id)).status).toBe('approved');
    expect((await store.beginPlanning(author, run.id, 2)).status).toBe('planning');
  });

  it('denies cross-tenant reads and approvals and viewer writes', async () => {
    const run = await store.create(author, 'project', spec);
    await expect(store.read(outsider, run.id)).rejects.toThrow('not found');
    await expect(store.approve(outsider, run.id, 1, run.specHash)).rejects.toThrow();
    await expect(store.approve(viewer, run.id, 1, run.specHash)).rejects.toThrow('access denied');
    await expect(store.create({ tenantId: 'tenant-a', userId: 'unknown' }, 'project', spec)).rejects.toThrow('access denied');
    expect((await store.read(author, run.id)).events).toHaveLength(1);
  });

  it('rejects stale hashes and duplicate approvals without duplicate events', async () => {
    const run = await store.create(author, 'project', spec);
    await expect(store.approve(author, run.id, 1, 'wrong-hash')).rejects.toThrow();
    await store.approve(author, run.id, 1, run.specHash);
    await expect(store.approve(author, run.id, 1, run.specHash)).rejects.toThrow();
    expect((await store.read(author, run.id)).events).toHaveLength(2);
  });

  it('requires reapproval after scope changes while retaining the old approval', async () => {
    const run = await store.create(author, 'project', spec);
    await store.approve(author, run.id, 1, run.specHash);
    const changed = await store.revise(author, run.id, 2, { ...spec, budgetCents: 200 });
    await expect(store.beginPlanning(author, run.id, 3)).rejects.toThrow();
    await expect(store.approve(author, run.id, 3, run.specHash)).rejects.toThrow();
    await store.approve(author, run.id, 3, changed.specHash);
    await store.beginPlanning(author, run.id, 4);
    expect(await db.select().from(schema.runApprovals)).toHaveLength(2);
    await expect(store.revise(author, run.id, 5, spec)).rejects.toThrow('executing');
  });

  it('rolls back the state transition if the approval evidence is missing', async () => {
    const run = await store.create(author, 'project', spec);
    await store.approve(author, run.id, 1, run.specHash);
    await db.delete(schema.runApprovals).where(eq(schema.runApprovals.runId, run.id));
    await expect(store.beginPlanning(author, run.id, 2)).rejects.toThrow('approval required');
    const result = await store.read(author, run.id);
    expect(result.status).toBe('approved');
    expect(result.revision).toBe(2);
    expect(result.events).toHaveLength(2);
  });

  it('rejects tampered spec bytes and rolls back approval', async () => {
    const run = await store.create(author, 'project', spec);
    await db.update(schema.runs).set({ spec: { ...spec, budgetCents: 900 } }).where(eq(schema.runs.id, run.id));
    await expect(store.approve(author, run.id, 1, run.specHash)).rejects.toThrow('integrity');
    expect((await store.read(author, run.id)).status).toBe('awaiting_spec_approval');
    expect(await db.select().from(schema.runApprovals)).toHaveLength(0);
  });

  it('hashes the approved budget and capabilities and rejects invalid budgets', () => {
    expect(hashBuildSpec(spec)).not.toBe(hashBuildSpec({ ...spec, capabilities: ['deploy'] }));
    expect(() => hashBuildSpec({ ...spec, budgetCents: -1 })).toThrow();
  });
});
