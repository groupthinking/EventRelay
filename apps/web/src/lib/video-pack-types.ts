import { z } from 'zod';

/** Hard cap so Gemini cannot persist a chat code dump on the pack. */
export const VIDEO_PACK_SNIPPET_MAX = 800;

export interface VideoPackArchitectureStage {
  id: string;
  name: string;
  description?: string | null;
}

export interface VideoPackArchitecture {
  summary?: string | null;
  stages: VideoPackArchitectureStage[];
  mermaid?: string | null;
}

export interface VideoPackArtifact {
  path_hint: string;
  purpose: string;
  interface: string;
  signatures?: string[];
  stubs?: string[];
}

export interface VideoPackStackTool {
  name: string;
  kind?: string | null;
  evidence?: string | null;
  docs_url?: string | null;
  check?: string | null;
}

export interface VideoPackStack {
  tools: VideoPackStackTool[];
}

export const architectureStageSchema = z.object({
  id: z.string().optional(),
  name: z.string().trim().min(1),
  description: z.string().nullable().optional(),
});

export const architectureSchema = z.object({
  summary: z.string().nullable().optional(),
  stages: z.array(architectureStageSchema).optional(),
  mermaid: z.string().nullable().optional(),
});

export const artifactSchema = z.object({
  path_hint: z.string().trim().min(1),
  purpose: z.string().trim().min(1),
  interface: z.string().trim().min(1),
  signatures: z.array(z.string()).optional(),
  stubs: z.array(z.string()).optional(),
});

export const stackToolSchema = z.object({
  name: z.string().trim().min(1),
  kind: z.string().nullable().optional(),
  evidence: z.string().nullable().optional(),
  docs_url: z.string().nullable().optional(),
  check: z.string().nullable().optional(),
});

export const stackSchema = z.object({
  tools: z.array(stackToolSchema).optional(),
});

export function truncatePackText(value: string, max: number = VIDEO_PACK_SNIPPET_MAX): string {
  return value.length <= max ? value : value.slice(0, max);
}

/** One shared 800-char budget across a snippet list (not 800 per line). */
export function compactPackSnippets(
  values: readonly string[] | undefined,
  max: number = VIDEO_PACK_SNIPPET_MAX,
): string[] | undefined {
  if (!values?.length) return undefined;
  const kept: string[] = [];
  let used = 0;
  for (const raw of values) {
    const snippet = raw.trim();
    if (!snippet) continue;
    const remaining = max - used;
    if (remaining <= 0) break;
    const clipped = snippet.length <= remaining ? snippet : snippet.slice(0, remaining);
    if (!clipped) continue;
    kept.push(clipped);
    used += clipped.length;
  }
  return kept.length > 0 ? kept : undefined;
}

export function parseArchitecture(value: unknown): VideoPackArchitecture | null {
  const parsed = architectureSchema.safeParse(value);
  if (!parsed.success) return null;
  const stages = (parsed.data.stages ?? []).flatMap((stage, index) => {
    const name = stage.name.trim();
    if (!name) return [];
    return [
      {
        id: stage.id?.trim() || `stage-${index + 1}`,
        name,
        description: stage.description?.trim() || null,
      },
    ];
  });
  const summary = parsed.data.summary?.trim() || null;
  const mermaid = parsed.data.mermaid ? truncatePackText(parsed.data.mermaid, 2_000) : null;
  if (!summary && stages.length === 0 && !mermaid) return null;
  return { summary, stages, mermaid };
}

export function parseArtifacts(value: unknown): VideoPackArtifact[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const parsed = artifactSchema.safeParse(item);
    if (!parsed.success) return [];
    const pathHint = parsed.data.path_hint.trim();
    const purpose = parsed.data.purpose.trim();
    const iface = truncatePackText(parsed.data.interface.trim());
    if (!pathHint || !purpose || !iface) return [];
    const signatures = compactPackSnippets(parsed.data.signatures);
    const stubsJoined = parsed.data.stubs
      ?.map((line) => line.trim())
      .filter(Boolean)
      .join('\n');
    const stubs = stubsJoined ? [truncatePackText(stubsJoined)].filter((line) => line.length > 0) : undefined;
    return [
      {
        path_hint: pathHint,
        purpose,
        interface: iface,
        ...(signatures ? { signatures } : {}),
        ...(stubs?.length ? { stubs } : {}),
      },
    ];
  });
}

export function parseStack(value: unknown): VideoPackStack {
  const parsed = stackSchema.safeParse(value);
  if (!parsed.success) return { tools: [] };
  const tools = (parsed.data.tools ?? []).flatMap((tool) => {
    const name = tool.name.trim();
    if (!name) return [];
    return [
      {
        name,
        kind: tool.kind?.trim() || null,
        evidence: tool.evidence?.trim() || null,
        check: tool.check?.trim() || null,
      },
    ];
  });
  return { tools };
}

export function readPackFormation(data: Record<string, unknown>): {
  architecture: VideoPackArchitecture | null;
  artifacts: VideoPackArtifact[];
  stack: VideoPackStack;
} {
  return {
    architecture: parseArchitecture(data.architecture),
    artifacts: parseArtifacts(data.artifacts),
    stack: parseStack(data.stack),
  };
}

export function emptyPackFormation(): {
  architecture: VideoPackArchitecture | null;
  artifacts: VideoPackArtifact[];
  stack: VideoPackStack;
} {
  return { architecture: null, artifacts: [], stack: { tools: [] } };
}
