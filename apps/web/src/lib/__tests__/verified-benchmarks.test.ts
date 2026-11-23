import { createHash } from 'crypto';
import { describe, expect, it } from 'vitest';
import { FIXTURE_BENCHMARKS, getBenchmarkByYoutubeId } from '../verified-benchmarks';
import { buildScaffoldPackage } from '../action-surface';
import { assessAnalysisEvidence, transcriptTextFromSegments } from '../analysis-evidence';

describe('verified-benchmarks', () => {
  it('keeps static fixtures ineligible for live evidence acceptance', () => {
    expect(FIXTURE_BENCHMARKS.length).toBeGreaterThanOrEqual(3);
    for (const bench of FIXTURE_BENCHMARKS) {
      const reassessed = assessAnalysisEvidence(bench);
      expect(reassessed).toMatchObject({ passed: false, state: 'unavailable' });
      expect(bench.quality.passed).toBe(false);
      expect(bench.quality.state).toBe('unavailable');
      expect(bench.provenance.transcriptVerified).toBe(false);
      expect(bench.provenance.acquisitionMethod).toBe('static-fixture');
      expect(bench.provenance.transcriptSource).toBe('static-fixture');
      expect(bench.provenance.acquiredAt).toBe('');
      expect(bench.latencyMs).toBeNull();
      expect(bench.quality.issues).toContain('Static fixture; live provider acquisition has not been verified.');
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
