// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GoogleSignInButton } from './GoogleSignInButton';

const { signIn } = vi.hoisted(() => ({ signIn: vi.fn() }));

vi.mock('next-auth/react', () => ({ signIn }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

beforeEach(() => {
  vi.stubGlobal('React', React);
  signIn.mockReset();
});

describe('GoogleSignInButton', () => {
  it('restores a retryable button and explains when Google sign-in does not redirect', async () => {
    let resolveSignIn!: () => void;
    signIn.mockImplementationOnce(
      () => new Promise<void>((resolve) => {
        resolveSignIn = resolve;
      }),
    );

    render(<GoogleSignInButton callbackUrl="/studio" />);

    act(() => {
      fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));
    });

    expect(signIn).toHaveBeenCalledWith('google', { callbackUrl: '/studio' });
    expect(screen.getByRole('button', { name: 'Redirecting to Google…' }).hasAttribute('disabled')).toBe(
      true,
    );

    await act(async () => {
      resolveSignIn();
    });

    expect(screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled')).toBe(
      false,
    );
    expect(screen.getByRole('alert').textContent).toBe(
      'Google sign-in did not start. Please try again.',
    );

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));
    });
    expect(signIn).toHaveBeenCalledTimes(2);
  });
});
