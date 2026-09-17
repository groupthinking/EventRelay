// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { GoogleSignInButton } from './GoogleSignInButton';
import { signIn } from 'next-auth/react';

vi.mock('next-auth/react', () => ({ signIn: vi.fn() }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('GoogleSignInButton', () => {
  it('restores an enabled retry state and accessible error after Google sign-in initiation fails', async () => {
    vi.mocked(signIn).mockRejectedValue(new Error('Provider unavailable'));
    render(<GoogleSignInButton callbackUrl="/studio" />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    expect((await screen.findByRole('alert')).textContent).toBe(
      'Unable to start Google sign-in. Please try again.',
    );
    expect(
      screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled'),
    ).toBe(false);
    expect(signIn).toHaveBeenCalledWith('google', { callbackUrl: '/studio' });
  });

  it('restores an enabled retry state when Google sign-in returns without navigation', async () => {
    vi.mocked(signIn).mockResolvedValue(undefined);
    render(<GoogleSignInButton callbackUrl="/studio" />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    expect((await screen.findByRole('alert')).textContent).toBe(
      'Unable to start Google sign-in. Please try again.',
    );
    expect(
      screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled'),
    ).toBe(false);
  });

  it('keeps the button disabled while Google sign-in is in flight', () => {
    vi.mocked(signIn).mockReturnValue(new Promise(() => {}) as ReturnType<typeof signIn>);
    render(<GoogleSignInButton callbackUrl="/studio" />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    expect(
      screen.getByRole('button', { name: 'Redirecting to Google…' }).hasAttribute('disabled'),
    ).toBe(true);
  });
});
