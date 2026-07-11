'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';

// Catches React rendering errors that escape every route-level error
// boundary (including errors thrown in the root layout) and reports them
// to Sentry. Must render its own <html>/<body> because it replaces the
// root layout when active.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          display: 'flex',
          minHeight: '100vh',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
          background: '#0a0a0a',
          color: '#fafafa',
        }}
      >
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <h1 style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>
            Something went wrong
          </h1>
          <p style={{ opacity: 0.7, marginBottom: '1.5rem' }}>
            The error has been reported. Please try again.
          </p>
          <button
            onClick={reset}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: '0.5rem',
              border: '1px solid #333',
              background: '#1a1a1a',
              color: '#fafafa',
              cursor: 'pointer',
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
