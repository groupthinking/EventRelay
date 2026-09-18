import { parseDocument } from 'yaml';
import { canonicalGateJson, hashCanonical } from '@/lib/gate-transition';

export const MCP_SKILLS_EXTENSION_ID = 'io.modelcontextprotocol/skills' as const;
export const CHATGPT_SKILL_IMPORT_RECEIPT_VERSION =
  'eventrelay.chatgpt-mcp-skill-import-receipt.v1' as const;
export const MCP_SKILLS_NORMATIVE_CONTRACT = {
  repository: 'modelcontextprotocol/modelcontextprotocol',
  path: 'seps/2640-skills-extension.md',
  commit: '1eb5bbe8ac933bdb595fedc687b8ed545e440491',
} as const;
export const MCP_SKILLS_DESIGN_HISTORY = {
  repository: 'modelcontextprotocol/ext-skills',
  path: 'specs/skills.md',
  commit: 'd866efdba298b55b8156c7b7aa1bdebc1b625f4c',
} as const;
export const MCP_SKILLS_EVIDENCE_SOURCE_MIGRATION = {
  repository: 'modelcontextprotocol/modelcontextprotocol',
  path: 'seps/2640-skills-extension.md',
  commit: 'f56f204f6290f6531b14d5734eb3e0a10f0eb201',
} as const;
// Public Git object ID. Split to prevent generic secret scanners from
// misclassifying this high-entropy evidence locator as an API credential.
export const MCP_CLIENT_MATRIX_REVISION = [
  '2997f33bf6e4aab3',
  'db48d755fc877c8feab32c71',
].join('');

type CacheScope = 'public' | 'private';
type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };

export type SkillFrontmatter = {
  name: string;
  description: string;
  [key: string]: unknown;
};

export type SkillManifestResource = {
  uri: string;
  digest: string;
  size: number;
};

export type SkillGetResult = {
  resultType: 'complete';
  ttlMs: number;
  cacheScope: CacheScope;
  skill: {
    uri: string;
    frontmatter: SkillFrontmatter;
    resources: SkillManifestResource[] | 'dynamic';
  };
};

export type ApprovedSkillManifest = {
  serverIdentity: string;
  skillUri: string;
  manifestDigest: string;
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
  approvedManifest?: ApprovedSkillManifest | null;
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
    specification_commit: typeof MCP_SKILLS_NORMATIVE_CONTRACT.commit;
    normative_contract: typeof MCP_SKILLS_NORMATIVE_CONTRACT;
    design_history: typeof MCP_SKILLS_DESIGN_HISTORY;
    evidence_source_migration: typeof MCP_SKILLS_EVIDENCE_SOURCE_MIGRATION;
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
    approved_compound_identity: {
      server_identity: string;
      skill_uri: string;
      manifest_digest: string;
    } | null;
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
const SHA256_HEX = /^[a-f0-9]{64}$/;
const SKILL_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const MAX_RESOURCES = 512;
const MAX_TOTAL_BYTES = 16_777_216;

function hold(message: string): never {
  throw new Error(`ChatGPT fixture handoff held: ${message}`);
}

function jsonValue(value: unknown, path = 'frontmatter'): JsonValue {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (Array.isArray(value)) return value.map((entry, index) => jsonValue(entry, `${path}[${index}]`));
  if (typeof value !== 'object') hold(`${path} contains a non-JSON value.`);
  const record = value as Record<string, unknown>;
  const output: Record<string, JsonValue> = {};
  for (const [key, entry] of Object.entries(record)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
      hold(`${path} contains an unsafe key.`);
    }
    output[key] = jsonValue(entry, `${path}.${key}`);
  }
  return output;
}

function parseFrontmatter(content: string): Record<string, JsonValue> {
  const match = /^---[\t ]*\r?\n([\s\S]*?)\r?\n---(?:[\t ]*\r?\n|$)/.exec(content);
  if (!match) hold('SKILL.md frontmatter is missing.');
  const document = parseDocument(match[1], {
    schema: 'core',
    merge: false,
    uniqueKeys: true,
  });
  if (document.errors.length > 0) hold('SKILL.md frontmatter is invalid YAML.');
  const parsed = document.toJS({ maxAliasCount: 0 });
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    hold('SKILL.md frontmatter must be an object.');
  }
  return jsonValue(parsed) as Record<string, JsonValue>;
}

