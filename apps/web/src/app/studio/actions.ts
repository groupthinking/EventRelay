'use server';

import 'server-only';
import { headers } from 'next/headers';
import {
  createOrUpdatePullRequestsForApprovedSpecs,
  type ApprovedSpecPullRequestInput,
  type GitHubPullRequestWriteResult,
} from '@/lib/github-pr-client';
import { resolveTrustedBillingEmail } from '@/lib/billing/billing-context';
import { isProSubscriber } from '@/lib/billing/entitlement-store';

export interface OpenGitHubPrsResult {
  ok: boolean;
  error?: string;
  pullRequests: GitHubPullRequestWriteResult[];
}

function parseRepository(value: string): { owner: string; repo: string } | null {
  const [owner, repo, ...rest] = value.trim().split('/');
  if (!owner || !repo || rest.length > 0) return null;
  return { owner, repo };
}

/**
 * Resolve the trusted billing identity for this server action.
 *
 * Server actions POST to the page path, and `/studio` is intentionally public
 * (see auth-paths.ts), so the middleware auth gate does *not* run here. Without
 * an explicit check any anonymous visitor could invoke this action and drive
 * GitHub writes with the server's GITHUB_TOKEN. We rebuild a minimal Request
 * from the incoming cookies so the same trusted-identity resolution used by
 * privileged API routes (session email → signed billing cookie) applies here.
 */
async function resolveActionBillingEmail(): Promise<string | null> {
  const cookieHeader = (await headers()).get('cookie') ?? '';
  const request = new Request('https://studio.internal/studio', {
    headers: { cookie: cookieHeader },
  });
  return resolveTrustedBillingEmail(request);
}

export async function openGitHubPrsForApprovedSpecs(
  specs: ApprovedSpecPullRequestInput[],
): Promise<OpenGitHubPrsResult> {
  // Authorize before touching any server-side GitHub credentials. Opening PRs
  // in the configured repository is a privileged, Pro-gated action — the same
  // entitlement class as agent dispatch — so anonymous/free callers are refused
  // before any GitHub API request is made.
  const billingEmail = await resolveActionBillingEmail();
  if (!(await isProSubscriber(billingEmail))) {
    return {
      ok: false,
      error: 'Opening GitHub pull requests requires a Pro subscription. Upgrade at /pricing.',
      pullRequests: [],
    };
  }

  const approvedSpecs = specs.filter((spec) => spec.approved);
  if (approvedSpecs.length === 0) {
    return {
      ok: false,
      error: 'Approve at least one spec before opening GitHub pull requests.',
      pullRequests: [],
    };
  }

  const token = (process.env.GITHUB_TOKEN || '').trim();
  const repository = parseRepository(process.env.GITHUB_REPOSITORY || '');
  if (!token || !repository) {
    return {
      ok: false,
      error: 'GitHub integration is not configured.',
      pullRequests: [],
    };
  }

  try {
    const pullRequests = await createOrUpdatePullRequestsForApprovedSpecs(
      approvedSpecs,
      {
        owner: repository.owner,
        repo: repository.repo,
        token,
      },
    );
    return { ok: true, pullRequests };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'Could not open GitHub pull requests.',
      pullRequests: [],
    };
  }
}
