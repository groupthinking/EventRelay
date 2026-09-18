// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GoogleSignInButton } from './GoogleSignInButton';

vi.mock('next-auth/react', () => ({ signIn: vi.fn() }));

const callbackUrl = '/studio';
const genericError = 'Unable to start Google sign-in. Please try again.';
const recoveryDelayMs = 1_000;
const initialUrl = window.location.href;
const mockedSignIn = vi.mocked(signIn);

beforeEach(() => {
  vi.useFakeTimers();
  mockedSignIn.mockReset();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.history.replaceState({}, '', initialUrl);
});

describe('GoogleSignInButton', () => {
  it('restores a retryable button and hides the rejected initiation detail', async () => {
    mockedSignIn
      .mockRejectedValueOnce(new Error('provider response details must stay private'))
      .mockResolvedValueOnce(undefined);

    render(<GoogleSignInButton callbackUrl={callbackUrl} />);
    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    await act(async () => {
      await Promise.resolve();
    });

    const alert = screen.getByRole('alert');
    expect(alert.textContent).toBe(genericError);
    expect(alert.textContent).not.toContain('provider response details');
    expect(
      screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled'),
    ).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));
    expect(mockedSignIn).toHaveBeenCalledTimes(2);
    expect(mockedSignIn).toHaveBeenLastCalledWith('google', { callbackUrl });
  });

  it('restores a retryable button after the redirect handoff timeout elapses', async () => {
    mockedSignIn.mockResolvedValue(undefined);

    render(<GoogleSignInButton callbackUrl={callbackUrl} />);
    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    await act(async () => {
      await Promise.resolve();
    });
    expect(
      screen.getByRole('button', { name: 'Redirecting to Google…' }).hasAttribute('disabled'),
    ).toBe(true);

    await act(async () => {
      vi.advanceTimersByTime(recoveryDelayMs);
    });

    expect(screen.getByRole('alert').textContent).toBe(genericError);
    expect(
      screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled'),
    ).toBe(false);
  });

  it('keeps duplicate-click protection after sign-in starts navigation', async () => {
    mockedSignIn.mockImplementationOnce(async () => {
      window.history.pushState({}, '', '/api/auth/signin/google');
      return undefined;
    });

    render(<GoogleSignInButton callbackUrl={callbackUrl} />);
    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    await act(async () => {
      await Promise.resolve();
    });

    fireEvent.click(screen.getByRole('button', { name: 'Redirecting to Google…' }));

    expect(mockedSignIn).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole('button', { name: 'Redirecting to Google…' }).hasAttribute('disabled'),
    ).toBe(true);
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