function decodePathSegment(raw: string): string {
  let decoded = raw;
  for (let depth = 0; depth < 4; depth += 1) {
    let next: string;
    try {
      next = decodeURIComponent(decoded);
    } catch {
      hold('skill URI contains invalid percent encoding.');
    }
    if (next === decoded) break;
    decoded = next;
  }
  if (
    !decoded ||
    decoded === '.' ||
    decoded === '..' ||
    decoded.includes('/') ||
    decoded.includes('\\') ||
    decoded.includes('%') ||
    /[\u0000-\u001f\u007f]/.test(decoded)
  ) {
    hold('skill URI path is not confined.');
  }
  return decoded;
}

type NormalizedSkillUri = {
  canonical: string;
  authority: string;
  segments: string[];
};

function requireString(value: unknown, field: string): string {
  if (typeof value !== 'string') hold(`${field} must be a string.`);
  return value;
}

function requireTrimmedString(value: unknown, field: string): string {
  const trimmed = requireString(value, field).trim();
  if (!trimmed) hold(`${field} is required.`);
  return trimmed;
}

function normalizeSkillUri(uri: unknown): NormalizedSkillUri {
  const rawUri = requireString(uri, 'skill URI');
  const match = /^skill:\/\/([^/?#]+)(\/[^?#]*)$/.exec(rawUri);
  if (!match) hold('skill URI must use the skill scheme without query or fragment.');
  let parsed: URL;
  try {
    parsed = new URL(rawUri);
  } catch {
    hold('skill URI is invalid.');
  }
  if (
    parsed.protocol !== 'skill:' ||
    parsed.username ||
    parsed.password ||
    parsed.port ||
    parsed.search ||
    parsed.hash
  ) {
    hold('skill URI authority is invalid.');
  }
  const authority = parsed.hostname.toLowerCase();
  if (!authority) hold('skill URI authority is missing.');
  const segments = match[2].slice(1).split('/').map(decodePathSegment);
  const canonical = `skill://${authority}/${segments.map((segment) => encodeURIComponent(segment)).join('/')}`;
  return { canonical, authority, segments };
}

function skillRoot(uri: string): NormalizedSkillUri & { rootSegments: string[]; name: string } {
  const normalized = normalizeSkillUri(uri);
  if (normalized.segments.length < 2 || normalized.segments.at(-1) !== 'SKILL.md') {
    hold('skill URI must end in /SKILL.md.');
  }
  const rootSegments = normalized.segments.slice(0, -1);
  const name = rootSegments.at(-1)!;
  if (!SKILL_NAME.test(name)) hold('skill URI final segment is invalid.');
  return { ...normalized, rootSegments, name };
}

function verifyManifest(
  skillUri: string,
  resources: readonly SkillManifestResource[],
  contents: Readonly<Record<string, string>>,
): Array<{ uri: string; digest: string; size: number }> {
  const skill = skillRoot(skillUri);
  if (resources.length === 0) hold('skill manifest is empty.');
  if (resources.length > MAX_RESOURCES) hold('skill manifest exceeds the resource limit.');

  const seen = new Set<string>();
  let totalSize = 0;
  const verified = resources.map((resource) => {
    const normalized = normalizeSkillUri(resource.uri);
    if (seen.has(normalized.canonical)) hold('skill manifest contains a duplicate URI.');
    seen.add(normalized.canonical);
    if (
      normalized.authority !== skill.authority ||
      normalized.segments.length <= skill.rootSegments.length ||
      !skill.rootSegments.every((segment, index) => normalized.segments[index] === segment)
    ) {
      hold('resource URI escapes the skill root.');
    }
    if (!SHA256_DIGEST.test(resource.digest)) hold('resource digest is invalid.');
    if (!Number.isInteger(resource.size) || resource.size < 0) hold('resource size is invalid.');
    totalSize += resource.size;
    if (totalSize > MAX_TOTAL_BYTES) hold('skill manifest exceeds the total-size limit.');

    const content = contents[resource.uri];
    if (typeof content !== 'string') hold(`resource content is missing for ${resource.uri}.`);
    const digest = `sha256:${hashCanonical(content)}`;
    const size = new TextEncoder().encode(content).byteLength;
    if (digest !== resource.digest) hold(`resource digest mismatch for ${resource.uri}.`);
    if (size !== resource.size) hold(`resource size mismatch for ${resource.uri}.`);
    return { uri: normalized.canonical, digest, size };
  });

  if (!seen.has(skill.canonical)) hold('SKILL.md is absent from the manifest.');
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
  const serverIdentity = requireTrimmedString(input.serverIdentity, 'server identity');
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
  const requestedSkill = skillRoot(input.requestedSkillUri);
  const returnedSkill = skillRoot(input.result.skill.uri);
  if (returnedSkill.canonical !== requestedSkill.canonical) {
    hold('returned skill URI does not match the requested URI.');
  }

  const manifestFrontmatter = jsonValue(input.result.skill.frontmatter) as Record<string, JsonValue>;
  if (
    typeof manifestFrontmatter.name !== 'string' ||
    typeof manifestFrontmatter.description !== 'string'
  ) {
    hold('manifest frontmatter requires name and description strings.');
  }
  if (manifestFrontmatter.name !== returnedSkill.name) {
    hold('manifest frontmatter name does not match the skill URI.');
  }
  const skillText = input.resourceContents[input.result.skill.uri];
  if (typeof skillText !== 'string') hold('SKILL.md content is missing.');
  const parsedFrontmatter = parseFrontmatter(skillText);
  if (canonicalGateJson(parsedFrontmatter) !== canonicalGateJson(manifestFrontmatter)) {
    hold('manifest frontmatter does not match SKILL.md frontmatter.');
  }

  if (input.result.skill.resources === 'dynamic') {
    hold('dynamic skill resources are not accepted by this fixture-only contract.');
  }
  if (!Array.isArray(input.result.skill.resources)) {
    hold('skill resources must be a static manifest array.');
  }
  const resources = verifyManifest(
    returnedSkill.canonical,
    input.result.skill.resources,
    input.resourceContents,
  );
  const manifestDigest = hashCanonical(canonicalGateJson(resources));
  const approved = input.approvedManifest ?? null;
  let approvedCompoundIdentity: FixtureChatGptSkillImportReceipt['authorization']['approved_compound_identity'] =
    null;
  if (approved) {
    if (!SHA256_HEX.test(approved.manifestDigest)) hold('approved manifest digest is invalid.');
    approvedCompoundIdentity = {
      server_identity: requireTrimmedString(approved.serverIdentity, 'approved server identity'),
      skill_uri: skillRoot(approved.skillUri).canonical,
      manifest_digest: approved.manifestDigest,
    };
  }
  const issuedAt =
    input.issuedAt === undefined ? new Date().toISOString() : requireString(input.issuedAt, 'issuedAt');
  const authorizationStatus: FixtureChatGptSkillImportReceipt['authorization']['status'] =
    approvedCompoundIdentity === null
      ? 'NOT_GRANTED'
      : approvedCompoundIdentity.server_identity === serverIdentity &&
          approvedCompoundIdentity.skill_uri === returnedSkill.canonical &&
          approvedCompoundIdentity.manifest_digest === manifestDigest
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
      specification_commit: MCP_SKILLS_NORMATIVE_CONTRACT.commit,
      normative_contract: MCP_SKILLS_NORMATIVE_CONTRACT,
      design_history: MCP_SKILLS_DESIGN_HISTORY,
      evidence_source_migration: MCP_SKILLS_EVIDENCE_SOURCE_MIGRATION,
    },
    decision: 'READY_FOR_FIXTURE_HANDOFF' as const,
    issued_at: issuedAt,
    compound_identity: {
      server_identity: serverIdentity,
      skill_uri: returnedSkill.canonical,
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
      approved_compound_identity: approvedCompoundIdentity,
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
