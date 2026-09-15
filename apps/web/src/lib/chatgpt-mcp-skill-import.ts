import { canonicalGateJson, hashCanonical } from '@/lib/gate-transition';

export const MCP_SKILLS_EXTENSION_ID = 'io.modelcontextprotocol/skills' as const;
export const CHATGPT_SKILL_IMPORT_RECEIPT_VERSION =
  'eventrelay.chatgpt-mcp-skill-import-receipt.v1' as const;
export const MCP_SKILLS_SPEC_COMMIT =
  'd866efdba298b55b8156c7b7aa1bdebc1b625f4c' as const;
export const MCP_CLIENT_MATRIX_REVISION =
  '2997f33bf6e4aab3db48d755fc877c8feab32c71' as const;

type CacheScope = 'public' | 'private';

export type SkillManifestResource = {
  uri: string;
  digest: string | 'dynamic';
  size: number | 'dynamic';
};

export type SkillGetResult = {
  resultType: 'complete';
  ttlMs: number;
  cacheScope: CacheScope;
  skill: {
    uri: string;
    name: string;
    description: string;
    resources: SkillManifestResource[];
  };
};

export type FixtureChatGptSkillImportInput = {
  serverIdentity: string;
  requestedSkillUri: string;
  capabilities: {
    resources?: object;
    extensions?: Record<string, object>;
  };
  result: SkillGetResult;
  resourceContents: Record<string, string>;
  approvedManifestDigest?: string | null;
  issuedAt?: string;
};

export type FixtureChatGptSkillImportReceipt = {
  version: typeof CHATGPT_SKILL_IMPORT_RECEIPT_VERSION;
  mode: 'fixture-only';
  target_client: 'chatgpt';
  client_support: {
    status: 'partial';
    evidence_kind: 'official-mcp-client-matrix';
    evidence_revision: typeof MCP_CLIENT_MATRIX_REVISION;
    live_client_observed: false;
    conformance_claim: 'not-claimed';
  };
  wire_contract: {
    extension_id: typeof MCP_SKILLS_EXTENSION_ID;
    specification_commit: typeof MCP_SKILLS_SPEC_COMMIT;
  };
  decision: 'READY_FOR_FIXTURE_HANDOFF';
  issued_at: string;
  compound_identity: {
    server_identity: string;
    skill_uri: string;
  };
  manifest: {
    digest: string;
    resource_count: number;
    resources: Array<{ uri: string; digest: string; size: number }>;
  };
  cache: {
    ttl_ms: number;
    scope: CacheScope;
    integrity_authority_effect: 'none';
  };
  authorization: {
    status: 'NOT_GRANTED' | 'VALID_FOR_MANIFEST' | 'INVALIDATED';
    approved_manifest_digest: string | null;
    authority_effect: 'none';
    untrusted_skill_content_cannot_grant_authority: true;
  };
  handoff: {
    import_state: 'not-executed';
    network_calls: 0;
    tool_calls: 0;
    external_effects: 0;
  };
  receipt_hash: string;
};

const SHA256_DIGEST = /^sha256:[a-f0-9]{64}$/;
const SKILL_URI = /^skill:\/\/(.+)\/SKILL\.md$/;
const SKILL_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function hold(message: string): never {
  throw new Error(`ChatGPT fixture handoff held: ${message}`);
}

