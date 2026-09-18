// @vitest-environment jsdom
import React from 'react';
import { webcrypto } from 'node:crypto';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import GroundedSpecReview from '@/components/GroundedSpecReview';
import { browserSpecFixture, reviewPackFixture } from '@/test/grounded-spec-fixture';
import { hashReviewContent, type SpecReviewAcknowledgment } from '@/lib/grounded-build-spec';

vi.mock('@/lib/grounded-build-spec', async (original) => ({ ...await original<typeof import('@/lib/grounded-build-spec')>(), hashReviewContent: vi.fn() }));
let realHash: typeof hashReviewContent;
beforeEach(async () => {
  vi.stubGlobal('React', React);
  vi.stubGlobal('crypto', webcrypto);
  realHash = (await vi.importActual<typeof import('@/lib/grounded-build-spec')>('@/lib/grounded-build-spec')).hashReviewContent;
  vi.mocked(hashReviewContent).mockImplementation(realHash);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
const eligible = async () => {
  const button = screen.getByRole('button', { name: 'Acknowledge review' });
  await waitFor(() => expect(button.hasAttribute('disabled')).toBe(false));
  return button;
};

describe('inspect-only grounded specification review (synthetic)', () => {
  it('shows source-linked requirements, proposed checks and safe source navigation', async () => {
    const onSeek = vi.fn();
    render(<GroundedSpecReview videoId="a" pack={reviewPackFixture()} onAcknowledge={() => true} onSeek={onSeek} />);
    expect(screen.getByRole('heading', { name: 'Grounded specification' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Observed requirements' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Proposed acceptance criteria' })).toBeTruthy();
    expect(screen.getByText(/model-reported.*partial.*80%/i)).toBeTruthy();
    fireEvent.click(screen.getByText('Supporting source'));
    fireEvent.click(screen.getByRole('button', { name: 'Seek to 0:04' }));
    expect(onSeek).toHaveBeenCalledWith(4);
    expect(screen.getByRole('link', { name: 'Open source at 0:04' }).getAttribute('href')).toBe('https://www.youtube.com/watch?v=auJzb1D-fag&t=4s');
    await eligible();
  });
  it('acknowledges blockers without accepting proposals or causing network operations, supports reload and clear', async () => {
    const raw = browserSpecFixture();
    raw.grounded_spec.requirements.push({ ...raw.grounded_spec.requirements[0]!, id: 'proposal', classification: 'proposed', rationale: 'Not observed; a possible next step.', citations: [], capabilities: ['accounts'] });
    const pack = reviewPackFixture(raw);
    const save = vi.fn<(ack: SpecReviewAcknowledgment | undefined) => boolean>(() => true);
    const network = vi.fn(); vi.stubGlobal('fetch', network);
    const view = render(<GroundedSpecReview videoId="a" pack={pack} onAcknowledge={save} />);
    fireEvent.click(await eligible());
    expect(save).toHaveBeenCalledOnce();
    const ack = save.mock.calls[0]![0]!;
    expect(ack).toEqual({ version: '1', sourceHash: pack.provenance.source_hash, specHash: pack.grounded_spec?.status === 'available' ? pack.grounded_spec.contentHash : '', acknowledgedAt: expect.any(String) });
    view.rerender(<GroundedSpecReview videoId="a" pack={pack} acknowledgment={ack} onAcknowledge={save} />);
    expect(screen.getByText(/review acknowledged locally/i)).toBeTruthy();
    expect(screen.getByText(/outside browser-only scope: accounts/i)).toBeTruthy();
    expect(screen.getByText(/not.*authorization.*G.A.T.E./i)).toBeTruthy();
    view.unmount();
    render(<GroundedSpecReview videoId="a" pack={JSON.parse(JSON.stringify(pack))} acknowledgment={ack} onAcknowledge={save} />);
    await screen.findByRole('button', { name: 'Clear local acknowledgment' });
    fireEvent.click(screen.getByRole('button', { name: 'Clear local acknowledgment' }));
    expect(save).toHaveBeenLastCalledWith(undefined);
    expect(network).not.toHaveBeenCalled();
  });
  it.each(['legacy', 'invalid', 'none'] as const)('does not acknowledge a %s specification', (state) => {
    const pack = reviewPackFixture();
    if (state === 'legacy') delete pack.grounded_spec;
    if (state === 'invalid') Reflect.set(pack, 'grounded_spec', { status: 'available', spec: null });
    if (state === 'none') pack.grounded_spec = { status: 'source-unavailable', issues: [{ code: 'no-source', path: '', message: 'No usable source.', severity: 'blocking' }] };
    render(<GroundedSpecReview videoId="a" pack={pack} acknowledgment={{ corrupt: true }} onAcknowledge={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'Acknowledge review' })).toBeNull();
    expect(screen.getByTestId('grounded-spec-review').textContent).toMatch(/unavailable|invalid|usable source/i);
  });
  it('fails closed on digest mismatch and unavailable Web Crypto', async () => {
    const pack = reviewPackFixture();
    if (pack.grounded_spec?.status !== 'available') throw new Error('Missing test spec');
    pack.grounded_spec.spec.limitations.push('Tampered after digest');
    const view = render(<GroundedSpecReview videoId="a" pack={pack} onAcknowledge={vi.fn()} />);
    await screen.findByText(/content digest does not match/i);
    expect(screen.getByRole('button', { name: 'Acknowledge review' }).hasAttribute('disabled')).toBe(true);
    vi.mocked(hashReviewContent).mockRejectedValue(new Error('Unavailable'));
    view.rerender(<GroundedSpecReview videoId="b" pack={reviewPackFixture()} onAcknowledge={vi.fn()} />);
    await screen.findByText(/content verification unavailable/i);
  });
  it('labels failed persistence as session-only rather than saved', async () => {
    const save = vi.fn(() => false);
    render(<GroundedSpecReview videoId="a" pack={reviewPackFixture()} onAcknowledge={save} />);
    fireEvent.click(await eligible());
    expect(screen.getByText(/session-only.*not saved/i)).toBeTruthy();
  });
  it('ignores late digests and stale acknowledgment after selection changes', async () => {
    let resolve!: (hash: string) => void;
    vi.mocked(hashReviewContent).mockImplementationOnce(() => new Promise((done) => { resolve = done; }));
    const first = reviewPackFixture();
    const save = vi.fn(() => true);
    const view = render(<GroundedSpecReview videoId="a" pack={first} onAcknowledge={save} />);
    const next = reviewPackFixture();
    if (next.grounded_spec?.status !== 'available' || first.grounded_spec?.status !== 'available') throw new Error('Missing fixture');
    const stale = { version: '1', sourceHash: first.provenance.source_hash, specHash: first.grounded_spec.contentHash, acknowledgedAt: new Date().toISOString() };
    next.grounded_spec.spec.limitations.push('Changed content');
    view.rerender(<GroundedSpecReview videoId="b" pack={next} acknowledgment={stale} onAcknowledge={save} />);
    await act(async () => resolve(first.grounded_spec!.status === 'available' ? first.grounded_spec!.contentHash : ''));
    await screen.findByText(/content digest does not match/i);
    expect(screen.queryByText(/review acknowledged locally/i)).toBeNull();
    expect(screen.getByRole('button', { name: 'Acknowledge review' }).hasAttribute('disabled')).toBe(true);
    expect(save).not.toHaveBeenCalled();
  });
});
