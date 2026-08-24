/**
 * Integration tests for the Postgres-backed training store.
 *
 * These run against the real database because the bugs this rewrite fixed were
 * *environmental*, not logical: the old implementation passed every mocked unit
 * test while failing 100% of the time in production, because the mock hid the
 * read-only filesystem. Mocking the database here would recreate exactly that
 * blind spot.
 *
 * Skips itself when no connection string is present so it never breaks a
 * checkout without database access.
 */

import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { inArray, sql } from 'drizzle-orm';
import { getDb, queryRows, resolveDatabaseCapability } from '@/lib/db/client';
import { trainingExamples } from '@/lib/db/schema';
import {
  getMetadata,
  getTrainingStatus,
  readTrainingFile,
  saveTrainingExample,
  TUNING_THRESHOLD,
} from '@/lib/training-store';

const configured = resolveDatabaseCapability().configured;
const suite = configured ? describe : describe.skip;

// Per AGENTS.md, fixtures use auJzb1D-fag.
const VIDEO_A = 'https://www.youtube.com/watch?v=auJzb1D-fag';
const VIDEO_B = 'https://www.youtube.com/watch?v=auJzb1D-fag&t=90';
const TEST_URLS = [VIDEO_A, VIDEO_B];

async function cleanup() {
  const db = getDb();
  if (!db) return;
  // `inArray`, not `= ANY(${array})`: drizzle interpolates a JS array into a
  // template as a record literal `($1, $2)`, which Postgres cannot cast to
  // text[] ("cannot cast type record to text[]").
  await db.delete(trainingExamples).where(inArray(trainingExamples.videoUrl, TEST_URLS));
}

suite('training-store (Postgres-backed)', () => {
  beforeAll(cleanup);
  afterAll(cleanup);

  it('reads status without attempting any write', async () => {
    // The regression guard for F4: the old getMetadata() called ensureDir()
    // before reading, so a read-only filesystem made even a status check throw.
    // Reading must never depend on write access.
    const status = await getTrainingStatus();

    expect(status.metadata.totalExamples).toBeGreaterThanOrEqual(0);
    expect(status.progress).toBeGreaterThanOrEqual(0);
    expect(status.progress).toBeLessThanOrEqual(100);
    expect(status.readyForTuning).toBe(status.metadata.totalExamples >= TUNING_THRESHOLD);
  });

  it('persists an example and reflects it in metadata', async () => {
    const before = await getMetadata();

    const result = await saveTrainingExample(VIDEO_A, {
      title: 'Integration Fixture A',
      summary: 'persisted to Postgres',
    });

    expect(result.saved).toBe(true);
    expect(result.metadata.totalExamples).toBe(before.totalExamples + 1);
    expect(result.metadata.lastVideoTitle).toBe('Integration Fixture A');

    // Survives a fresh read — proving it was actually written, not just
    // returned. The filesystem version returned an incremented count from an
    // in-memory object while the write had already failed.
    const reread = await getMetadata();
    expect(reread.totalExamples).toBe(before.totalExamples + 1);
    expect(reread.videosProcessed).toContain(VIDEO_A);
  });

  it('refuses a duplicate video', async () => {
    const before = await getMetadata();
    const result = await saveTrainingExample(VIDEO_A, { title: 'Duplicate attempt' });

    expect(result.saved).toBe(false);
    expect(result.metadata.totalExamples).toBe(before.totalExamples);
  });

  it('holds dedup under concurrent saves of the same video', async () => {
    // The old `videosProcessed.includes(url)` check was read-then-write with no
    // atomicity: concurrent runs could both pass it and both append, corrupting
    // the fine-tuning dataset. Dedup is now a UNIQUE index.
    const results = await Promise.all(
      Array.from({ length: 5 }, () =>
        saveTrainingExample(VIDEO_B, { title: 'Concurrent Fixture B' }),
      ),
    );

    expect(results.filter((r) => r.saved)).toHaveLength(1);

    const rows = await queryRows<{ c: number }>(
      getDb()!,
      sql`SELECT COUNT(*)::int AS c FROM training_examples WHERE video_url = ${VIDEO_B}`,
    );
    expect(rows[0].c).toBe(1);
  });

  it('serialises the dataset as valid JSONL', async () => {
    const jsonl = await readTrainingFile();
    expect(jsonl).not.toBeNull();

    const lines = jsonl!.trim().split('\n');
    expect(lines.length).toBeGreaterThan(0);

    for (const line of lines) {
      const parsed = JSON.parse(line);
      // Vertex AI SFT shape: alternating user/model turns.
      expect(parsed.contents).toHaveLength(2);
      expect(parsed.contents[0].role).toBe('user');
      expect(parsed.contents[1].role).toBe('model');
      expect(typeof parsed.contents[1].parts[0].text).toBe('string');
    }
  });
});

describe('database capability resolution', () => {
  it('accepts either NEON_DATABASE_URL or POSTGRES_URL', () => {
    // F1 was caused by reading a single hardcoded env var name while the
    // deployment supplied a differently-named equivalent.
    const host = 'db.example.com';
    const url = `postgres://u:p@${host}/main`;

    expect(resolveDatabaseCapability({ NEON_DATABASE_URL: url }).source).toBe(
      'NEON_DATABASE_URL',
    );
    expect(resolveDatabaseCapability({ POSTGRES_URL: url }).source).toBe('POSTGRES_URL');
    expect(resolveDatabaseCapability({ POSTGRES_URL: url }).host).toBe(host);
  });

  it('never leaks credentials in diagnostics', () => {
    const capability = resolveDatabaseCapability({
      NEON_DATABASE_URL: 'postgres://user:sup3rsecret@db.example.com/main',
    });
    expect(JSON.stringify(capability)).not.toContain('sup3rsecret');
  });

  it('skips a malformed connection string rather than accepting it', () => {
    // A malformed value is worse than a missing one: it looks configured and
    // then fails at query time, far from the misconfiguration.
    const capability = resolveDatabaseCapability({
      NEON_DATABASE_URL: 'not-a-url',
      POSTGRES_URL: 'postgres://u:p@good.example.com/main',
    });
    expect(capability.source).toBe('POSTGRES_URL');
  });

  it('reports unconfigured with actionable guidance', () => {
    const capability = resolveDatabaseCapability({});
    expect(capability.configured).toBe(false);
    expect(capability.reason).toContain('NEON_DATABASE_URL');
  });
});
