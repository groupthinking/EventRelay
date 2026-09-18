'use client';

import { signIn } from 'next-auth/react';
import { LogIn } from 'lucide-react';
import { useState } from 'react';

type GoogleSignInButtonProps = {
  callbackUrl: string;
};

const signInErrorMessage = 'Unable to start Google sign-in. Please try again.';

export function GoogleSignInButton({ callbackUrl }: GoogleSignInButtonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSignIn() {
    setIsSubmitting(true);
    setErrorMessage(null);

    const initialLocation = window.location.href;

    try {
      await signIn('google', { callbackUrl });
      await new Promise((resolve) => window.setTimeout(resolve, 0));

      if (window.location.href !== initialLocation) {
        return;
      }
    } catch {
      // Provider details must not be exposed in the client UI or logs.
    }

    setErrorMessage(signInErrorMessage);
    setIsSubmitting(false);
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={handleSignIn}
        disabled={isSubmitting}
        className="flex w-full items-center justify-center gap-3 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200 disabled:cursor-wait disabled:opacity-70"
      >
        <LogIn className="h-5 w-5" aria-hidden="true" />
        {isSubmitting ? 'Redirecting to Google…' : 'Continue with Google'}
      </button>
      {errorMessage ? (
        <p role="alert" className="text-sm text-rose-300">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
