// @vitest-environment jsdom
import React from 'react';
import { webcrypto } from 'node:crypto';
import { Blob as NodeBlob } from 'node:buffer';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StudioBoundTasks from '@/components/studio/StudioBoundTasks';
import { reviewPackFixture } from '@/test/grounded-spec-fixture';

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.stubGlobal('crypto', webcrypto);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

async function exportButton() {
  const button = await screen.findByRole('button', { name: /export tasks/i });
  await waitFor(() => expect(button.hasAttribute('disabled')).toBe(false));
  return button;
}

describe('source-bound tasks (synthetic contract fixtures, not video evidence)', () => {
  it('binds a requirement to its source and proposed check without claiming execution', async () => {
    render(<StudioBoundTasks pack={reviewPackFixture()} />);

    expect(await screen.findByText('Mark a task complete')).toBeTruthy();
    expect(screen.getByText('Toggle the task checkbox.')).toBeTruthy();
    expect(screen.getByText('Select a task to mark it complete.')).toBeTruthy();
    const source = screen.getAllByRole('link').find((link) =>
      link.getAttribute('href') === 'https://www.youtube.com/watch?v=auJzb1D-fag&t=4s');
    expect(source).toBeTruthy();
    expect(source?.getAttribute('rel')).toContain('noopener');
    expect(screen.getByText('An unchecked task')).toBeTruthy();
    expect(screen.getByText('Select its checkbox')).toBeTruthy();
    expect(screen.getByText('The task is visibly checked.')).toBeTruthy();
    expect(screen.getAllByText(/not run/i).length).toBeGreaterThan(0);
    await exportButton();
  });

  it.each(['legacy', 'invalid', 'source-unavailable', 'wrong-source'] as const)(
    'does not fabricate tasks from a %s pack', (state) => {
      const pack = reviewPackFixture();
      if (state === 'legacy') delete pack.grounded_spec;
      if (state === 'invalid') Reflect.set(pack, 'grounded_spec', { status: 'available', spec: null });
      if (state === 'source-unavailable') pack.grounded_spec = {
        status: 'source-unavailable',
        issues: [{ code: 'no-source', path: '', message: 'No usable source.', severity: 'blocking' }],
      };
      if (state === 'wrong-source') pack.video_id = 'jNQXAC9IVRw';
      render(<StudioBoundTasks pack={pack} />);
      expect(screen.queryByText('Mark a task complete')).toBeNull();
      const button = screen.queryByRole('button', { name: /export tasks/i });
      expect(button === null || button.hasAttribute('disabled')).toBe(true);
    },
  );

  it('prevents exporting a task set after its bound content changes', async () => {
    const pack = reviewPackFixture();
    if (pack.grounded_spec?.status !== 'available') throw new Error('Missing test specification');
    pack.grounded_spec.spec.requirements[0]!.detail = 'Changed after the original content was hashed.';
    render(<StudioBoundTasks pack={pack} />);
    await screen.findByText(/digest.*match|content.*changed|content.*mismatch/i);
    const button = screen.queryByRole('button', { name: /export tasks/i });
    expect(button === null || button.hasAttribute('disabled')).toBe(true);
  });

  it('holds tasks when content hashing is unavailable', async () => {
    vi.stubGlobal('crypto', { subtle: { digest: vi.fn().mockRejectedValue(new Error('Unavailable')) } });
    render(<StudioBoundTasks pack={reviewPackFixture()} />);
    await screen.findByText(/content verification is unavailable/i);
    expect(screen.queryByText('Mark a task complete')).toBeNull();
    expect(screen.queryByRole('button', { name: /export tasks/i })).toBeNull();
  });

  it('does not reuse a previous digest when the selected pack changes', async () => {
    const view = render(<StudioBoundTasks pack={reviewPackFixture()} />);
    await exportButton();
    const next = reviewPackFixture();
    if (next.grounded_spec?.status !== 'available') throw new Error('Missing test specification');
    next.grounded_spec.spec.requirements[0]!.detail = 'A new, unverified selection.';
    view.rerender(<StudioBoundTasks pack={next} />);
    expect(screen.queryByRole('button', { name: /export tasks/i })).toBeNull();
    expect(screen.queryByText('Mark a task complete')).toBeNull();
    await screen.findByText(/content digest does not match/i);
  });

  it('exports the bound identity and unexecuted checks, then releases the download URL', async () => {
    const createObjectURL = vi.fn<(blob: Blob) => string>(() => 'blob:synthetic-task-export');
    const revokeObjectURL = vi.fn();
    const BrowserURL = URL;
    vi.stubGlobal('URL', class extends BrowserURL {
      static createObjectURL = createObjectURL;
      static revokeObjectURL = revokeObjectURL;
    });
    vi.stubGlobal('Blob', NodeBlob);
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const network = vi.fn();
    vi.stubGlobal('fetch', network);
    const pack = reviewPackFixture();
    render(<StudioBoundTasks pack={pack} />);
    fireEvent.click(await exportButton());
    expect(createObjectURL).toHaveBeenCalledOnce();
    const exported = createObjectURL.mock.calls[0]![0] as unknown as NodeBlob;
    const data = JSON.parse(await exported.text());
    expect(data.source.packId).toBe(pack.id);
    expect(data.source.sourceHash).toBe(pack.provenance.source_hash);
    expect(data.tasks[0]).toMatchObject({
      id: 'toggle', executionStatus: 'not_run', outputStatus: 'not_generated', verificationStatus: 'unverified',
    });
    expect(data.tasks[0].checks[0]).toMatchObject({ id: 'toggle-check', requirementId: 'toggle', status: 'not_run' });
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:synthetic-task-export'), { timeout: 2000 });
    expect(network).not.toHaveBeenCalled();
  });
});
