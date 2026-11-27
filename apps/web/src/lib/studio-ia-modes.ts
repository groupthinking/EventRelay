/**
 * Cut 4 — IA rename pass.
 *
 * Maps Hybrid D activity-rail modes (Agents / Tools / Files / Canvas / Code)
 * onto the existing Studio chat + four deliverable tabs. Pure helpers only —
 * no React, no mock pack content.
 */

export const STUDIO_ACTIVITY_MODES = [
  'video',
  'agents',
  'tools',
  'files',
  'canvas',
  'code',
] as const;

export type StudioActivityMode = (typeof STUDIO_ACTIVITY_MODES)[number];

export type StudioOutputSection = 'preview' | 'tasks' | 'code' | 'transcript';

export type StudioContextSurface = 'agents' | 'output';

/** Deliverable tab focused by a Tools / Files / Canvas / Code activity click. */
export function studioOutputSectionForActivity(
  mode: StudioActivityMode,
): StudioOutputSection | null {
  switch (mode) {
    case 'tools':
      return 'tasks';
    case 'files':
      return 'transcript';
    case 'canvas':
      return 'preview';
    case 'code':
      return 'code';
    case 'video':
    case 'agents':
      return null;
    default: {
      const _exhaustive: never = mode;
      return _exhaustive;
    }
  }
}

/** Context rail surface for an activity mode (Agents chat vs deliverables). */
export function studioContextSurfaceForActivity(mode: StudioActivityMode): StudioContextSurface {
  switch (mode) {
    case 'video':
    case 'agents':
      return 'agents';
    case 'tools':
    case 'files':
    case 'canvas':
    case 'code':
      return 'output';
    default: {
      const _exhaustive: never = mode;
      return _exhaustive;
    }
  }
}

/** Activity mode to select when the user picks a deliverable tab. */
export function studioActivityForOutputSection(section: StudioOutputSection): StudioActivityMode {
  switch (section) {
    case 'tasks':
      return 'tools';
    case 'transcript':
      return 'files';
    case 'preview':
      return 'canvas';
    case 'code':
      return 'code';
    default: {
      const _exhaustive: never = section;
      return _exhaustive;
    }
  }
}
