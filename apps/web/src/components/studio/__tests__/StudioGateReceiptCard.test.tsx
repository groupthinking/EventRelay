// @vitest-environment jsdom
import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import StudioGateReceiptCard from '@/components/studio/StudioGateReceiptCard';
import { GATE_RECEIPT_VERSION, type StudioGateReceiptView } from '@/lib/gate-transition';

afterEach(() => {
  cleanup();
});

function view(
  decision: StudioGateReceiptView['decision'],
  overrides?: Partial<StudioGateReceiptView>,
): StudioGateReceiptView {
  return {
    decision,
    reason: `Plane stays proposed for auJzb1D-fag (${decision}).`,
    reason_code: `GATE_${decision}`,
    receiptId: 'er:gate:v1:fixture',
    receiptHash: 'b'.repeat(64),
    version: GATE_RECEIPT_VERSION,
    transitionId: 'attempt:auJzb1D-fag',
    retained: false,
    ...overrides,
  };
}

describe('StudioGateReceiptCard (Cut 5)', () => {
  it('shows https live link only on PASS', () => {
    render(
      <StudioGateReceiptCard
        receipt={view('PASS', { version: 'eventrelay.gate-receipt.v2', retained: true })}
        liveUrl="https://demo.vercel.app"
      />,
    );
    expect(screen.getByTestId('studio-gate-decision').textContent).toBe('PASS');
    const link = screen.getByTestId('studio-gate-live-url');
    expect(link.getAttribute('href')).toBe('https://demo.vercel.app');
    expect(link.textContent).toBe('https://demo.vercel.app');
  });

  it.each(['HOLD', 'REJECT', 'ESCALATE'] as const)(
    'does not render a live URL or live claim for %s',
    (decision) => {
      render(
        <StudioGateReceiptCard receipt={view(decision)} liveUrl="https://demo.vercel.app" />,
      );
      expect(screen.getByTestId('studio-gate-decision').textContent).toBe(decision);
      expect(screen.queryByTestId('studio-gate-live-url')).toBeNull();
      expect(screen.getByTestId('studio-gate-reason').textContent).not.toMatch(/\blive\b/i);
    },
  );

  it('exposes receipt id, hash, and transition for the fixture path', () => {
    render(<StudioGateReceiptCard receipt={view('HOLD')} />);
    expect(screen.getByTestId('studio-gate-receipt-id').textContent).toBe('er:gate:v1:fixture');
    expect(screen.getByTestId('studio-gate-receipt-hash').textContent).toBe('b'.repeat(64));
    expect(screen.getByText(/Transition: attempt:auJzb1D-fag/)).toBeTruthy();
  });
});
