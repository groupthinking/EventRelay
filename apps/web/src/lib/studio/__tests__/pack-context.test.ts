import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
const get = vi.hoisted(() => vi.fn());
vi.mock('../controls', () => ({ studioRedis: () => ({ get }) }));
let load: (hash: string | null) => Promise<string | null>;
beforeAll(async () => { load = (await import('../pack-context').catch(() => ({})) as { loadStudioPackContext: typeof load }).loadStudioPackContext; });
const hash = '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea';
const pack = { version: 'v0', video_id: 'auJzb1D-fag', source_url: 'https://www.youtube.com/watch?v=auJzb1D-fag', transcript: { full_text: 'An extracted demonstration' }, architecture: { summary: 'A counter', stages: [] }, artifacts: [{ path_hint: 'app/page.tsx', purpose: 'Counter', interface: 'Page()' }], stack: { tools: [{ name: 'Next.js', evidence: 'Extracted from video' }] }, provenance: { source_hash: hash, notes: 'Extracted, not execution verified' } };
beforeEach(() => { get.mockReset(); get.mockResolvedValue(JSON.stringify({ state: 'ready', pack })); });
async function read(value: string | null) { expect(load, 'Ready Video Pack handoff must exist').toBeTypeOf('function'); return load(value); }
describe('server-read Video Pack builder context', () => {
  it('does not read storage for a prompt-only app', async () => { expect(await read(null)).toBeNull(); expect(get).not.toHaveBeenCalled(); });
  it('loads the actual hashed pack from the existing REST namespace', async () => {
    const content = await read(hash); expect(get).toHaveBeenCalledWith(`er:videopack:v0:${hash}`);
    expect(content).toContain('A counter'); expect(content).toContain('app/page.tsx'); expect(content).toContain('Next.js'); expect(content).toMatch(/not.*verified/i);
  });
  it.each([null, '{}', JSON.stringify({ state: 'processing', pack }), JSON.stringify({ state: 'ready', pack: { ...pack, provenance: { source_hash: 'b'.repeat(64) } } }), JSON.stringify({ state: 'ready', pack: { ...pack, transcript: { full_text: 'cite:youtube:auJzb1D-fag' } } })])('holds missing or unverified readiness without inventing a pack', async (record) => {
    get.mockResolvedValue(record); await expect(read(hash)).rejects.toMatchObject({ status: 409 });
  });
  it('rejects noncanonical source identity', async () => {
    get.mockResolvedValue(JSON.stringify({ state: 'ready', pack: { ...pack, video_id: 'jNQXAC9IVRw' } }));
    await expect(read(hash)).rejects.toMatchObject({ status: 409 });
  });
  it('rejects hostile Redis key suffixes', async () => { await expect(read('../secret')).rejects.toMatchObject({ status: 400 }); expect(get).not.toHaveBeenCalled(); });
  it('does not leak a storage exception', async () => { get.mockRejectedValue(new Error('private')); await expect(read(hash)).rejects.toMatchObject({ status: 503 }); });
});
