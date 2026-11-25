import { describe, expect, it, vi } from 'vitest';
import {
  createOrUpdatePullRequest,
  createOrUpdatePullRequestsForApprovedSpecs,
  type ApprovedSpecPullRequestInput,
} from '@/lib/github-pr-client';

describe('github-pr-client', () => {
  it('creates a pull request when no open PR exists for the spec branch', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ number: 7, html_url: 'https://github.com/o/r/pull/7' }), {
          status: 201,
        }),
      );

    const result = await createOrUpdatePullRequest(
      {
        id: 'spec-1',
        title: 'Add onboarding workflow',
        body: '## Spec\n\n- Add onboarding flow',
        head: 'spec/add-onboarding-workflow',
        base: 'main',
      },
      { owner: 'octo', repo: 'eventrelay', token: 'token', fetchImpl },
    );

    expect(result).toEqual(
      expect.objectContaining({
        specId: 'spec-1',
        number: 7,
        htmlUrl: 'https://github.com/o/r/pull/7',
        action: 'created',
      }),
    );

    expect(fetchImpl).toHaveBeenCalledTimes(2);
    expect(String(fetchImpl.mock.calls[0]?.[0])).toContain('/repos/octo/eventrelay/pulls?');
    expect(String(fetchImpl.mock.calls[1]?.[0])).toContain('/repos/octo/eventrelay/pulls');
    const body = JSON.parse(String((fetchImpl.mock.calls[1]?.[1] as RequestInit).body));
    expect(body).toMatchObject({
      title: 'Add onboarding workflow',
      head: 'spec/add-onboarding-workflow',
      base: 'main',
    });
  });

  it('updates the existing pull request when one already exists for the spec branch', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify([{ number: 42, html_url: 'https://github.com/o/r/pull/42' }]),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ number: 42, html_url: 'https://github.com/o/r/pull/42' }), {
          status: 200,
        }),
      );

    const result = await createOrUpdatePullRequest(
      {
        id: 'spec-2',
        title: 'Revise payment handoff',
        body: 'Updated spec body',
        head: 'spec/revise-payment-handoff',
        base: 'main',
      },
      { owner: 'octo', repo: 'eventrelay', token: 'token', fetchImpl },
    );

    expect(result.action).toBe('updated');
    expect(result.number).toBe(42);
    expect(String(fetchImpl.mock.calls[1]?.[0])).toContain('/repos/octo/eventrelay/pulls/42');
    const body = JSON.parse(String((fetchImpl.mock.calls[1]?.[1] as RequestInit).body));
    expect(body).toMatchObject({
      title: 'Revise payment handoff',
      body: 'Updated spec body',
      base: 'main',
    });
  });

  it('opens pull requests only for approved specs', async () => {
    const specs: ApprovedSpecPullRequestInput[] = [
      {
        id: 'spec-approved',
        title: 'Approved spec',
        body: 'Approved body',
        head: 'spec/approved',
        approved: true,
      },
      {
        id: 'spec-unapproved',
        title: 'Unapproved spec',
        body: 'Unapproved body',
        head: 'spec/unapproved',
        approved: false,
      },
    ];
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ number: 9, html_url: 'https://github.com/o/r/pull/9' }), {
          status: 201,
        }),
      );

    const result = await createOrUpdatePullRequestsForApprovedSpecs(specs, {
      owner: 'octo',
      repo: 'eventrelay',
      token: 'token',
      fetchImpl,
    });

    expect(result).toHaveLength(1);
    expect(result[0]?.specId).toBe('spec-approved');
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });
});
