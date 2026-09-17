// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { signIn } from 'next-auth/react';
import { GoogleSignInButton } from './GoogleSignInButton';

vi.mock('next-auth/react', () => ({ signIn: vi.fn() }));

const callbackUrl = '/studio';
const genericError = 'Unable to start Google sign-in. Please try again.';
const recoveryDelayMs = 1_000;
const mockedSignIn = vi.mocked(signIn);

beforeEach(() => {
  vi.useFakeTimers();
  mockedSignIn.mockReset();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('GoogleSignInButton', () => {
  it('restores a retryable button and hides the rejected initiation detail', async () => {
    mockedSignIn
      .mockRejectedValueOnce(new Error('network request failed'))
      .mockResolvedValueOnce(undefined);

    render(<GoogleSignInButton callbackUrl={callbackUrl} />);
    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByRole('alert').textContent).toBe(genericError);
    expect(screen.queryByText('network request failed')).toBeNull();
    expect(
      screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled'),
    ).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));
    expect(mockedSignIn).toHaveBeenCalledTimes(2);
    expect(mockedSignIn).toHaveBeenLastCalledWith('google', { callbackUrl });
  });

  it('restores a retryable button after a resolved initiation leaves the page mounted', async () => {
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

  it('prevents duplicate initiation while the OAuth handoff promise is pending', () => {
    mockedSignIn.mockImplementation(() => new Promise<undefined>(() => undefined));

    render(<GoogleSignInButton callbackUrl={callbackUrl} />);
    const button = screen.getByRole('button', { name: 'Continue with Google' });
    fireEvent.click(button);
    fireEvent.click(button);

    expect(mockedSignIn).toHaveBeenCalledOnce();
    expect(
      screen.getByRole('button', { name: 'Redirecting to Google…' }).hasAttribute('disabled'),
    ).toBe(true);
  });
});
