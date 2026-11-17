// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Nav from '@/components/Nav';

const usePathnameMock = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: () => usePathnameMock(),
}));

afterEach(() => {
  cleanup();
  delete document.documentElement.dataset.theme;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal('React', React);
  usePathnameMock.mockReset();
});

describe('Nav template routing semantics', () => {
  it('marks Pricing as current on desktop and in expanded mobile menu', () => {
    usePathnameMock.mockReturnValue('/pricing');
    render(<Nav />);

    const desktopPricing = screen.getByRole('link', { name: 'Pricing' });
    expect(desktopPricing.getAttribute('aria-current')).toBe('page');

    fireEvent.click(screen.getByRole('button', { name: /open navigation menu/i }));
    const mobileNav = screen.getAllByRole('link', { name: 'Pricing' }).at(-1);
    expect(mobileNav?.getAttribute('aria-current')).toBe('page');
  });

  it('marks Home as current when pathname is root', () => {
    usePathnameMock.mockReturnValue('/');
    render(<Nav />);
    expect(screen.getAllByRole('link', { name: 'Home' })[0]?.getAttribute('aria-current')).toBe('page');
  });

  it('toggles document theme between dark default and light mode', () => {
    usePathnameMock.mockReturnValue('/');
    render(<Nav />);

    const toLight = screen.getByRole('button', { name: 'Switch to light mode' });
    fireEvent.click(toLight);
    expect(document.documentElement.dataset.theme).toBe('light');

    const toDark = screen.getByRole('button', { name: 'Switch to dark mode' });
    fireEvent.click(toDark);
    expect(document.documentElement.dataset.theme).toBe('dark');
  });
});
