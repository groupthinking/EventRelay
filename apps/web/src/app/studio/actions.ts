'use server';

import 'server-only';
import {
  createOrUpdatePullRequestsForApprovedSpecs,
  type ApprovedSpecPullRequestInput,
  type GitHubPullRequestWriteResult,
} from '@/lib/github-pr-client';

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

export async function openGitHubPrsForApprovedSpecs(
  specs: ApprovedSpecPullRequestInput[],
): Promise<OpenGitHubPrsResult> {
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
