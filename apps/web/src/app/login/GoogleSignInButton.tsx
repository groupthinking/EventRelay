'use client';

import { signIn } from 'next-auth/react';
import { LogIn } from 'lucide-react';
import { useState } from 'react';

type GoogleSignInButtonProps = {
  callbackUrl: string;
};

export function GoogleSignInButton({ callbackUrl }: GoogleSignInButtonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSignIn() {
    setIsSubmitting(true);
    await signIn('google', { callbackUrl });
  }

  return (
    <button
      type="button"
      onClick={handleSignIn}
      disabled={isSubmitting}
      className="flex w-full items-center justify-center gap-3 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200 disabled:cursor-wait disabled:opacity-70"
    >
      <LogIn className="h-5 w-5" aria-hidden="true" />
      {isSubmitting ? 'Redirecting to Google…' : 'Continue with Google'}
    </button>
  );
}
