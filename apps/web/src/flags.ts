import { vercelAdapter } from '@flags-sdk/vercel';
import { flag } from 'flags/next';

export const customBadge = flag<boolean>({
  key: 'custom-badge',
  defaultValue: false,
  adapter: vercelAdapter(),
  description: 'Show a Vercel Flags-powered badge on the UVAI homepage',
});

// Production keeps the classic home + Studio IDE until the flag is flipped in
// the Vercel dashboard; local dev and previews default to the live Studio.
export const liveStudio = flag<boolean>({
  key: 'live-studio',
  defaultValue: process.env.VERCEL_ENV !== 'production',
  adapter: vercelAdapter(),
  description: 'Serve the short home on-ramp and the live Studio workspace (chapters, transcript, editable tasks, dispatch)',
});

// Plan 005: unified AppShell sidebar + Home URL/intent dock and showcase gallery.
// Production keeps the existing Home until this flag is flipped in the Vercel dashboard.
export const projectWorkspace = flag<boolean>({
  key: 'project-workspace',
  defaultValue: process.env.VERCEL_ENV !== 'production',
  adapter: vercelAdapter(),
  description: 'Serve the unified AppShell sidebar and Home URL/intent dock + showcase gallery (Plan 005)',
});
