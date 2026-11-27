export type StudioActivityMode = 'video' | 'agents' | 'tools' | 'files' | 'canvas' | 'code';

export type StudioOutputSection = 'preview' | 'tasks' | 'code' | 'transcript';

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
