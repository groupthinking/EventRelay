// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OneLoopStudio from '@/components/OneLoopStudio';
import { useDashboardStore, type Video } from '@/store/dashboard-store';
import { startStudioDeploy } from '@/lib/studio-workflow';

vi.mock('next/navigation', () => ({ useSearchParams: () => new URLSearchParams() }));
vi.mock('@/components/Nav', () => ({ default: () => null }));
vi.mock('@/app/studio/actions', () => ({ openGitHubPrsForApprovedSpecs: vi.fn() }));
vi.mock('@/lib/use-youtube-player', () => ({ useYouTubePlayer: () => ({ containerRef: { current: null }, ready: false, failed: false, seekTo: vi.fn() }) }));
vi.mock('@/lib/studio-workflow', async (importOriginal) => ({ ...await importOriginal<typeof import('@/lib/studio-workflow')>(), startStudioDeploy: vi.fn() }));

const gate: NonNullable<Awaited<ReturnType<typeof startStudioDeploy>>['gate']> = { decision: 'HOLD', reason: 'Signed artifact evidence is required.', reason_code: 'GATE_HOLD_MISSING_EVIDENCE', receiptId: 'er:gate:v2:test', receiptHash: 'a'.repeat(64), version: 'eventrelay.gate-receipt.v2', transitionId: 'transition-test', retained: false };
const video: Video = { id: 'selected-a', title: 'Gate fixture', url: 'https://www.youtube.com/watch?v=auJzb1D-fag', status: 'complete', progress: 100, transcript: 'Review the observed requirements and gather verified evidence before authorizing a transition.' };

beforeEach(() => {
  vi.stubGlobal('React', React);
  vi.spyOn(useDashboardStore.persist, 'rehydrate').mockImplementation(() => undefined);
  useDashboardStore.setState({ videos: [video, { ...video, id: 'selected-b' }], selectedVideoId: video.id });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('Studio authoritative gate receipt', () => {
  it('reopens a stored pack without running analysis or gate actions', async () => {
    const { reviewPackFixture } = await import('@/test/grounded-spec-fixture');
    const pack = reviewPackFixture();
    useDashboardStore.setState({ videos: [{ ...video, status: 'failed', videoPack: { packId: pack.id, sourceHash: pack.provenance.source_hash, version: pack.version, pack } }], selectedVideoId: null });
    const process = vi.spyOn(useDashboardStore.getState(), 'processVideo');
    const deployCalls = vi.mocked(startStudioDeploy).mock.calls.length;
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Stored packs' }), { target: { value: video.id } });
    expect(screen.getByTestId('grounded-spec-review')).toBeTruthy();
    expect(screen.getByText('Task checklist')).toBeTruthy();
    expect(process).not.toHaveBeenCalled();
    expect(vi.mocked(startStudioDeploy).mock.calls.length).toBe(deployCalls);
  });

  it.each(['PASS', 'HOLD', 'REJECT', 'ESCALATE'] as const)('displays server %s without inventing deployment links or execution', async (decision) => {
    const receipt = { ...gate, decision, retained: true, reason: `${decision}: isolated server decision.`, reason_code: `GATE_${decision}` };
    vi.mocked(startStudioDeploy).mockResolvedValue({ ok: false, status: decision === 'PASS' ? 200 : 409, gate: receipt });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.click(screen.getByTestId('studio-deploy-button'));
    await screen.findByTestId('studio-gate-receipt');
    expect(screen.getByTestId('studio-gate-decision').textContent).toBe(decision);
    expect(screen.getByTestId('studio-gate-reason').textContent).toBe(receipt.reason);
    expect(screen.getByTestId('studio-gate-receipt-id').textContent).toBe(receipt.receiptId);
    expect(screen.getByTestId('studio-gate-receipt-hash').textContent).toBe(receipt.receiptHash);
    expect(screen.getByText(/Transition: transition-test.*Receipt retained/)).toBeTruthy();
    expect(screen.getByText('Server decision. Later stages require separate Loop approval.')).toBeTruthy();
    expect(screen.queryByTestId('studio-gate-live-url')).toBeNull();
    expect(screen.queryByText(/deploy live|deployment succeeded|deploy completed/i)).toBeNull();
    expect(screen.getByRole('button', { name: 'Check preflight' }).hasAttribute('disabled')).toBe(false);
  });

  it('labels a missing server receipt as a local diagnostic, never retained authorization', async () => {
    vi.mocked(startStudioDeploy).mockResolvedValue({ ok: false, status: 503, error: 'Offline runtime unavailable.' });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.click(screen.getByTestId('studio-deploy-button'));
    const receipt = await screen.findByTestId('studio-gate-receipt');
    expect(receipt.textContent).toContain('Local diagnostic only — not an authorization receipt.');
    expect(receipt.textContent).toContain('eventrelay.gate-receipt.v1');
    expect(receipt.textContent).not.toContain('Receipt retained');
    expect(receipt.textContent).not.toContain('Server decision.');
    expect(screen.queryByTestId('studio-gate-live-url')).toBeNull();
  });
  it('labels idle and pending actions as preflight only, with deployment unavailable', async () => {
    let finish!: (result: Awaited<ReturnType<typeof startStudioDeploy>>) => void;
    vi.mocked(startStudioDeploy).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    const button = screen.getByRole('button', { name: 'Check preflight' });
    expect(screen.getByText(/preflight only.*deployment is unavailable/i)).toBeTruthy();
    expect(button.getAttribute('aria-describedby')).toBe('studio-preflight-hint');
    fireEvent.click(button);
    expect(screen.getByRole('button', { name: 'Checking preflight…' }).hasAttribute('disabled')).toBe(true);
    await act(async () => finish({ ok: false, status: 409, gate }));
    expect(screen.getByRole('button', { name: 'Check preflight' })).toBeTruthy();
    expect(screen.queryByText(/attempting deploy|attempt deploy/i)).toBeNull();
  });

  it('displays a server HOLD as runtime evidence, not a deployment', async () => {
    vi.mocked(startStudioDeploy).mockResolvedValue({ ok: false, status: 409, gate });
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.click(screen.getByTestId('studio-deploy-button'));
    const receipt = await screen.findByTestId('studio-gate-receipt');
    expect(receipt.textContent).toContain('HOLD');
    expect(receipt.textContent).toContain(gate.receiptId);
    expect(receipt.textContent).toContain('Transition: transition-test');
    expect(receipt.textContent).toContain('Receipt not retained');
    expect(receipt.textContent).toContain('Server decision. Later stages require separate Loop approval.');
    expect(screen.queryByRole('link', { name: /live/i })).toBeNull();
    act(() => useDashboardStore.getState().selectVideo('selected-b'));
    expect(screen.queryByTestId('studio-gate-receipt')).toBeNull();
  });

  it('ignores a late receipt when another video is selected', async () => {
    let finish!: (result: Awaited<ReturnType<typeof startStudioDeploy>>) => void;
    vi.mocked(startStudioDeploy).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    render(<OneLoopStudio showAgentWorkflowUi={false} />);
    fireEvent.click(screen.getByTestId('studio-deploy-button'));
    act(() => useDashboardStore.getState().selectVideo('selected-b'));
    await act(async () => finish({ ok: false, status: 409, gate }));
    expect(screen.queryByTestId('studio-gate-receipt')).toBeNull();
  });
});
