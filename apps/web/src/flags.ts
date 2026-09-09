import { vercelAdapter } from '@flags-sdk/vercel';
import { flag } from 'flags/next';

export const customBadge = flag<boolean>({
  key: 'custom-badge',
  adapter: vercelAdapter(),
  description: 'Show a Vercel Flags-powered badge on the UVAI homepage',
});

export const agentWorkflowUi = flag<boolean>({
  key: 'agent-workflow-ui',
  adapter: vercelAdapter(),
  description: 'Show the durable agent workflow controls and verified tool results in UVAI Studio',
});