function parseFrontmatterName(content: string): string {
  const match = /^---\s*\n([\s\S]*?)\n---(?:\s*\n|$)/.exec(content);
  if (!match) hold('SKILL.md frontmatter is missing.');
  const nameLine = match[1]
    .split('\n')
    .find((line) => /^name\s*:/.test(line.trim()));
  if (!nameLine) hold('SKILL.md frontmatter name is missing.');
  const name = nameLine.slice(nameLine.indexOf(':') + 1).trim().replace(/^['"]|['"]$/g, '');
  if (!SKILL_NAME.test(name)) hold('SKILL.md frontmatter name is invalid.');
  return name;
}

function skillRoot(uri: string): { path: string; name: string } {
  const match = SKILL_URI.exec(uri);
  if (!match) hold('skill URI must end in /SKILL.md.');
  const path = match[1];
  const segments = path.split('/');
  if (segments.some((segment) => !segment || segment === '.' || segment === '..')) {
    hold('skill URI path is not confined.');
  }
  const name = segments.at(-1)!;
  if (!SKILL_NAME.test(name)) hold('skill URI final segment is invalid.');
  return { path, name };
}

function verifyManifest(
  skillUri: string,
  resources: readonly SkillManifestResource[],
  contents: Readonly<Record<string, string>>,
): Array<{ uri: string; digest: string; size: number }> {
  const { path } = skillRoot(skillUri);
  const root = `skill://${path}/`;
  if (resources.length === 0) hold('skill manifest is empty.');

  const seen = new Set<string>();
  const verified = resources.map((resource) => {
    if (seen.has(resource.uri)) hold('skill manifest contains a duplicate URI.');
    seen.add(resource.uri);
    if (!resource.uri.startsWith(root)) hold('resource URI escapes the skill root.');
    const suffix = resource.uri.slice(root.length);
    if (!suffix || suffix.split('/').some((segment) => !segment || segment === '.' || segment === '..')) {
      hold('resource URI path is not confined.');
    }
    if (resource.digest === 'dynamic' || resource.size === 'dynamic') {
      hold('dynamic resources are not accepted by this fixture-only contract.');
    }
    if (!SHA256_DIGEST.test(resource.digest)) hold('resource digest is invalid.');
    if (!Number.isInteger(resource.size) || resource.size < 0) hold('resource size is invalid.');

    const content = contents[resource.uri];
    if (typeof content !== 'string') hold(`resource content is missing for ${resource.uri}.`);
    const digest = `sha256:${hashCanonical(content)}`;
    const size = new TextEncoder().encode(content).byteLength;
    if (digest !== resource.digest) hold(`resource digest mismatch for ${resource.uri}.`);
    if (size !== resource.size) hold(`resource size mismatch for ${resource.uri}.`);
    return { uri: resource.uri, digest, size };
  });

  if (!seen.has(skillUri)) hold('SKILL.md is absent from the manifest.');
  return verified.sort((left, right) => left.uri.localeCompare(right.uri));
}

/**
 * Validate an inert MCP Skills package for the ChatGPT partial-support path.
 * This does not contact ChatGPT, import a skill, execute content, or grant
 * authority. The receipt proves only fixture validation against the official
 * MCP Skills wire contract.
 */
export function createFixtureChatGptSkillImport(
  input: FixtureChatGptSkillImportInput,
): FixtureChatGptSkillImportReceipt {
  const serverIdentity = input.serverIdentity.trim();
  if (!serverIdentity) hold('server identity is required.');
  if (!input.capabilities.resources) hold('resources capability is required.');
  if (!input.capabilities.extensions?.[MCP_SKILLS_EXTENSION_ID]) {
    hold('MCP Skills extension capability is required.');
  }
  if (input.result.resultType !== 'complete') hold('skills/get resultType must be complete.');
  if (!Number.isInteger(input.result.ttlMs) || input.result.ttlMs < 0) {
    hold('ttlMs must be a nonnegative integer.');
  }
  if (input.result.cacheScope !== 'public' && input.result.cacheScope !== 'private') {
    hold('cacheScope must be public or private.');
  }
  if (input.result.skill.uri !== input.requestedSkillUri) {
    hold('returned skill URI does not match the requested URI.');
  }

  const { name: uriName } = skillRoot(input.result.skill.uri);
  if (input.result.skill.name !== uriName) hold('manifest name does not match the skill URI.');
  const skillText = input.resourceContents[input.result.skill.uri];
  if (typeof skillText !== 'string') hold('SKILL.md content is missing.');
  if (parseFrontmatterName(skillText) !== uriName) {
    hold('SKILL.md frontmatter name does not match the skill URI.');
  }

  const resources = verifyManifest(
    input.result.skill.uri,
    input.result.skill.resources,
    input.resourceContents,
  );
  const manifestDigest = hashCanonical(canonicalGateJson(resources));
  const approvedManifestDigest = input.approvedManifestDigest ?? null;
  const authorizationStatus: FixtureChatGptSkillImportReceipt['authorization']['status'] =
    approvedManifestDigest === null
      ? 'NOT_GRANTED'
      : approvedManifestDigest === manifestDigest
        ? 'VALID_FOR_MANIFEST'
        : 'INVALIDATED';

  const body = {
    version: CHATGPT_SKILL_IMPORT_RECEIPT_VERSION,
    mode: 'fixture-only' as const,
    target_client: 'chatgpt' as const,
    client_support: {
      status: 'partial' as const,
      evidence_kind: 'official-mcp-client-matrix' as const,
      evidence_revision: MCP_CLIENT_MATRIX_REVISION,
      live_client_observed: false as const,
      conformance_claim: 'not-claimed' as const,
    },
    wire_contract: {
      extension_id: MCP_SKILLS_EXTENSION_ID,
      specification_commit: MCP_SKILLS_SPEC_COMMIT,
    },
    decision: 'READY_FOR_FIXTURE_HANDOFF' as const,
    issued_at: input.issuedAt ?? new Date().toISOString(),
    compound_identity: {
      server_identity: serverIdentity,
      skill_uri: input.result.skill.uri,
    },
    manifest: {
      digest: manifestDigest,
      resource_count: resources.length,
      resources,
    },
    cache: {
      ttl_ms: input.result.ttlMs,
      scope: input.result.cacheScope,
      integrity_authority_effect: 'none' as const,
    },
    authorization: {
      status: authorizationStatus,
      approved_manifest_digest: approvedManifestDigest,
      authority_effect: 'none' as const,
      untrusted_skill_content_cannot_grant_authority: true as const,
    },
    handoff: {
      import_state: 'not-executed' as const,
      network_calls: 0 as const,
      tool_calls: 0 as const,
      external_effects: 0 as const,
    },
  };
  return { ...body, receipt_hash: hashCanonical(canonicalGateJson(body)) };
}
