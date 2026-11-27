import { describe, expect, it } from 'vitest';
import {
  STUDIO_ACTIVITY_MODES,
  studioActivityForOutputSection,
  studioContextSurfaceForActivity,
  studioOutputSectionForActivity,
} from '../studio-ia-modes';

describe('Cut 4 IA rename — activity ↔ deliverable wiring', () => {
  it('exposes Video · Agents · Tools · Files · Canvas · Code only (no persona mode)', () => {
    expect([...STUDIO_ACTIVITY_MODES]).toEqual([
      'video',
      'agents',
      'tools',
      'files',
      'canvas',
      'code',
    ]);
    expect(STUDIO_ACTIVITY_MODES).not.toContain('persona');
    expect(STUDIO_ACTIVITY_MODES).not.toContain('hire');
  });

  it('maps Tools / Files / Canvas / Code onto the four deliverable tabs', () => {
    expect(studioOutputSectionForActivity('tools')).toBe('tasks');
    expect(studioOutputSectionForActivity('files')).toBe('transcript');
    expect(studioOutputSectionForActivity('canvas')).toBe('preview');
    expect(studioOutputSectionForActivity('code')).toBe('code');
  });

  it('keeps Video / Agents on the chat surface (no deliverable tab)', () => {
    expect(studioOutputSectionForActivity('video')).toBeNull();
    expect(studioOutputSectionForActivity('agents')).toBeNull();
    expect(studioContextSurfaceForActivity('video')).toBe('agents');
    expect(studioContextSurfaceForActivity('agents')).toBe('agents');
    expect(studioContextSurfaceForActivity('tools')).toBe('output');
    expect(studioContextSurfaceForActivity('files')).toBe('output');
    expect(studioContextSurfaceForActivity('canvas')).toBe('output');
    expect(studioContextSurfaceForActivity('code')).toBe('output');
  });

  it('maps deliverable tabs back onto Tools / Files / Canvas / Code activity', () => {
    expect(studioActivityForOutputSection('tasks')).toBe('tools');
    expect(studioActivityForOutputSection('transcript')).toBe('files');
    expect(studioActivityForOutputSection('preview')).toBe('canvas');
    expect(studioActivityForOutputSection('code')).toBe('code');
  });

  it('grounds Labels to live Studio panes (chat / output / export / spec)', () => {
    // Agents → StudioIdeChat; Tools → Tasks & Tools; Files → Transcript (+ toolbar export);
    // Canvas → Preview; Code → Code & Spec. Fixture id remains auJzb1D-fag in callers.
    expect(studioOutputSectionForActivity('tools')).toBe('tasks');
    expect(studioOutputSectionForActivity('files')).toBe('transcript');
    expect(studioOutputSectionForActivity('canvas')).toBe('preview');
    expect(studioOutputSectionForActivity('code')).toBe('code');
    expect(studioContextSurfaceForActivity('agents')).toBe('agents');
  });
});
