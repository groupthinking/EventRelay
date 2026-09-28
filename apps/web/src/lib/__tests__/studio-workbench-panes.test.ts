import { describe, expect, it } from 'vitest';
import {
  countTranscriptWords,
  studioDedupeSopStepsAgainstEvents,
  studioOutlineSectionToPane,
  studioResolveActivePane,
  studioSummaryIsRedundant,
  studioTranscriptSummaryLabel,
  studioWorkbenchTabs,
  type StudioWorkbenchContent,
} from '../studio-workbench-panes';

const EMPTY: StudioWorkbenchContent = {
  hasTranscript: false,
  hasActions: false,
  hasEvents: false,
  hasWorkflow: false,
  hasSpec: false,
  hasSummary: false,
  hasPack: false,
};

describe('studioWorkbenchTabs', () => {
  it('always starts with Video as the default pane and nothing stacked', () => {
    const tabs = studioWorkbenchTabs(EMPTY);
    expect(tabs.map((tab) => tab.id)).toEqual(['video']);
  });

  it('adds one tab per available surface, never stacking into one pane', () => {
    const tabs = studioWorkbenchTabs({
      hasTranscript: true,
      hasActions: true,
      hasEvents: true,
      hasWorkflow: true,
      hasSpec: true,
      hasSummary: true,
      hasPack: true,
    });
    expect(tabs.map((tab) => tab.id)).toEqual([
      'video',
      'transcript',
      'actions',
      'events',
      'workflow',
      'spec',
      'summary',
      'pack',
    ]);
  });

  it('omits surfaces without content', () => {
    const tabs = studioWorkbenchTabs({ ...EMPTY, hasTranscript: true, hasPack: true });
    expect(tabs.map((tab) => tab.id)).toEqual(['video', 'transcript', 'pack']);
  });
});

describe('studioResolveActivePane', () => {
  it('keeps the requested pane when it still has a tab', () => {
    const tabs = studioWorkbenchTabs({ ...EMPTY, hasTranscript: true });
    expect(studioResolveActivePane('transcript', tabs)).toBe('transcript');
  });

  it('falls back to Video (first tab) when the request is missing or gone', () => {
    const tabs = studioWorkbenchTabs({ ...EMPTY, hasPack: true });
    expect(studioResolveActivePane('events', tabs)).toBe('video');
    expect(studioResolveActivePane(null, tabs)).toBe('video');
  });
});

describe('studioOutlineSectionToPane', () => {
  it('maps outline section ids to panes', () => {
    expect(studioOutlineSectionToPane('studio-shell-video')).toBe('video');
    expect(studioOutlineSectionToPane('studio-shell-transcript')).toBe('transcript');
    expect(studioOutlineSectionToPane('studio-shell-result')).toBe('spec');
    expect(studioOutlineSectionToPane('studio-shell-pack')).toBe('pack');
    expect(studioOutlineSectionToPane('studio-shell-sop')).toBe('workflow');
    expect(studioOutlineSectionToPane('studio-shell-chapter-3')).toBe('video');
    expect(studioOutlineSectionToPane('unknown')).toBeNull();
  });
});

describe('studioTranscriptSummaryLabel', () => {
  it('summarizes a ready transcript with a word count instead of the full body', () => {
    const transcript = Array.from({ length: 1280 }, (_, i) => `word${i}`).join(' ');
    expect(studioTranscriptSummaryLabel({ transcript, stageLabel: 'Transcript ready' })).toBe(
      '1280 words · Transcript ready',
    );
  });

  it('falls back to the live stage label when no transcript exists yet', () => {
    expect(studioTranscriptSummaryLabel({ transcript: '', stageLabel: 'Building transcript' })).toBe(
      'Building transcript',
    );
  });

  it('counts words robustly', () => {
    expect(countTranscriptWords('  one   two\nthree ')).toBe(3);
    expect(countTranscriptWords('')).toBe(0);
    expect(countTranscriptWords(null)).toBe(0);
  });
});

describe('studioDedupeSopStepsAgainstEvents', () => {
  it('drops SOP steps whose titles duplicate an event title', () => {
    const events = [{ title: 'Change the tire' }, { title: 'Torque the lug nuts' }];
    const sop = [
      { title: 'change the tire' },
      { title: 'Lower the jack' },
      { title: '  Torque the Lug Nuts  ' },
    ];
    expect(studioDedupeSopStepsAgainstEvents(events, sop).map((s) => s.title)).toEqual([
      'Lower the jack',
    ]);
  });

  it('keeps SOP steps when there are no events', () => {
    const sop = [{ title: 'a' }, { title: 'b' }];
    expect(studioDedupeSopStepsAgainstEvents([], sop)).toHaveLength(2);
  });
});

describe('studioSummaryIsRedundant', () => {
  it('flags a summary that only echoes the listed titles', () => {
    expect(studioSummaryIsRedundant('Change the tire', ['Change the tire'])).toBe(true);
    expect(
      studioSummaryIsRedundant('Change the tire Lower the jack', [
        'Change the tire',
        'Lower the jack',
      ]),
    ).toBe(true);
  });

  it('keeps a summary that adds prose beyond the list', () => {
    expect(
      studioSummaryIsRedundant('A concise walkthrough of a roadside tire change with safety notes.', [
        'Change the tire',
        'Lower the jack',
      ]),
    ).toBe(false);
  });

  it('treats an empty summary as redundant and a summary with no titles as kept', () => {
    expect(studioSummaryIsRedundant('', ['x'])).toBe(true);
    expect(studioSummaryIsRedundant('Anything', [])).toBe(false);
  });
});
