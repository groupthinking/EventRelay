/* @vitest-environment jsdom */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { signIn } from 'next-auth/react';
import { GoogleSignInButton } from './GoogleSignInButton';

vi.mock('next-auth/react', () => ({
  signIn: vi.fn(),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe('GoogleSignInButton', () => {
  it('restores retry state and announces a generic error when sign-in returns without redirecting', async () => {
    vi.mocked(signIn).mockResolvedValueOnce(undefined);

    render(<GoogleSignInButton callbackUrl="/studio" />);

    const button = screen.getByRole('button', { name: 'Continue with Google' }) as HTMLButtonElement;
    fireEvent.click(button);

    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe('Redirecting to Google…');
    expect(signIn).toHaveBeenCalledWith('google', { callbackUrl: '/studio' });

    await waitFor(() => {
      expect(button.disabled).toBe(false);
    });

    expect(button.textContent).toBe('Continue with Google');
    expect(screen.getByRole('alert').textContent).toBe(
      'Google sign-in could not be started. Please try again.',
    );

    fireEvent.click(button);
    await waitFor(() => {
      expect(signIn).toHaveBeenCalledTimes(2);
    });
  });

  it('restores retry state and hides rejection details when sign-in rejects', async () => {
    vi.mocked(signIn).mockRejectedValueOnce(new Error('provider response detail'));

    render(<GoogleSignInButton callbackUrl="/studio" />);

    const button = screen.getByRole('button', { name: 'Continue with Google' }) as HTMLButtonElement;
    fireEvent.click(button);

    expect(button.disabled).toBe(true);

    await waitFor(() => {
      expect(button.disabled).toBe(false);
    });

    expect(screen.getByRole('alert').textContent).toBe(
      'Google sign-in could not be started. Please try again.',
    );
    expect(screen.queryByText('provider response detail')).toBeNull();
  });

  it('prevents duplicate Google sign-in requests while a redirect handoff is pending', () => {
    vi.mocked(signIn).mockReturnValue(new Promise(() => {}));

    render(<GoogleSignInButton callbackUrl="/studio" />);

    const button = screen.getByRole('button', { name: 'Continue with Google' }) as HTMLButtonElement;
    fireEvent.click(button);
    fireEvent.click(button);

    expect(button.disabled).toBe(true);
    expect(signIn).toHaveBeenCalledTimes(1);
  });
});
