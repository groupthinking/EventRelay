import { describe, expect, it } from 'vitest';
import { loadSamplePack } from '@/lib/sample-pack';
import {
  applyTaskEdits,
  buildDispatchRequest,
  deriveLiveTasks,
  formatTimestamp,
  inferOwner,
  nearestKeyframe,
  normalizeTaskEdit,
  sourceWatchUrl,
} from '@/lib/live-studio-tasks';

const { pack } = loadSamplePack();
const tasks = deriveLiveTasks(pack);

describe('deriveLiveTasks', () => {
  it('returns nothing without a pack', () => {
    expect(deriveLiveTasks(undefined)).toEqual([]);
  });

  it('lists cited grounded-spec requirements first, then chapter-matched action items', () => {
    expect(tasks.map((task) => task.id)).toEqual(['G-REQ-01', 'G-REQ-02', 'G-REQ-03', 'ACT-01', 'ACT-02', 'ACT-03']);
    for (const task of tasks.slice(0, 3)) {
      expect(task.origin).toBe('grounded-spec');
      expect(task.source?.basis).toBe('cited');
      expect(task.source?.label).toMatch(/^Transcript #\d+$/);
      expect(task.check).toMatch(/^Given .+, when .+, then .+\.$/m);
    }
    for (const task of tasks.slice(3)) {
      expect(task.origin).toBe('action-item');
      expect(task.source?.basis).toBe('chapter-match');
      expect(task.source?.quote).toBeNull();
    }
  });

  it('links every task to a source timestamp and the nearest keyframe', () => {
    for (const task of tasks) {
      expect(task.source).not.toBeNull();
      expect(task.keyframe?.t_s).toBe(nearestKeyframe(pack.keyframes, task.source!.startSeconds)?.t_s);
    }
  });

  it('takes an action item check from a named stack tool when one is mentioned', () => {
    const act01 = tasks.find((task) => task.id === 'ACT-01');
    const tool = pack.stack?.tools.find((item) => item.name === 'Google AI Studio');
    expect(tool?.check).toBeTruthy();
    expect(act01?.check).toBe(tool?.check);
  });
});

describe('task edits', () => {
  const base = tasks[0];

  it('stores only changed fields and keeps the derived title when cleared', () => {
    expect(normalizeTaskEdit(base, { title: base.title, spec: base.spec, check: base.check, owner: base.owner })).toBeNull();
    expect(normalizeTaskEdit(base, { title: '   ', owner: 'qa' })).toEqual(base.owner === 'qa' ? null : { owner: 'qa' });
    expect(normalizeTaskEdit(base, { title: ' New title ', spec: base.spec })).toEqual({ title: 'New title' });
  });

  it('applies edits on top of derived tasks and marks them edited', () => {
    const edited = applyTaskEdits(tasks, { [base.id]: { title: 'Renamed', owner: 'qa' } });
    expect(edited[0]).toMatchObject({ title: 'Renamed', owner: 'qa', edited: true, spec: base.spec });
    expect(edited[1]).toBe(tasks[1]);
    expect(applyTaskEdits(tasks, undefined)).toEqual(tasks);
  });
});

describe('buildDispatchRequest', () => {
  it('maps tasks into the /api/agents/dispatch body with source links', () => {
    const chosen = [tasks[0], tasks[3]];
    const request = buildDispatchRequest({ tasks: chosen, videoId: pack.video_id, jobId: 'job-1', transcript: 'text' });
    expect(request.job_id).toBe('job-1');
    expect(request.transcript).toBe('text');
    expect(request.events).toHaveLength(2);
    expect(request.events[0]).toMatchObject({
      id: tasks[0].id,
      type: 'action',
      title: tasks[0].title,
      owner_agent: tasks[0].owner,
      timestamp: formatTimestamp(tasks[0].source!.startSeconds),
      timestamp_basis: 'cited',
      source_url: sourceWatchUrl(pack.video_id, tasks[0].source!.startSeconds),
    });
    expect(request.events[0].description).toContain(`Check: ${tasks[0].check}`);
    expect(request.agent_types).toEqual([...new Set(chosen.map((task) => task.owner))]);
  });

  it('omits job_id when no job is known', () => {
    expect(buildDispatchRequest({ tasks: [tasks[0]], videoId: null })).not.toHaveProperty('job_id');
  });
});

describe('helpers', () => {
  it('formats timestamps and routes owners', () => {
    expect(formatTimestamp(0)).toBe('0:00');
    expect(formatTimestamp(344)).toBe('5:44');
    expect(formatTimestamp(3725)).toBe('1:02:05');
    expect(inferOwner('anything', 'explore')).toBe('researcher');
    expect(inferOwner('anything', 'test')).toBe('qa');
    expect(sourceWatchUrl('auJzb1D-fag', 344.7)).toBe('https://www.youtube.com/watch?v=auJzb1D-fag&t=344s');
  });
});
