// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { signIn } from 'next-auth/react';
import { GoogleSignInButton } from './GoogleSignInButton';

vi.mock('next-auth/react', () => ({ signIn: vi.fn() }));

const callbackUrl = '/studio?video=https://www.youtube.com/watch?v=auJzb1D-fag';
const genericError = 'We couldn’t start Google sign-in. Please try again.';

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });

  return { promise, reject, resolve };
}

function renderButton() {
  render(<GoogleSignInButton callbackUrl={callbackUrl} />);
  return screen.getByRole('button', { name: 'Continue with Google' }) as HTMLButtonElement;
}

function getRetryButton() {
  return screen.getByRole('button', { name: 'Continue with Google' }) as HTMLButtonElement;
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  window.history.replaceState({}, '', '/login');
});

describe('GoogleSignInButton', () => {
  it('shows a generic error and permits retry after Google sign-in initiation rejects', async () => {
    const failedAttempt = createDeferred<undefined>();
    const retryAttempt = createDeferred<undefined>();
    vi.mocked(signIn)
      .mockReturnValueOnce(failedAttempt.promise)
      .mockReturnValueOnce(retryAttempt.promise);

    const firstButton = renderButton();
    act(() => {
      fireEvent.click(firstButton);
    });

    expect(signIn).toHaveBeenCalledWith('google', { callbackUrl });
    expect(firstButton.disabled).toBe(true);
    expect(firstButton.textContent).toContain('Redirecting to Google…');

    await act(async () => {
      failedAttempt.reject(new Error('Sign-in initiation failed'));
      await failedAttempt.promise.catch(() => undefined);
    });

    expect(screen.getByRole('alert').textContent).toBe(genericError);
    expect(getRetryButton().disabled).toBe(false);

    act(() => {
      fireEvent.click(getRetryButton());
    });
    expect(signIn).toHaveBeenCalledTimes(2);
  });

  it('shows a retryable error when Google sign-in resolves without navigation', async () => {
    const attempt = createDeferred<undefined>();
    vi.mocked(signIn).mockReturnValueOnce(attempt.promise);

    const button = renderButton();
    act(() => {
      fireEvent.click(button);
    });

    expect(signIn).toHaveBeenCalledWith('google', { callbackUrl });
    expect(button.disabled).toBe(true);

    await act(async () => {
      attempt.resolve(undefined);
      await attempt.promise;
    });

    expect(screen.getByRole('alert').textContent).toBe(genericError);
    expect(getRetryButton().disabled).toBe(false);
  });

  it('keeps duplicate-click prevention active after Google sign-in starts navigation', async () => {
    const attempt = createDeferred<undefined>();
    vi.mocked(signIn).mockReturnValueOnce(attempt.promise);

    const button = renderButton();
    act(() => {
      fireEvent.click(button);
      fireEvent.click(button);
    });

    expect(signIn).toHaveBeenCalledTimes(1);
    expect(button.disabled).toBe(true);
    expect(button.textContent).toContain('Redirecting to Google…');

    await act(async () => {
      window.history.pushState({}, '', '/oauth-handoff-started');
      attempt.resolve(undefined);
      await attempt.promise;
    });

    expect(
      (screen.getByRole('button', { name: 'Redirecting to Google…' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
