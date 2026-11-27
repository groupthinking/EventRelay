import 'server-only';

import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { z } from 'zod';
import { StudioError } from '@/lib/studio/errors';
import type { StudioOwner } from '@/lib/studio/security';
import { identityHash } from '@/lib/video-pack';
import { canonicalYouTubeSource, resolveYouTubeSourceId } from '@/lib/video-source-identity';
import {
  PROJECT_VISIBILITIES,
  defaultProjectTitle,
  type ProjectRecord,
} from './project-types';

const rowSchema = z.object({
  id: z.uuid(),
  owner_subject: z.string().min(1).max(512),
  source_hash: z.string().regex(/^[a-f0-9]{64}$/),
  source_url: z.string().min(1).max(512),
  title: z.string().min(1).max(160),
  visibility: z.enum(PROJECT_VISIBILITIES),
  created_at: z.iso.datetime({ offset: true }),
  updated_at: z.iso.datetime({ offset: true }),
});

type ProjectRow = z.infer<typeof rowSchema>;
type ProjectDatabase = {
  public: {
    Tables: {
      projects: {
        Row: ProjectRow;
        Insert: Pick<ProjectRow, 'owner_subject' | 'source_hash' | 'source_url' | 'title'> &
          Partial<Omit<ProjectRow, 'owner_subject' | 'source_hash' | 'source_url' | 'title'>>;
        Update: Partial<ProjectRow>;
        Relationships: [];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
  };
};

export const createProjectSchema = z
  .object({
    sourceUrl: z.string().trim().min(1).max(512),
    title: z.string().trim().min(1).max(160).optional(),
    visibility: z.enum(PROJECT_VISIBILITIES).default('private'),
  })
  .strict();

export const updateProjectSchema = z
  .object({
    title: z.string().trim().min(1).max(160).optional(),
    visibility: z.enum(PROJECT_VISIBILITIES).optional(),
  })
  .strict()
  .refine((value) => value.title !== undefined || value.visibility !== undefined);

const columns = 'id,owner_subject,source_hash,source_url,title,visibility,created_at,updated_at';
let cachedClient: { url: string; key: string; client: SupabaseClient<ProjectDatabase> } | undefined;

function unavailable(): StudioError {
  return new StudioError(503, 'projects_unavailable', 'Project storage is unavailable.');
}

function clientForOwner(owner: StudioOwner): SupabaseClient<ProjectDatabase> {
  if (!owner.subject?.trim() || owner.subject.length > 512) {
    throw new StudioError(401, 'authentication_required', 'Sign in to manage projects.');
  }
  const url = (process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL)?.trim();
  const key = (process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY)?.trim();
  if (!url || !key) throw unavailable();
  if (cachedClient?.url === url && cachedClient.key === key) return cachedClient.client;

  try {
    const endpoint = new URL(url);
    if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password) throw unavailable();
    const client = createClient<ProjectDatabase>(url, key, {
      auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false },
      global: {
        fetch: (input, init) =>
          fetch(input, {
            ...init,
            cache: 'no-store',
            signal: init?.signal
              ? AbortSignal.any([init.signal, AbortSignal.timeout(10_000)])
              : AbortSignal.timeout(10_000),
          }),
      },
    });
    cachedClient = { url, key, client };
    return client;
  } catch {
    throw unavailable();
  }
}

function validateId(id: string): void {
  if (!z.uuid().safeParse(id).success) {
    throw new StudioError(400, 'invalid_project_id', 'Invalid project identifier.');
  }
}

function projectFromRow(data: unknown, owner: StudioOwner): ProjectRecord {
  const parsed = rowSchema.safeParse(data);
  if (!parsed.success || parsed.data.owner_subject !== owner.subject) throw unavailable();
  const row = parsed.data;
  const videoId = resolveYouTubeSourceId(row.source_url);
  if (!videoId) throw unavailable();
  return {
    id: row.id,
    sourceHash: row.source_hash,
    sourceUrl: row.source_url,
    videoId,
    title: row.title,
    visibility: row.visibility,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    storage: 'remote',
  };
}

