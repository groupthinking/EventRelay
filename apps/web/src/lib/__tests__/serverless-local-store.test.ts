import { afterEach, describe, expect, it, vi } from 'vitest';

const fsMocks = vi.hoisted(() => ({
  appendFile: vi.fn(async () => undefined),
  mkdir: vi.fn(async () => undefined),
  readFile: vi.fn(async () => ''),
  writeFile: vi.fn(async () => undefined),
}));

vi.mock('fs', () => ({
  promises: fsMocks,
}));

afterEach(() => {
  vi.clearAllMocks();
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function importTrainingStore() {
  vi.stubEnv('VERCEL', undefined);
  vi.stubEnv('VERCEL_ENV', 'preview');
  vi.resetModules();
  return import('@/lib/training-store');
}

async function importEmbeddingStore() {
  vi.stubEnv('VERCEL', undefined);
  vi.stubEnv('VERCEL_ENV', 'preview');
  vi.resetModules();
  return import('@/lib/embedding-store');
}

describe('local disk stores skip Vercel serverless filesystem access', () => {
  it('skips training store reads and writes when only VERCEL_ENV is set', async () => {
    fsMocks.mkdir.mockRejectedValue(new Error('mkdir should not run on Vercel'));
    fsMocks.appendFile.mockRejectedValue(new Error('appendFile should not run on Vercel'));
    fsMocks.writeFile.mockRejectedValue(new Error('writeFile should not run on Vercel'));
    fsMocks.readFile.mockRejectedValue(new Error('readFile should not run on Vercel'));

    const trainingStore = await importTrainingStore();

    await expect(trainingStore.getTrainingStatus()).resolves.toMatchObject({
      metadata: expect.objectContaining({ totalExamples: 0 }),
      nextMilestone: 25,
      progress: 0,
      readyForTuning: false,
    });
    await expect(trainingStore.readTrainingFile()).resolves.toBeNull();
    await expect(
      trainingStore.saveTrainingExample('https://youtu.be/auJzb1D-fag', { title: 'Preview deploy' }),
    ).resolves.toMatchObject({
      metadata: expect.objectContaining({ totalExamples: 0 }),
      milestone: null,
      saved: false,
    });

    expect(fsMocks.mkdir).not.toHaveBeenCalled();
    expect(fsMocks.appendFile).not.toHaveBeenCalled();
    expect(fsMocks.writeFile).not.toHaveBeenCalled();
    expect(fsMocks.readFile).not.toHaveBeenCalled();
  });

  it('skips embedding store reads and writes when only VERCEL_ENV is set', async () => {
    fsMocks.mkdir.mockRejectedValue(new Error('mkdir should not run on Vercel'));
    fsMocks.readFile.mockRejectedValue(new Error('readFile should not run on Vercel'));
    fsMocks.writeFile.mockRejectedValue(new Error('writeFile should not run on Vercel'));

    const embeddingStore = await importEmbeddingStore();

    await expect(
      embeddingStore.saveEmbeddings('auJzb1D-fag', [
        { duration: 5, embedding: [0.1, 0.2], start: 0, text: 'hello world' },
      ]),
    ).resolves.toBeUndefined();
    await expect(embeddingStore.loadEmbeddings('auJzb1D-fag')).resolves.toBeNull();

    expect(fsMocks.mkdir).not.toHaveBeenCalled();
    expect(fsMocks.readFile).not.toHaveBeenCalled();
    expect(fsMocks.writeFile).not.toHaveBeenCalled();
  });
});
