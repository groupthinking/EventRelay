// @vitest-environment jsdom
/**
 * Cut 4 exit checks: activity modes wire to chat / four deliverable tabs;
 * no persona grid; fixture id auJzb1D-fag only in copy.
 */
import React, { useState } from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import StudioIdeShell from '@/components/studio/StudioIdeShell';
import StudioIdeOutput, { type OutputSection } from '@/components/studio/StudioIdeOutput';
import {
  studioActivityForOutputSection,
  studioOutputSectionForActivity,
  type StudioActivityMode,
} from '@/lib/studio-ia-modes';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function Cut4Harness() {
  const [activityMode, setActivityMode] = useState<StudioActivityMode>('video');
  const [outputSection, setOutputSection] = useState<OutputSection>('tasks');

  return (
    <StudioIdeShell
      activityMode={activityMode}
      onActivityChange={(mode) => {
        setActivityMode(mode);
        const section = studioOutputSectionForActivity(mode);
        if (section) setOutputSection(section);
      }}
      toolbar={<span>auJzb1D-fag</span>}
      videoPane={<div data-testid="fixture-player">auJzb1D-fag</div>}
      chatPane={<p data-testid="agents-chat">Agents stream</p>}
      outputPane={
        <StudioIdeOutput
          video={undefined}
          activeSection={outputSection}
          onSectionChange={(section) => {
            setOutputSection(section);
            setActivityMode(studioActivityForOutputSection(section));
          }}
        />
      }
    />
  );
}

describe('Cut 4 IA rename wiring', () => {
  it('wires Tools / Files / Canvas / Code to the four deliverable tabs', () => {
    vi.stubGlobal('React', React);
    render(<Cut4Harness />);

    const cases: Array<{ mode: StudioActivityMode; section: OutputSection }> = [
      { mode: 'tools', section: 'tasks' },
      { mode: 'files', section: 'transcript' },
      { mode: 'canvas', section: 'preview' },
      { mode: 'code', section: 'code' },
    ];

    for (const { mode, section } of cases) {
      fireEvent.click(screen.getByTestId(`studio-activity-${mode}`));
      expect(screen.getByTestId('studio-ide-shell').dataset.activity).toBe(mode);
      expect(screen.getByTestId('studio-ide-output-pane').hasAttribute('hidden')).toBe(false);
      expect(screen.getByTestId('studio-ide-chat-pane').hasAttribute('hidden')).toBe(true);
      expect(screen.getByTestId(`studio-ide-output-tab-${section}`).getAttribute('aria-selected')).toBe(
        'true',
      );
      expect(screen.getByTestId(`studio-ide-output-${section}`)).toBeTruthy();
    }
  });

  it('keeps Agents on chat and never renders a persona / hire grid', () => {
    vi.stubGlobal('React', React);
    render(<Cut4Harness />);

    fireEvent.click(screen.getByTestId('studio-activity-tools'));
    fireEvent.click(screen.getByTestId('studio-activity-agents'));

    expect(screen.getByTestId('studio-ide-shell').dataset.activity).toBe('agents');
    expect(screen.getByTestId('studio-ide-chat-pane').hasAttribute('hidden')).toBe(false);
    expect(screen.getByTestId('studio-ide-output-pane').hasAttribute('hidden')).toBe(true);
    expect(screen.getByTestId('agents-chat')).toBeTruthy();
    expect(screen.queryByText(/HIRE/i)).toBeNull();
    expect(screen.queryByRole('button', { name: /hire/i })).toBeNull();
    expect(screen.queryByText(/persona/i)).toBeNull();
  });

  it('syncs deliverable tab clicks back onto the matching activity mode', () => {
    vi.stubGlobal('React', React);
    render(<Cut4Harness />);

    fireEvent.click(screen.getByTestId('studio-activity-tools'));
    fireEvent.click(screen.getByTestId('studio-ide-output-tab-preview'));
    expect(screen.getByTestId('studio-ide-shell').dataset.activity).toBe('canvas');
    expect(screen.getByTestId('studio-ide-output-tab-preview').getAttribute('aria-selected')).toBe(
      'true',
    );

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-transcript'));
    expect(screen.getByTestId('studio-ide-shell').dataset.activity).toBe('files');

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-code'));
    expect(screen.getByTestId('studio-ide-shell').dataset.activity).toBe('code');

    fireEvent.click(screen.getByTestId('studio-ide-output-tab-tasks'));
    expect(screen.getByTestId('studio-ide-shell').dataset.activity).toBe('tools');
  });

  it('keeps the stage fixture player mounted while switching IA modes', () => {
    vi.stubGlobal('React', React);
    render(<Cut4Harness />);

    for (const mode of ['agents', 'tools', 'files', 'canvas', 'code', 'video'] as const) {
      fireEvent.click(screen.getByTestId(`studio-activity-${mode}`));
      expect(screen.getByTestId('fixture-player').textContent).toBe('auJzb1D-fag');
    }
  });
});
