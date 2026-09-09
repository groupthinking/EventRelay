import { vercelAdapter } from '@flags-sdk/vercel';
import { flag } from 'flags/next';

export const customBadge = flag<boolean>({
  key: 'custom-badge',
  adapter: vercelAdapter(),
  description: 'Show a Vercel Flags-powered badge on the UVAI homepage',
});
