import { createHash } from 'crypto';
import { describe, expect, it } from 'vitest';
import { VERIFIED_BENCHMARKS, getBenchmarkByYoutubeId } from '../verified-benchmarks';
import { buildScaffoldPackage } from '../action-surface';
import { transcriptTextFromSegments } from '../analysis-evidence';

describe('verified-benchmarks', () => {
  it('exposes three verified enterprise benchmarks with passing quality gates', () => {
    expect(VERIFIED_BENCHMARKS.length).toBeGreaterThanOrEqual(3);
    for (const bench of VERIFIED_BENCHMARKS) {
      expect(bench.quality.passed).toBe(true);
      expect(bench.quality.state).toBe('verified');
      expect(bench.provenance.transcriptVerified).toBe(true);
      expect(bench.provenance.contentSha256).toMatch(/^[a-f0-9]{64}$/);
      const expectedSha256 = createHash('sha256')
        .update(transcriptTextFromSegments(bench.segments), 'utf8')
        .digest('hex');
      expect(bench.provenance.contentSha256).toBe(expectedSha256);
      expect(bench.segments.length).toBeGreaterThan(0);
      expect(bench.linkedSop.entities.length).toBeGreaterThan(0);
      expect(bench.linkedSop.steps.length).toBeGreaterThan(0);
    }
  });

  it('compiles official vendor links and deterministic scaffold packages for each benchmark', () => {
    const primary = getBenchmarkByYoutubeId('auJzb1D-fag');
    expect(primary).toBeDefined();
    expect(primary!.linkedSop.entities.some((e) => e.name === 'Gemini')).toBe(true);
    expect(primary!.linkedSop.entities.some((e) => e.name === 'Vercel')).toBe(true);

    const pkg = buildScaffoldPackage({
      projectName: primary!.title,
      actions: [],
      linkedSop: primary!.linkedSop,
    });
    expect(pkg.files['README.md']).toContain('Named tools');
    expect(pkg.files['DEPLOY.md']).toContain('Vercel');
    expect(pkg.files['linked-sop.json']).toBeTruthy();
    expect(pkg.files['tasks.json']).toBeTruthy();
  });
});
