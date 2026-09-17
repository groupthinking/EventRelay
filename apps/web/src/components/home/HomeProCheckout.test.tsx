/* @vitest-environment jsdom */
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import HomeProCheckout from './HomeProCheckout';

vi.mock('@/components/billing/ProCheckoutButton', () => ({
  default: ({ label }: { label: string }) => <button type="button">{label}</button>,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('HomeProCheckout', () => {
  it('groups billing cadence controls and updates the selected shared price', () => {
    render(<HomeProCheckout />);

    const cadence = screen.getByRole('group', { name: 'Billing cadence' });
    const monthly = screen.getByRole('button', { name: 'Monthly checkout' });
    const annual = screen.getByRole('button', { name: 'Annual checkout' });

    expect(cadence.contains(monthly)).toBe(true);
    expect(monthly.getAttribute('aria-pressed')).toBe('true');
    expect(annual.getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByTestId('home-workflow-pro-selected-price').textContent).toBe('$39/mo');

    fireEvent.click(annual);

    expect(monthly.getAttribute('aria-pressed')).toBe('false');
    expect(annual.getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('home-workflow-pro-selected-price').textContent).toBe('$390/yr');
    expect(
      screen.getByRole('button', { name: 'Continue to UVAI Workflow Pro $390/yr checkout' }),
    ).toBeTruthy();
  });
});
