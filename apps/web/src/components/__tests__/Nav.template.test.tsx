// @vitest-environment jsdom
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Nav from '@/components/Nav';

const here = dirname(fileURLToPath(import.meta.url));

const usePathnameMock = vi.fn();

vi.mock('next/navigation', () => ({
  usePathname: () => usePathnameMock(),
}));

afterEach(() => {
  cleanup();
  delete document.documentElement.dataset.theme;
  delete document.documentElement.dataset.contrast;
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

  it('keeps light-mode state when Nav remounts on another route', () => {
    usePathnameMock.mockReturnValue('/');
    const first = render(<Nav />);
    fireEvent.click(screen.getByRole('button', { name: 'Switch to light mode' }));
    expect(document.documentElement.dataset.theme).toBe('light');
    first.unmount();

    usePathnameMock.mockReturnValue('/studio');
    render(<Nav />);
    const toggle = screen.getByRole('button', { name: 'Switch to dark mode' });
    fireEvent.click(toggle);
    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('toggles data-contrast between high and normal without touching theme', () => {
    usePathnameMock.mockReturnValue('/');
    render(<Nav />);

    const contrast = screen.getByRole('button', { name: 'High Contrast' });
    expect(contrast.getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(contrast);
    expect(document.documentElement.dataset.contrast).toBe('high');
    expect(contrast.getAttribute('aria-pressed')).toBe('true');
    expect(document.documentElement.dataset.theme).toBeUndefined();

    fireEvent.click(contrast);
    expect(document.documentElement.dataset.contrast).toBe('normal');
    expect(contrast.getAttribute('aria-pressed')).toBe('false');
  });

  it('supports Webflow floating rail defaultCollapsed with visible brand mark and ⌘/ toggle', () => {
    usePathnameMock.mockReturnValue('/studio');
    render(<Nav variant="rail" defaultCollapsed />);

    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(nav.dataset.collapsed).toBe('true');
    expect(screen.getByRole('link', { name: 'UVAI Home' }).getAttribute('href')).toBe('/');

    const expand = screen.getByRole('button', { name: 'Expand sidebar' });
    expect(expand.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(expand);
    expect(nav.dataset.collapsed).toBe('false');
    expect(screen.getByRole('button', { name: 'Collapse sidebar' }).getAttribute('aria-expanded')).toBe('true');

    fireEvent.keyDown(window, { key: '/', metaKey: true });
    expect(nav.dataset.collapsed).toBe('true');
  });

  it('keeps primary topbar links visible down to 600px and mobile drawer below 600px', () => {
    usePathnameMock.mockReturnValue('/');
    render(<Nav />);

    const homeLink = screen.getByRole('link', { name: 'Home' });
    const linksWrap = homeLink.parentElement;
    expect(linksWrap?.className).toContain('min-[600px]:flex');
    expect(linksWrap?.className).not.toContain('md:flex');
    expect(homeLink.className).toContain('whitespace-nowrap');

    const menuButton = screen.getByRole('button', { name: 'Open navigation menu' });
    expect(menuButton.className).toContain('min-[600px]:hidden');
  });

  it('keeps an accessible Sign in / account trigger in collapsed rail footer and expands to reveal rightSlot', () => {
    usePathnameMock.mockReturnValue('/studio');
    render(<Nav variant="rail" defaultCollapsed rightSlot={<a href="/login">Sign in</a>} />);

    const nav = screen.getByRole('navigation', { name: 'Primary' });
    expect(nav.dataset.collapsed).toBe('true');

    const collapsedAccount = screen.getByRole('button', { name: 'Sign in or account' });
    expect(collapsedAccount.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(collapsedAccount);

    expect(nav.dataset.collapsed).toBe('false');
    expect(screen.queryByRole('button', { name: 'Sign in or account' })).toBeNull();
    expect(screen.getByRole('link', { name: 'Sign in' }).getAttribute('href')).toBe('/login');
  });

  it('defines topbar height token and keeps rail labels and CTA accessible across breakpoints', () => {
    const css = readFileSync(join(here, '../../styles/theme-tokens.css'), 'utf8');
    expect(css).toContain('--uvai-topbar-h: 64px;');
    expect(css).toContain('--uvai-topbar-h: 56px;');
    expect(css).toContain('.uvai-rail-shell[data-collapsed=\'true\'] .uvai-rail-collapsed-cta');
    expect(css).toContain('.uvai-rail-shell[data-collapsed=\'true\'] .uvai-rail-brand-text');
    expect(css).toContain('.uvai-rail-shell[data-collapsed=\'true\'] .uvai-rail-links .uvai-rail-label');
    expect(css).toContain('.uvai-rail-shell[data-collapsed=\'true\'] .uvai-rail-cta');
  });
});
