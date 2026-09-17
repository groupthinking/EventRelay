// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { signIn } from 'next-auth/react';
import { GoogleSignInButton } from './GoogleSignInButton';

vi.mock('next-auth/react', () => ({ signIn: vi.fn() }));

const retryError = 'Unable to start Google sign-in. Please try again.';

let initialHref: string;

beforeEach(() => {
  vi.mocked(signIn).mockReset();
  vi.stubGlobal('React', React);
  initialHref = window.location.href;
});

afterEach(() => {
  cleanup();
  window.history.replaceState({}, '', initialHref);
  vi.unstubAllGlobals();
});

describe('GoogleSignInButton', () => {
  it('restores a retryable state when Google sign-in returns without redirecting', async () => {
    vi.mocked(signIn).mockResolvedValueOnce(undefined).mockResolvedValueOnce(undefined);

    render(<GoogleSignInButton callbackUrl="/studio" />);

    const button = screen.getByRole('button', { name: 'Continue with Google' });
    fireEvent.click(button);

    const error = await screen.findByRole('alert');
    expect(error.textContent).toBe(retryError);
    expect(error.textContent).not.toContain('provider response');
    await waitFor(() => expect(button.hasAttribute('disabled')).toBe(false));

    fireEvent.click(button);
    await waitFor(() => expect(vi.mocked(signIn)).toHaveBeenCalledTimes(2));
  });

  it('restores a retryable state without exposing rejected sign-in details', async () => {
    vi.mocked(signIn).mockRejectedValueOnce(new Error('provider response contained a token'));

    render(<GoogleSignInButton callbackUrl="/studio" />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    const error = await screen.findByRole('alert');
    expect(error.textContent).toBe(retryError);
    expect(error.textContent).not.toContain('token');
    expect(screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled')).toBe(
      false,
    );
  });

  it('prevents duplicate clicks after the browser begins the Google handoff', async () => {
    let completeHandoff!: () => void;
    vi.mocked(signIn).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          completeHandoff = () => {
            window.history.replaceState({}, '', '/api/auth/signin/google');
            resolve(undefined);
          };
        }),
    );

    render(<GoogleSignInButton callbackUrl="/studio" />);

    const button = screen.getByRole('button', { name: 'Continue with Google' });
    fireEvent.click(button);
    await waitFor(() => expect(vi.mocked(signIn)).toHaveBeenCalledTimes(1));

    expect(button.hasAttribute('disabled')).toBe(true);
    fireEvent.click(button);
    expect(vi.mocked(signIn)).toHaveBeenCalledTimes(1);

    await act(async () => completeHandoff());

    expect(button.hasAttribute('disabled')).toBe(true);
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
