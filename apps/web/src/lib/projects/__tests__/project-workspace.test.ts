import { describe, expect, it } from 'vitest';
import type { EmittedVideoPack } from '@/lib/emit-video-pack';
import {
  buildProjectBrief,
  buildProjectFolders,
  filterTranscriptRows,
  formatProjectBriefMarkdown,
  formatTranscriptJson,
  parseProjectTime,
  parseProjectView,
  resolveProjectFolder,
  resolvePackTranscriptSegments,
} from '../project-workspace';

const HASH = '2778c5fc08a1b7f19fe0a83bca959e24ecf20040c3cc1a3b6edd244d68c5e4ea';
const project = {
  title: 'Test Video Pack',
  videoId: 'auJzb1D-fag',
  sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag',
  sourceHash: '',
};

function pack(over: Partial<EmittedVideoPack> = {}): EmittedVideoPack {
  return {
    version: 'v0',
    id: 'vp:v0:auJzb1D-fag',
    video_id: 'auJzb1D-fag',
    source_url: project.sourceUrl,
    provenance: { source_hash: HASH },
    transcript: {
      language: 'en',
      full_text: 'hello world',
      segments: [
        { idx: 0, start_s: 0, end_s: 10, text: 'Welcome to the build' },
        { idx: 1, start_s: 10, end_s: 25, text: 'Install Next.js first' },
        { idx: 2, start_s: 40, end_s: 50, text: 'Deploy to Vercel' },
      ],
    },
    chapters: [
      { start: 0, end: 20, topic: 'Setup', key_points: ['Install tooling'] },
      { start: 20, end: 60, topic: 'Deploy', key_points: [] },
    ],
    keyframes: [{ t_s: 5 }, { t_s: 20 }, { t_s: 60 }, { t_s: 90 }],
    events: [
      { id: 'e1', type: 'topic', title: 'Intro', timestamp: '0:10' },
      { id: 'e2', type: 'topic', title: 'Late', timestamp: '0:45' },
      { id: 'e3', type: 'topic', title: 'Untimed' },
    ],
    requirements: [{ id: 'r1', title: 'Req' }],
    action_items: [{ id: 'a1', title: 'Ship it', description: 'Deploy the app', priority: 'high' }],
    stack: { tools: [{ name: 'Next.js', kind: 'framework', evidence: 'said at 0:15' }, { name: 'Vercel' }] },
    architecture: { summary: 'A small deploy walkthrough.', stages: [] },
    ...over,
  } as EmittedVideoPack;
}

describe('workspace URL state', () => {
  it('defaults unknown views to brief and parses whole-second times', () => {
    expect(parseProjectView('run')).toBe('run');
    expect(parseProjectView('bogus')).toBe('brief');
    expect(parseProjectView(null)).toBe('brief');
    expect(parseProjectTime('90')).toBe(90);
    expect(parseProjectTime('-1')).toBeNull();
    expect(parseProjectTime('1.5')).toBeNull();
    expect(parseProjectTime('abc')).toBeNull();
    expect(parseProjectTime(null)).toBeNull();
  });
});

describe('buildProjectFolders', () => {
  it('returns only the all folder (zeroed) when there is no pack', () => {
    const folders = buildProjectFolders(null);
    expect(folders).toHaveLength(1);
    expect(folders[0]).toMatchObject({ id: 'all', assetCount: 0, keyframeCount: 0, eventCount: 0 });
  });

  it('counts real keyframes and events per chapter range without double counting boundaries', () => {
    const folders = buildProjectFolders(pack());
    expect(folders.map((f) => f.id)).toEqual(['all', 'ch-1', 'ch-2']);
    const [all, ch1, ch2] = folders;
    expect(all).toMatchObject({ keyframeCount: 4, eventCount: 3, taskCount: 2, assetCount: 9 });
    // t=20 belongs to CH2 (CH1 stops before the next chapter); t=60 is CH2's inclusive end.
    expect(ch1).toMatchObject({ label: 'CH1', topic: 'Setup', keyframeCount: 1, eventCount: 1, taskCount: null });
    expect(ch2).toMatchObject({ label: 'CH2', topic: 'Deploy', keyframeCount: 2, eventCount: 1, inclusiveEnd: true });
  });

  it('resolves unknown folder ids to the all folder', () => {
    const folders = buildProjectFolders(pack());
    expect(resolveProjectFolder(folders, 'ch-2').id).toBe('ch-2');
    expect(resolveProjectFolder(folders, 'nope').id).toBe('all');
    expect(resolveProjectFolder(folders, null).id).toBe('all');
  });
});

