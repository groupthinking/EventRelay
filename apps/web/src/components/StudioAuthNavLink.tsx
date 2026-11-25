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
        className="rounded-full border px-4 py-1.5 text-sm"
        style={{ borderColor: 'var(--uvai-border)', color: 'var(--uvai-ink-faint)' }}
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
        <span className="truncate text-sm font-medium" style={{ color: 'var(--uvai-ink-soft)' }} title={label}>
          {label}
        </span>
        <button
          type="button"
          onClick={() => {
            void signOut({ callbackUrl: CANONICAL_STUDIO_PATH });
          }}
          className="uvai-btn shrink-0 rounded-full !px-3 !py-1.5 text-sm"
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <Link
      href={signInHref}
      className="uvai-btn uvai-btn-primary rounded-full !px-4 !py-1.5 text-sm"
    >
      Sign in
    </Link>
  );
}
