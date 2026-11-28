import { describe, expect, it } from 'vitest';
import {
  studioActivityForOutputSection,
  studioOutputSectionForActivity,
} from '../studio-ia-modes';

describe('Cut 4 IA rename — activity ↔ deliverable wiring', () => {
  it('maps Tools / Files / Canvas / Code onto the four deliverable tabs', () => {
    expect(studioOutputSectionForActivity('tools')).toBe('tasks');
    expect(studioOutputSectionForActivity('files')).toBe('transcript');
    expect(studioOutputSectionForActivity('canvas')).toBe('preview');
    expect(studioOutputSectionForActivity('code')).toBe('code');
  });

  it('keeps Video / Agents off a deliverable tab', () => {
    expect(studioOutputSectionForActivity('video')).toBeNull();
    expect(studioOutputSectionForActivity('agents')).toBeNull();
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
  });
});
