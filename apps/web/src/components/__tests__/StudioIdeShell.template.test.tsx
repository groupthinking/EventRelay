// @vitest-environment jsdom
import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import StudioIdeShell from '@/components/studio/StudioIdeShell';

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('OpenAI template Studio navigation', () => {
  it('switches source/chat/output without losing a conversation draft', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={<span>Run controls</span>} videoPane={<p>Source evidence</p>}
      chatPane={<input aria-label="Draft" defaultValue="" />} outputPane={<p>Deliverables</p>} />);
    fireEvent.change(screen.getByLabelText('Draft'), { target: { value: 'Which step is unclear?' } });
    fireEvent.click(screen.getByRole('tab', { name: 'Source' }));
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('video');
    expect(screen.getByRole('tab', { name: 'Source' }).getAttribute('aria-selected')).toBe('true');
    fireEvent.click(screen.getByRole('tab', { name: 'Deliverables' }));
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('output');
    fireEvent.click(screen.getByRole('tab', { name: 'Conversation' }));
    expect((screen.getByLabelText('Draft') as HTMLInputElement).value).toBe('Which step is unclear?');
  });

  it('returns to Conversation after either selected mobile side pane collapses', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    for (const [view, collapse] of [['Source', 'Collapse video pane'], ['Deliverables', 'Collapse output pane']]) {
      fireEvent.click(screen.getByRole('tab', { name: view }));
      fireEvent.click(screen.getByRole('button', { name: collapse }));
      expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('chat');
      expect(screen.getByRole('tab', { name: 'Conversation' }).getAttribute('aria-selected')).toBe('true');
    }
  });

  it('supports arrow and Home/End keys within the view toolbar', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Conversation' }), { key: 'ArrowRight' });
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('output');
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'Deliverables' }));
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Deliverables' }), { key: 'Home' });
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('video');
  });

  it('restores a collapsed pane through the mobile view controls', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    fireEvent.click(screen.getByRole('button', { name: 'Collapse video pane' }));
    expect(screen.queryByTestId('studio-ide-video-pane')).toBeNull();
    fireEvent.click(screen.getByRole('tab', { name: 'Source' }));
    expect(screen.getByTestId('studio-ide-video-pane')).toBeTruthy();
  });

  it('keeps one main landmark containing the selected tabpanel', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);

    const main = screen.getByRole('main');
    expect(screen.getAllByRole('main')).toHaveLength(1);
    for (const name of ['Source', 'Conversation', 'Deliverables']) {
      const tab = screen.getByRole('tab', { name });
      fireEvent.click(tab);
      const panel = document.getElementById(tab.getAttribute('aria-controls')!);
      expect(panel?.getAttribute('role')).toBe('tabpanel');
      expect(panel?.getAttribute('aria-labelledby')).toBe(tab.id);
      expect(main.contains(panel)).toBe(true);
      expect(screen.getByRole('main')).toBe(main);
    }
  });

  it.each([
    ['left', 'ArrowRight', 'ArrowLeft', 280],
    ['right', 'ArrowLeft', 'ArrowRight', 340],
  ] as const)('resizes the %s pane in both directions and clamps keyboard bounds', (side, grow, shrink, initial) => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    const splitter = screen.getByTestId(`studio-ide-splitter-${side}`);
    const shell = screen.getByTestId('studio-ide-shell');
    const widthProperty = side === 'left' ? '--ide-left-w' : '--ide-right-w';
    fireEvent.keyDown(splitter, { key: grow });
    expect(splitter.getAttribute('aria-valuenow')).toBe(String(initial + 20));
    expect(shell.style.getPropertyValue(widthProperty)).toBe(`${initial + 20}px`);
    fireEvent.keyDown(splitter, { key: shrink });
    expect(splitter.getAttribute('aria-valuenow')).toBe(String(initial));
    fireEvent.keyDown(splitter, { key: 'Home' });
    fireEvent.keyDown(splitter, { key: shrink });
    expect(splitter.getAttribute('aria-valuenow')).toBe(splitter.getAttribute('aria-valuemin'));
    fireEvent.keyDown(splitter, { key: 'End' });
    fireEvent.keyDown(splitter, { key: grow });
    expect(splitter.getAttribute('aria-valuenow')).toBe(splitter.getAttribute('aria-valuemax'));
  });

  it.each([901, 1000, 1100])('keeps keyboard widths and ARIA bounds within the %spx layout budget', (width) => {
    vi.stubGlobal('React', React);
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      const measuredWidth = this.classList.contains('template-studio-panes') ? width
        : this.classList.contains('uvai-splitter') ? 4 : 0;
      return { x: 0, y: 0, top: 0, left: 0, right: measuredWidth, bottom: 700, width: measuredWidth, height: 700, toJSON: () => ({}) };
    });
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    const left = screen.getByTestId('studio-ide-splitter-left');
    const right = screen.getByTestId('studio-ide-splitter-right');
    const shell = screen.getByTestId('studio-ide-shell');
    const assertWidths = () => {
      const leftWidth = Number(left.getAttribute('aria-valuenow'));
      const rightWidth = Number(right.getAttribute('aria-valuenow'));
      expect(leftWidth + rightWidth + 8 + 240).toBeLessThanOrEqual(width);
      for (const splitter of [left, right]) {
        const current = Number(splitter.getAttribute('aria-valuenow'));
        expect(current).toBeGreaterThanOrEqual(Number(splitter.getAttribute('aria-valuemin')));
        expect(current).toBeLessThanOrEqual(Number(splitter.getAttribute('aria-valuemax')));
      }
      expect(shell.style.getPropertyValue('--ide-left-w')).toBe(`${leftWidth}px`);
      expect(shell.style.getPropertyValue('--ide-right-w')).toBe(`${rightWidth}px`);
    };
    assertWidths();
    for (const splitter of [left, right]) {
      for (const key of ['End', 'ArrowRight', 'ArrowLeft', 'Home']) {
        fireEvent.keyDown(splitter, { key });
        assertWidths();
      }
    }
  });

  it('reconciles the width budget on viewport changes and pane collapse/restore', () => {
    vi.stubGlobal('React', React);
    let width = 1440;
    let notifyResize = () => {};
    const disconnect = vi.fn();
    vi.stubGlobal('ResizeObserver', class {
      constructor(callback: () => void) { notifyResize = callback; }
      observe() {}
      disconnect = disconnect;
    });
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      const measuredWidth = this.classList.contains('template-studio-panes') ? width
        : this.classList.contains('uvai-splitter') ? 4 : this.tagName === 'BUTTON' ? 50 : 0;
      return { x: 0, y: 0, top: 0, left: 0, right: measuredWidth, bottom: 700, width: measuredWidth, height: 700, toJSON: () => ({}) };
    });
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    const shell = screen.getByTestId('studio-ide-shell');
    const left = screen.getByTestId('studio-ide-splitter-left');
    const right = screen.getByTestId('studio-ide-splitter-right');
    fireEvent.keyDown(left, { key: 'End' });
    fireEvent.keyDown(right, { key: 'End' });
    expect(left.getAttribute('aria-valuenow')).toBe('560');
    expect(right.getAttribute('aria-valuenow')).toBe('560');
    act(() => { width = 901; notifyResize(); });
    expect(left.getAttribute('aria-valuenow')).toBe('413');
    expect(right.getAttribute('aria-valuenow')).toBe('240');
    expect(left.getAttribute('aria-valuemax')).toBe('413');
    expect(right.getAttribute('aria-valuemax')).toBe('240');
    expect(shell.style.getPropertyValue('--ide-left-w')).toBe('413px');
    expect(shell.style.getPropertyValue('--ide-right-w')).toBe('240px');
    act(() => { width = 1440; notifyResize(); });
    expect(left.getAttribute('aria-valuenow')).toBe('560');
    expect(right.getAttribute('aria-valuenow')).toBe('560');
    act(() => { width = 901; notifyResize(); });
    fireEvent.click(screen.getByRole('button', { name: 'Collapse output pane' }));
    // The restore button consumes 50px and the remaining splitter 4px.
    expect(left.getAttribute('aria-valuenow')).toBe('560');
    fireEvent.click(screen.getByRole('button', { name: 'Show output pane' }));
    expect(left.getAttribute('aria-valuenow')).toBe('413');
    expect(screen.getByTestId('studio-ide-splitter-right').getAttribute('aria-valuenow')).toBe('240');
    expect(disconnect).toHaveBeenCalled();
  });

  it('exposes separators as keyboard-resizable controls', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);

    const splitter = screen.getByTestId('studio-ide-splitter-left');
    expect(splitter.getAttribute('role')).toBe('separator');
    expect(splitter.getAttribute('tabindex')).toBe('0');
    expect(splitter.getAttribute('aria-valuemin')).toBe('240');
    expect(splitter.getAttribute('aria-valuemax')).toBe('560');
    expect(splitter.getAttribute('aria-valuenow')).toBe('280');

    fireEvent.keyDown(splitter, { key: 'ArrowRight' });
    expect(splitter.getAttribute('aria-valuenow')).toBe('300');

    fireEvent.keyDown(splitter, { key: 'End' });
    expect(splitter.getAttribute('aria-valuenow')).toBe('560');
  });
});