describe('transcript rows', () => {
  it('reads real pack segments with at least one second of duration', () => {
    const rows = resolvePackTranscriptSegments(pack());
    expect(rows).toHaveLength(3);
    expect(rows[1]).toEqual({ idx: 1, start: 10, duration: 15, text: 'Install Next.js first' });
  });

  it('never synthesizes timings from an identity stub or untimed text', () => {
    expect(resolvePackTranscriptSegments(null)).toEqual([]);
    expect(
      resolvePackTranscriptSegments(pack({ transcript: { full_text: 'cite:youtube:auJzb1D-fag', segments: [] } })),
    ).toEqual([]);
    expect(
      resolvePackTranscriptSegments(pack({ transcript: { full_text: 'just words with no times', segments: [] } })),
    ).toEqual([]);
  });

  it('falls back to timestamped full_text when segments are absent', () => {
    const rows = resolvePackTranscriptSegments(
      pack({ transcript: { full_text: '0:05 first line\n0:12 second line\n0:30 third line', segments: [] } }),
    );
    expect(rows.map((row) => [row.start, row.text])).toEqual([
      [5, 'first line'],
      [12, 'second line'],
      [30, 'third line'],
    ]);
  });

  it('filters by chapter folder and case-insensitive query', () => {
    const rows = resolvePackTranscriptSegments(pack());
    const folders = buildProjectFolders(pack());
    expect(filterTranscriptRows(rows, folders[0], '').length).toBe(3);
    expect(filterTranscriptRows(rows, folders[1], '').map((r) => r.text)).toEqual([
      'Welcome to the build',
      'Install Next.js first',
    ]);
    expect(filterTranscriptRows(rows, folders[2], '').map((r) => r.text)).toEqual(['Deploy to Vercel']);
    expect(filterTranscriptRows(rows, folders[0], 'NEXT.JS').map((r) => r.text)).toEqual(['Install Next.js first']);
    expect(filterTranscriptRows(rows, folders[1], 'vercel')).toEqual([]);
  });

  it('serializes rows as JSON with end times', () => {
    const json = JSON.parse(formatTranscriptJson(resolvePackTranscriptSegments(pack()).slice(0, 1), 'auJzb1D-fag'));
    expect(json).toEqual({ video_id: 'auJzb1D-fag', segments: [{ start_s: 0, end_s: 10, text: 'Welcome to the build' }] });
  });
});

describe('project brief', () => {
  it('is empty and honest without a pack', () => {
    const brief = buildProjectBrief(project, null);
    expect(brief).toMatchObject({
      hasPack: false,
      summary: null,
      chapters: [],
      stack: [],
      actionItems: [],
      openQuestions: [],
      captionSource: 'No captions available',
    });
  });

  it('is built only from real pack fields', () => {
    const brief = buildProjectBrief(project, pack());
    expect(brief).toMatchObject({
      hasPack: true,
      sourceHash: HASH,
      summary: 'A small deploy walkthrough.',
      captionSource: 'Timed captions',
    });
    expect(brief.chapters.map((c) => [c.number, c.topic])).toEqual([[1, 'Setup'], [2, 'Deploy']]);
    expect(brief.stack.map((t) => t.name)).toEqual(['Next.js', 'Vercel']);
    expect(brief.actionItems[0]).toMatchObject({ title: 'Ship it', priority: 'high' });
    expect(brief.openQuestions).toEqual(['No evidence was captured for Vercel.']);
  });

  it('flags missing chapters and timed captions as open questions', () => {
    const brief = buildProjectBrief(
      project,
      pack({ chapters: [], transcript: { full_text: 'plain untimed text', segments: [] }, stack: { tools: [] } }),
    );
    expect(brief.openQuestions).toEqual([
      'No chapters were extracted for this video.',
      'No timed captions are available, so timestamps cannot be verified.',
    ]);
    expect(brief.captionSource).toBe('ASR fallback');
  });

  it('renders deterministic Markdown', () => {
    const brief = buildProjectBrief(project, pack());
    const md = formatProjectBriefMarkdown(brief);
    expect(md).toBe(formatProjectBriefMarkdown(brief));
    expect(md).toContain('# Test Video Pack');
    expect(md).toContain(`- Source hash: ${HASH}`);
    expect(md).toContain('1. [0:00–0:20] Setup');
    expect(md).toContain('   - Install tooling');
    expect(md).toContain('- Next.js (framework — said at 0:15)');
    expect(md).toContain('- **Ship it** [high]: Deploy the app');
    expect(md).toContain('- No evidence was captured for Vercel.');
  });

  it('states empty sections explicitly instead of inventing content', () => {
    const md = formatProjectBriefMarkdown(buildProjectBrief(project, null));
    expect(md).toContain('_No summary was extracted._');
    expect(md).toContain('_No chapters were extracted._');
    expect(md).toContain('_No tools were detected._');
    expect(md).toContain('_No action items were extracted._');
    expect(md).toContain('_None recorded._');
  });
});
