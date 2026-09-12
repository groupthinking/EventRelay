import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/github-pr-client', () => ({
  createOrUpdatePullRequestsForApprovedSpecs: vi.fn(),
}));

vi.mock('next/headers', () => ({
  headers: vi.fn(async () => new Headers()),
}));

vi.mock('@/lib/billing/billing-context', () => ({
  resolveTrustedBillingEmail: vi.fn(async () => 'pro@example.com'),
}));

vi.mock('@/lib/billing/entitlement-store', () => ({
  isProSubscriber: vi.fn(async () => true),
}));

import { openGitHubPrsForApprovedSpecs } from '@/app/studio/actions';
import { createOrUpdatePullRequestsForApprovedSpecs } from '@/lib/github-pr-client';
import { isProSubscriber } from '@/lib/billing/entitlement-store';

const mockedOpen = vi.mocked(createOrUpdatePullRequestsForApprovedSpecs);
const mockedIsPro = vi.mocked(isProSubscriber);

describe('openGitHubPrsForApprovedSpecs', () => {
  const originalToken = process.env.GITHUB_TOKEN;
  const originalRepo = process.env.GITHUB_REPOSITORY;

  beforeEach(() => {
    vi.clearAllMocks();
    process.env.GITHUB_TOKEN = 'test-token';
    process.env.GITHUB_REPOSITORY = 'octo/eventrelay';
  });

  afterEach(() => {
    if (originalToken === undefined) delete process.env.GITHUB_TOKEN;
    else process.env.GITHUB_TOKEN = originalToken;
    if (originalRepo === undefined) delete process.env.GITHUB_REPOSITORY;
    else process.env.GITHUB_REPOSITORY = originalRepo;
  });

  it('refuses callers without a Pro entitlement', async () => {
    mockedIsPro.mockResolvedValueOnce(false);

    const result = await openGitHubPrsForApprovedSpecs([
      { id: 'spec-1', title: 'Approved', body: 'Body', head: 'spec/approved', approved: true },
    ]);

    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/pro subscription/i);
    expect(mockedOpen).not.toHaveBeenCalled();
  });

  it('fails closed when no spec is approved', async () => {
    const result = await openGitHubPrsForApprovedSpecs([
      { id: 'spec-1', title: 'Spec', body: 'Body', head: 'spec/one', approved: false },
    ]);

    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/approve at least one spec/i);
    expect(mockedOpen).not.toHaveBeenCalled();
  });

  it('calls the GitHub write flow with only approved specs', async () => {
    mockedOpen.mockResolvedValue([
      { specId: 'spec-1', number: 10, htmlUrl: 'https://github.com/o/r/pull/10', action: 'created' },
    ]);

    const result = await openGitHubPrsForApprovedSpecs([
      { id: 'spec-1', title: 'Approved', body: 'Body', head: 'spec/approved', approved: true },
      { id: 'spec-2', title: 'Skipped', body: 'Body', head: 'spec/skipped', approved: false },
    ]);

    expect(result.ok).toBe(true);
    expect(mockedOpen).toHaveBeenCalledWith(
      [
        { id: 'spec-1', title: 'Approved', body: 'Body', head: 'spec/approved', approved: true },
      ],
      expect.objectContaining({
        owner: 'octo',
        repo: 'eventrelay',
        token: 'test-token',
      }),
    );
  });

  it('fails closed when GitHub integration is not configured', async () => {
    delete process.env.GITHUB_TOKEN;
    const result = await openGitHubPrsForApprovedSpecs([
      { id: 'spec-1', title: 'Approved', body: 'Body', head: 'spec/approved', approved: true },
    ]);

    expect(result.ok).toBe(false);
    expect(result.error).toMatch(/not configured/i);
    expect(mockedOpen).not.toHaveBeenCalled();
  });
});