/** Resolve a pasted URL into the canonical single-source identity. */
export function resolveProjectSource(rawUrl: string): {
  videoId: string;
  sourceUrl: string;
  sourceHash: string;
} {
  const videoId = resolveYouTubeSourceId(rawUrl);
  if (!videoId) throw new StudioError(400, 'invalid_source_url', 'Enter a valid YouTube video URL.');
  return { videoId, sourceUrl: canonicalYouTubeSource(videoId), sourceHash: identityHash(videoId) };
}

export async function listProjects(owner: StudioOwner): Promise<ProjectRecord[]> {
  const { data, error } = await clientForOwner(owner)
    .from('projects')
    .select(columns)
    .eq('owner_subject', owner.subject)
    .order('updated_at', { ascending: false })
    .order('id', { ascending: false })
    .limit(100);
  if (error || !Array.isArray(data)) throw unavailable();
  return data.map((row) => projectFromRow(row, owner));
}

export async function getProject(owner: StudioOwner, projectId: string): Promise<ProjectRecord> {
  validateId(projectId);
  const { data, error } = await clientForOwner(owner)
    .from('projects')
    .select(columns)
    .eq('owner_subject', owner.subject)
    .eq('id', projectId)
    .maybeSingle();
  if (error) throw unavailable();
  if (!data) throw new StudioError(404, 'project_not_found', 'Project not found.');
  const project = projectFromRow(data, owner);
  if (project.id !== projectId) throw unavailable();
  return project;
}

export async function createOrFindProject(
  owner: StudioOwner,
  input: z.input<typeof createProjectSchema>,
): Promise<{ project: ProjectRecord; created: boolean }> {
  const parsed = createProjectSchema.safeParse(input);
  if (!parsed.success) throw new StudioError(400, 'invalid_request', 'Invalid project request.');
  const source = resolveProjectSource(parsed.data.sourceUrl);
  const client = clientForOwner(owner);
  const { data, error } = await client
    .from('projects')
    .insert({
      owner_subject: owner.subject,
      source_hash: source.sourceHash,
      source_url: source.sourceUrl,
      title: parsed.data.title ?? defaultProjectTitle(source.videoId),
      visibility: parsed.data.visibility,
    })
    .select(columns)
    .single();

  if (!error && data) {
    const project = projectFromRow(data, owner);
    if (project.sourceHash !== source.sourceHash) throw unavailable();
    return { project, created: true };
  }
  if (error?.code !== '23505') throw unavailable();

  // The (owner_subject, source_hash) constraint arbitrates duplicates: return the existing row.
  const existing = await client
    .from('projects')
    .select(columns)
    .eq('owner_subject', owner.subject)
    .eq('source_hash', source.sourceHash)
    .maybeSingle();
  if (existing.error || !existing.data) throw unavailable();
  const project = projectFromRow(existing.data, owner);
  if (project.sourceHash !== source.sourceHash) throw unavailable();
  return { project, created: false };
}

export async function updateProject(
  owner: StudioOwner,
  projectId: string,
  input: z.input<typeof updateProjectSchema>,
): Promise<ProjectRecord> {
  validateId(projectId);
  const parsed = updateProjectSchema.safeParse(input);
  if (!parsed.success) throw new StudioError(400, 'invalid_request', 'Invalid project update.');
  const { data, error } = await clientForOwner(owner)
    .from('projects')
    .update({ ...parsed.data, updated_at: new Date().toISOString() })
    .eq('owner_subject', owner.subject)
    .eq('id', projectId)
    .select(columns)
    .maybeSingle();
  if (error) throw unavailable();
  if (!data) throw new StudioError(404, 'project_not_found', 'Project not found.');
  const project = projectFromRow(data, owner);
  if (project.id !== projectId) throw unavailable();
  return project;
}

export async function deleteProject(owner: StudioOwner, projectId: string): Promise<void> {
  validateId(projectId);
  const { data, error } = await clientForOwner(owner)
    .from('projects')
    .delete()
    .eq('owner_subject', owner.subject)
    .eq('id', projectId)
    .select('id')
    .maybeSingle();
  if (error) throw unavailable();
  if (!data) throw new StudioError(404, 'project_not_found', 'Project not found.');
}
