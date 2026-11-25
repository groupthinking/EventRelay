// @vitest-environment jsdom
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cleanup, render, screen } from '@testing-library/react';
import { SessionProvider } from 'next-auth/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { StudioAuthNavLink } from '@/components/StudioAuthNavLink';

const useSession = vi.fn();

vi.mock('next-auth/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('next-auth/react')>();
  return {
    ...actual,
    useSession: () => useSession(),
    signOut: vi.fn(),
  };
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('StudioAuthNavLink', () => {
  it('shows Sign in when there is no session', () => {
    useSession.mockReturnValue({ data: null, status: 'unauthenticated' });
    render(
      <SessionProvider session={null}>
        <StudioAuthNavLink />
      </SessionProvider>,
    );
    const link = screen.getByRole('link', { name: 'Sign in' });
    expect(link.getAttribute('href')).toBe('/login?callbackUrl=%2Fstudio');
  });

  it('shows the signed-in identity instead of Sign in', () => {
    useSession.mockReturnValue({
      data: { user: { email: 'garveyht@gmail.com', name: 'Hayden Garvey' } },
      status: 'authenticated',
    });
    render(
      <SessionProvider session={null}>
        <StudioAuthNavLink />
      </SessionProvider>,
    );
    expect(screen.queryByRole('link', { name: 'Sign in' })).toBeNull();
    expect(screen.getByText('garveyht@gmail.com')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeTruthy();
  });

  it('defines --card-accent on :root so primary nav buttons stay visible outside .uvai-cards', () => {
    const here = dirname(fileURLToPath(import.meta.url));
    const css = readFileSync(join(here, '../../styles/studio-cards.css'), 'utf8');
    expect(css).toMatch(/:root,\s*\n?\.uvai-cards\s*\{[\s\S]*--card-accent:\s*var\(--uvai-accent\)/);
  });
});
