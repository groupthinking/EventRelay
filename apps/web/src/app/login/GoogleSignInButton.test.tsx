// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { GoogleSignInButton } from './GoogleSignInButton';

vi.mock('next-auth/react', () => ({ signIn: vi.fn() }));

const genericError = 'Unable to start Google sign-in. Please try again.';
const initialUrl = window.location.href;

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState({}, '', initialUrl);
});

describe('GoogleSignInButton', () => {
  it('restores a retryable button and announces a generic error after sign-in rejects', async () => {
    vi.mocked(signIn)
      .mockRejectedValueOnce(new Error('provider response details must stay private'))
      .mockImplementationOnce(() => new Promise<never>(() => undefined));

    render(<GoogleSignInButton callbackUrl="/studio" />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled'),
      ).toBe(false);
    });

    const alert = screen.getByRole('alert');
    expect(alert.textContent).toBe(genericError);
    expect(alert.textContent).not.toContain('provider response details');

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    expect(signIn).toHaveBeenCalledTimes(2);
    expect(
      screen.getByRole('button', { name: 'Redirecting to Google…' }).hasAttribute('disabled'),
    ).toBe(true);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('restores a retryable button when sign-in returns without starting a redirect', async () => {
    vi.mocked(signIn).mockResolvedValueOnce(undefined);

    render(<GoogleSignInButton callbackUrl="/studio" />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Continue with Google' }).hasAttribute('disabled'),
      ).toBe(false);
    });

    expect(screen.getByRole('alert').textContent).toBe(genericError);
  });

  it('keeps duplicate-click protection after sign-in starts navigation', async () => {
    vi.mocked(signIn).mockImplementationOnce(async () => {
      window.history.pushState({}, '', '/api/auth/signin/google');
      return undefined;
    });

    render(<GoogleSignInButton callbackUrl="/studio" />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Redirecting to Google…' }).hasAttribute('disabled'),
      ).toBe(true);
    });

    fireEvent.click(screen.getByRole('button', { name: 'Redirecting to Google…' }));

    expect(signIn).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('keeps the button disabled when navigation starts right after sign-in resolves', async () => {
    vi.mocked(signIn).mockImplementationOnce(async () => {
      setTimeout(() => {
        window.history.pushState({}, '', '/api/auth/signin/google');
      }, 0);
      return undefined;
    });

    render(<GoogleSignInButton callbackUrl="/studio" />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Google' }));

    await waitFor(() => {
      expect(window.location.pathname).toBe('/api/auth/signin/google');
    });

    expect(
      screen.getByRole('button', { name: 'Redirecting to Google…' }).hasAttribute('disabled'),
    ).toBe(true);
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
