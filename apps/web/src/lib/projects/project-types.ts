/** Client- and server-safe Project types. Never carries `owner_subject`. */
export const PROJECT_VISIBILITIES = ['private', 'shared'] as const;
export type ProjectVisibility = (typeof PROJECT_VISIBILITIES)[number];

export interface ProjectRecord {
  id: string;
  /** 64-char Video Pack hash; empty for guest (local) projects until synced. */
  sourceHash: string;
  sourceUrl: string;
  videoId: string;
  title: string;
  visibility: ProjectVisibility;
  createdAt: string;
  updatedAt: string;
  storage: 'remote' | 'local';
}

export function defaultProjectTitle(videoId: string): string {
  return `YouTube Video (${videoId})`;
}
