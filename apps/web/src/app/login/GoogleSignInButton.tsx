'use client';

import { signIn } from 'next-auth/react';
import { useState } from 'react';

type GoogleSignInButtonProps = {
  callbackUrl: string;
};

export default function GoogleSignInButton({ callbackUrl }: GoogleSignInButtonProps) {
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
      <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M21.35 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.24a4.48 4.48 0 0 1-1.94 2.94v2.51h3.14c1.84-1.7 2.91-4.2 2.91-7.28Z" />
        <path fill="#34A853" d="M12 21.75c2.63 0 4.84-.87 6.44-2.24L15.3 17a5.8 5.8 0 0 1-8.63-3.05H3.43v2.59A9.73 9.73 0 0 0 12 21.75Z" />
        <path fill="#FBBC05" d="M6.67 13.95a5.83 5.83 0 0 1 0-3.9V7.46H3.43a9.75 9.75 0 0 0 0 9.08l3.24-2.59Z" />
        <path fill="#EA4335" d="M12 5.75c1.51 0 2.87.52 3.94 1.54l2.95-2.95C16.84 2.44 14.63 1.25 12 1.25a9.73 9.73 0 0 0-8.57 5.21l3.24 2.59A5.8 5.8 0 0 1 12 5.75Z" />
      </svg>
      {isSubmitting ? 'Redirecting to Google…' : 'Continue with Google'}
    </button>
  );
}
