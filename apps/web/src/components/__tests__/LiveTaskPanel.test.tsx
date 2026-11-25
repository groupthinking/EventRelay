// @vitest-environment jsdom
import React, { useState } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LiveTaskPanel from '@/components/studio/live/LiveTaskPanel';
import { loadSamplePack } from '@/lib/sample-pack';
import { applyTaskEdits, deriveLiveTasks, type LiveTaskEdits } from '@/lib/live-studio-tasks';

const { pack } = loadSamplePack();
const baseTasks = deriveLiveTasks(pack);

function Harness({ onSeek = vi.fn(), onSave = vi.fn() }: { onSeek?: (seconds: number) => void; onSave?: (edits: LiveTaskEdits) => void }) {
  const [edits, setEdits] = useState<LiveTaskEdits | undefined>(undefined);
  return (
    <LiveTaskPanel
      tasks={applyTaskEdits(baseTasks, edits)}
      baseTasks={baseTasks}
      live={false}
      canSeek
      videoId={pack.video_id}
      jobId="job-1"
      transcript={pack.transcript?.full_text}
      onSeek={onSeek}
      edits={edits}
      onSaveEdits={(next) => {
        onSave(next);
        setEdits(next);
      }}
    />
  );
}

type Route = (url: string, init?: RequestInit) => Response | Promise<Response>;

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function stubFetch(route: Route) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => Promise.resolve(route(String(input), init)));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener() {}, removeEventListener() {} }));
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('LiveTaskPanel task edit', () => {
  it('edits title, check and owner inline and persists only changed fields', async () => {
    stubFetch(() => json(200, { available: false }));
    const onSave = vi.fn();
    render(<Harness onSave={onSave} />);

    fireEvent.click(await screen.findByTestId('live-task-G-REQ-01-open'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Attach a video and show its token count' } });
    fireEvent.change(screen.getByLabelText('Check'), { target: { value: 'Token count badge is visible.' } });
    fireEvent.change(screen.getByLabelText('Owner agent'), { target: { value: 'qa' } });
    fireEvent.click(screen.getByTestId('live-task-G-REQ-01-save'));

    expect(onSave).toHaveBeenLastCalledWith({
      'G-REQ-01': { title: 'Attach a video and show its token count', check: 'Token count badge is visible.', owner: 'qa' },
    });
    const card = screen.getByTestId('live-task-G-REQ-01');
    expect(card.textContent).toContain('Attach a video and show its token count');
    expect(card.textContent).toContain('Edited');
    expect(screen.getByTestId('live-task-G-REQ-01-owner').textContent).toBe('QA agent');
    expect(screen.getByTestId('live-task-G-REQ-01-check').textContent).toContain('Token count badge is visible.');
  });

  it('resets an edited task back to its source-derived values', async () => {
    stubFetch(() => json(200, { available: false }));
    const onSave = vi.fn();
    render(<Harness onSave={onSave} />);
    fireEvent.click(await screen.findByTestId('live-task-ACT-01-open'));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Renamed' } });
    fireEvent.click(screen.getByTestId('live-task-ACT-01-save'));
    fireEvent.click(screen.getByTestId('live-task-ACT-01-open'));
    fireEvent.click(screen.getByTestId('live-task-ACT-01-reset'));
    expect(onSave).toHaveBeenLastCalledWith({});
    expect(screen.getByTestId('live-task-ACT-01').textContent).toContain(baseTasks[3].title);
    expect(screen.getByTestId('live-task-ACT-01').textContent).not.toContain('Edited');
  });

  it('seeks the player from a task timestamp and keyframe', async () => {
    stubFetch(() => json(200, { available: false }));
    const onSeek = vi.fn();
    render(<Harness onSeek={onSeek} />);
    fireEvent.click(await screen.findByTestId('live-task-G-REQ-01-timestamp'));
    expect(onSeek).toHaveBeenLastCalledWith(baseTasks[0].source?.startSeconds);
    fireEvent.click(screen.getByTestId('live-task-G-REQ-01-keyframe'));
    expect(onSeek).toHaveBeenLastCalledWith(baseTasks[0].keyframe?.t_s);
  });
});

describe('LiveTaskPanel dispatch', () => {
  it('streams queued then FAILED with an upgrade link when dispatch needs Pro', async () => {
    const fetchMock = stubFetch((url, init) =>
      init?.method === 'POST'
        ? json(402, { error: 'Agent dispatch is a Pro feature. Upgrade at /pricing.', upgradeRequired: true })
        : json(200, { available: true }),
    );
    render(<Harness />);
    fireEvent.click(await screen.findByTestId('live-task-G-REQ-01-select'));
    fireEvent.click(screen.getByTestId('live-dispatch-button'));

    await screen.findByTestId('live-dispatch-upgrade');
    const lines = [...screen.getByTestId('live-run-log').querySelectorAll('li')].map((li) => li.getAttribute('data-status'));
    expect(lines).toEqual(['queued', 'failed']);
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
    const body = JSON.parse(String(post?.[1]?.body)) as { job_id: string; events: Array<{ id: string }> };
    expect(body.job_id).toBe('job-1');
    expect(body.events.map((event) => event.id)).toEqual(['G-REQ-01']);
  });

  it('streams queued, running and done lines from dispatch and status polling', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let polls = 0;
    stubFetch((url, init) => {
      if (init?.method === 'POST') {
        return json(200, {
          dispatch_id: 'dsp-1',
          executions: [
            { agent_id: 'a-1', agent_type: 'builder', status: 'running', progress: 10, event_id: 'G-REQ-01' },
            { agent_id: 'a-2', agent_type: 'researcher', status: 'queued', progress: 0, event_id: 'ACT-01' },
          ],
        });
      }
      if (url.startsWith('/api/agents/status')) {
        polls += 1;
        const agentId = new URL(url, 'http://localhost').searchParams.get('agentId');
        return json(200, {
          agent_id: agentId,
          agent_type: agentId === 'a-1' ? 'builder' : 'researcher',
          status: agentId === 'a-1' ? 'complete' : 'failed',
          progress: 100,
          ...(agentId === 'a-2' ? { error: 'tool unavailable' } : {}),
        });
      }
      return json(200, { available: true });
    });
    render(<Harness />);
    fireEvent.click(await screen.findByTestId('live-task-G-REQ-01-select'));
    fireEvent.click(screen.getByTestId('live-task-ACT-01-select'));
    expect(screen.getByTestId('live-dispatch-button').textContent).toContain('Dispatch 2 tasks');
    fireEvent.click(screen.getByTestId('live-dispatch-button'));

    await waitFor(() => expect(screen.getByTestId('live-run-log').textContent).toContain('dsp-1'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_100);
    });
    await waitFor(() => expect(polls).toBe(2));
    await waitFor(() => {
      const statuses = [...screen.getByTestId('live-run-log').querySelectorAll('li')].map((li) => li.getAttribute('data-status'));
      expect(statuses).toEqual(['queued', 'queued', 'running', 'running', 'queued', 'done', 'failed']);
    });
    expect(screen.getByTestId('live-run-log').textContent).toContain('tool unavailable');
    expect(screen.queryByTestId('live-dispatch-upgrade')).toBeNull();
  });
});
