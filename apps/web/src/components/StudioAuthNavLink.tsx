'use client';

import Link from 'next/link';
import { signOut, useSession } from 'next-auth/react';
import { CANONICAL_STUDIO_PATH } from '@/lib/auth-paths';

const signInHref = `/login?callbackUrl=${encodeURIComponent(CANONICAL_STUDIO_PATH)}`;

export function StudioAuthNavLink() {
  const { data: session, status } = useSession();

  if (status === 'loading') {
    return (
      <span
        className="rounded-full border border-white/10 px-4 py-1.5 text-sm text-white/40"
        aria-hidden
      >
        …
      </span>
    );
  }

  if (session?.user) {
    const label = session.user.email ?? session.user.name ?? 'Signed in';
    return (
      <div className="flex max-w-xs items-center gap-2">
        <span className="truncate text-sm text-white/75" title={label}>
          {label}
        </span>
        <button
          type="button"
          onClick={() => {
            void signOut({ callbackUrl: CANONICAL_STUDIO_PATH });
          }}
          className="shrink-0 rounded-full border border-white/15 px-3 py-1.5 text-sm text-white/80 hover:bg-white/5"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <Link
      href={signInHref}
      className="rounded-full border border-white/15 px-4 py-1.5 text-sm text-white/80 hover:bg-white/5"
    >
      Sign in
    </Link>
  );
}
