import 'server-only';

export interface ApprovedSpecPullRequestInput {
  id: string;
  title: string;
  body: string;
  head: string;
  base?: string;
  approved: boolean;
}

export interface GitHubPullRequestWriteResult {
  specId: string;
  number: number;
  htmlUrl: string;
  action: 'created' | 'updated';
}

export interface GitHubPullRequestClientConfig {
  owner: string;
  repo: string;
  token: string;
  fetchImpl?: typeof fetch;
}

interface GitHubPullRequestPayload {
  number?: unknown;
  html_url?: unknown;
}

function apiBase(config: GitHubPullRequestClientConfig): string {
  return `https://api.github.com/repos/${encodeURIComponent(config.owner)}/${encodeURIComponent(config.repo)}`;
}

function githubHeaders(token: string): Record<string, string> {
  return {
    Accept: 'application/vnd.github+json',
    Authorization: ['Bearer', token].join(' '),
    'Content-Type': 'application/json',
    'X-GitHub-Api-Version': '2022-11-28',
  };
}

function readResult(
  payload: GitHubPullRequestPayload | null,
  specId: string,
  action: 'created' | 'updated',
): GitHubPullRequestWriteResult {
  const number = typeof payload?.number === 'number' ? payload.number : 0;
  const htmlUrl = typeof payload?.html_url === 'string' ? payload.html_url : '';
  if (!number || !htmlUrl) {
    throw new Error(`GitHub ${action} response was missing pull request fields for spec "${specId}"`);
  }
  return { specId, number, htmlUrl, action };
}

async function parsePayload(response: Response): Promise<GitHubPullRequestPayload | null> {
  return (await response.json().catch(() => null)) as GitHubPullRequestPayload | null;
}

export async function createOrUpdatePullRequest(
  spec: Omit<ApprovedSpecPullRequestInput, 'approved'>,
  config: GitHubPullRequestClientConfig,
): Promise<GitHubPullRequestWriteResult> {
  const fetchImpl = config.fetchImpl ?? fetch;
  const base = spec.base?.trim() || 'main';
  const encodedHead = encodeURIComponent(`${config.owner}:${spec.head}`);
  const encodedBase = encodeURIComponent(base);
  const listUrl = `${apiBase(config)}/pulls?state=open&head=${encodedHead}&base=${encodedBase}&per_page=1`;

  const list = await fetchImpl(listUrl, {
    headers: githubHeaders(config.token),
    method: 'GET',
    signal: AbortSignal.timeout(30_000),
  });
  if (!list.ok) {
    const detail = await list.text();
    throw new Error(`Could not list open pull requests (${list.status}): ${detail}`);
  }

  const open = (await list.json().catch(() => [])) as Array<{ number?: unknown }>;
  const existingNumber = typeof open[0]?.number === 'number' ? open[0].number : null;

  if (existingNumber != null) {
    const update = await fetchImpl(`${apiBase(config)}/pulls/${existingNumber}`, {
      headers: githubHeaders(config.token),
      method: 'PATCH',
      body: JSON.stringify({ title: spec.title, body: spec.body, base }),
      signal: AbortSignal.timeout(30_000),
    });
    if (!update.ok) {
      const detail = await update.text();
      throw new Error(`Could not update pull request #${existingNumber} (${update.status}): ${detail}`);
    }
    return readResult(await parsePayload(update), spec.id, 'updated');
  }

  const created = await fetchImpl(`${apiBase(config)}/pulls`, {
    headers: githubHeaders(config.token),
    method: 'POST',
    body: JSON.stringify({
      title: spec.title,
      body: spec.body,
      head: spec.head,
      base,
    }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!created.ok) {
    const detail = await created.text();
    throw new Error(`Could not create pull request for spec "${spec.id}" (${created.status}): ${detail}`);
  }

  return readResult(await parsePayload(created), spec.id, 'created');
}

export async function createOrUpdatePullRequestsForApprovedSpecs(
  specs: ApprovedSpecPullRequestInput[],
  config: GitHubPullRequestClientConfig,
): Promise<GitHubPullRequestWriteResult[]> {
  const approvedSpecs = specs.filter((spec) => spec.approved);
  const results: GitHubPullRequestWriteResult[] = [];
  for (const spec of approvedSpecs) {
    results.push(
      await createOrUpdatePullRequest(
        {
          id: spec.id,
          title: spec.title,
          body: spec.body,
          head: spec.head,
          base: spec.base,
        },
        config,
      ),
    );
  }
  return results;
}
