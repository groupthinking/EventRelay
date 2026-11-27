// @vitest-environment jsdom
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import StudioIdeShell from '@/components/studio/StudioIdeShell';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('Hybrid D Studio stage shell (Cut 1)', () => {
  it('renders activity rail, dominant stage, and Agents context by default', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={<span>Run controls</span>}
        videoPane={<p>Source evidence</p>}
        chatPane={<input aria-label="Draft" defaultValue="" />}
        outputPane={<p>Deliverables</p>}
      />,
    );

    expect(screen.getByTestId('studio-ide-shell').dataset.shell).toBe('hybrid-d');
    expect(screen.getByTestId('studio-activity-rail')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-video-pane')).toBeTruthy();
    expect(screen.getByTestId('studio-context-rail')).toBeTruthy();
    expect(screen.getByTestId('studio-ide-chat-pane').hasAttribute('hidden')).toBe(false);
    expect(screen.getByTestId('studio-ide-output-pane').hasAttribute('hidden')).toBe(true);
    expect(screen.getByTestId('studio-activity-video').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('studio-stage-plane').textContent).toMatch(/proposed/i);
  });

  it('switches activity modes between Agents chat and Tools output without losing draft', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={<span>Run controls</span>}
        videoPane={<p>Source evidence</p>}
        chatPane={<input aria-label="Draft" defaultValue="" />}
        outputPane={<p>Deliverables</p>}
      />,
    );
    fireEvent.change(screen.getByLabelText('Draft'), {
      target: { value: 'Which step is unclear?' },
    });
    fireEvent.click(screen.getByTestId('studio-activity-tools'));
    expect(screen.getByTestId('studio-ide-shell').dataset.activity).toBe('tools');
    expect(screen.getByTestId('studio-ide-output-pane').hasAttribute('hidden')).toBe(false);
    expect(screen.getByTestId('studio-ide-chat-pane').hasAttribute('hidden')).toBe(true);

    fireEvent.click(screen.getByTestId('studio-activity-agents'));
    expect(screen.getByTestId('studio-ide-shell').dataset.activity).toBe('agents');
    expect((screen.getByLabelText('Draft') as HTMLInputElement).value).toBe(
      'Which step is unclear?',
    );
  });

  it('collapses and restores the context rail', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={null}
        videoPane={<p>Source</p>}
        chatPane={<p>Chat</p>}
        outputPane={<p>Files</p>}
      />,
    );
    fireEvent.click(screen.getByTestId('studio-context-collapse'));
    expect(screen.getByTestId('studio-ide-shell').dataset.contextCollapsed).toBe('true');
    expect(screen.getByTestId('studio-context-rail').dataset.collapsed).toBe('true');
    fireEvent.click(screen.getByTestId('studio-context-restore'));
    expect(screen.getByTestId('studio-ide-shell').dataset.contextCollapsed).toBeUndefined();
  });

  it('switches source/chat/output mobile tabs with keyboard', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={null}
        videoPane={<p>Source</p>}
        chatPane={<p>Chat</p>}
        outputPane={<p>Files</p>}
      />,
    );
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Source' }), { key: 'ArrowRight' });
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('chat');
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'Conversation' }));
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Conversation' }), { key: 'End' });
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('output');
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Deliverables' }), { key: 'Home' });
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('video');
  });

  it('keeps one main landmark containing stage and context panels', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={null}
        videoPane={<p>Source</p>}
        chatPane={<p>Chat</p>}
        outputPane={<p>Files</p>}
      />,
    );

    const main = screen.getByRole('main');
    expect(screen.getAllByRole('main')).toHaveLength(1);
    expect(main.contains(screen.getByTestId('studio-ide-video-pane'))).toBe(true);
    expect(main.contains(screen.getByTestId('studio-activity-rail'))).toBe(true);
    expect(main.contains(screen.getByTestId('studio-context-rail'))).toBe(true);
  });

  it('omits vertical drag splitters in the stage shell', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={<span>Controls</span>}
        videoPane={<p>Source</p>}
        chatPane={<p>Chat</p>}
        outputPane={<p>Files</p>}
        detailsRail={<p>Rail metadata</p>}
      />,
    );
    expect(screen.queryByTestId('studio-ide-splitter-left')).toBeNull();
    expect(screen.queryByTestId('studio-ide-splitter-right')).toBeNull();
    expect(screen.getByTestId('studio-ide-details-rail')).toBeTruthy();
    expect(screen.getByRole('main').dataset.detailsRail).toBe('true');
  });

  it('supports controlled mobilePane and activityMode callbacks', () => {
    vi.stubGlobal('React', React);
    const onMobilePaneChange = vi.fn();
    const onActivityModeChange = vi.fn();
    render(
      <StudioIdeShell
        toolbar={null}
        videoPane={<p>Source</p>}
        chatPane={<p>Chat</p>}
        outputPane={<p>Files</p>}
        mobilePane="video"
        activityMode="video"
        onMobilePaneChange={onMobilePaneChange}
        onActivityModeChange={onActivityModeChange}
      />,
    );
    fireEvent.click(screen.getByTestId('studio-activity-code'));
    expect(onActivityModeChange).toHaveBeenCalledWith('code');
    expect(onMobilePaneChange).toHaveBeenCalledWith('output');
  });

  it('reveals Deliverables when mobilePane is output without activityMode', () => {
    vi.stubGlobal('React', React);
    render(
      <StudioIdeShell
        toolbar={null}
        videoPane={<p>Source</p>}
        chatPane={<p>Chat</p>}
        outputPane={<p>Deliverables body</p>}
        mobilePane="output"
      />,
    );

    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('output');
    expect(screen.getByTestId('studio-ide-output-pane').hasAttribute('hidden')).toBe(false);
    expect(screen.getByTestId('studio-ide-chat-pane').hasAttribute('hidden')).toBe(true);
    expect(screen.getByTestId('studio-ide-output-pane').textContent).toContain(
      'Deliverables body',
    );
  });

  it('locks Hybrid D stage-dominant grid CSS (not conversation-left split)', () => {
    const shellSource = readFileSync(
      join(process.cwd(), 'src/components/studio/StudioIdeShell.tsx'),
      'utf8',
    );
    const cssSource = readFileSync(
      join(process.cwd(), 'src/styles/studio-workbench.css'),
      'utf8',
    );
    expect(shellSource).toContain('data-shell="hybrid-d"');
    expect(shellSource).toContain('studio-activity-rail');
    expect(cssSource).toContain('minmax(0, 1.45fr)');
    expect(cssSource).toContain('studio-activity-rail');
    expect(cssSource).not.toContain('minmax(290px, 0.9fr)');
    expect(cssSource).not.toContain('font-size: 72px');
  });
});
