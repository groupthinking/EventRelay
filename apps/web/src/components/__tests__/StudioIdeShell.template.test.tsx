// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import StudioIdeShell from '@/components/studio/StudioIdeShell';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('OpenAI template Studio navigation', () => {
  it('switches source/chat/output without losing a conversation draft', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={<span>Run controls</span>} videoPane={<p>Source evidence</p>}
      chatPane={<input aria-label="Draft" defaultValue="" />} outputPane={<p>Deliverables</p>} />);
    fireEvent.change(screen.getByLabelText('Draft'), { target: { value: 'Which step is unclear?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Source' }));
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('video');
    expect(screen.getByRole('button', { name: 'Source' }).getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(screen.getByRole('button', { name: 'Deliverables' }));
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('output');
    fireEvent.click(screen.getByRole('button', { name: 'Conversation' }));
    expect((screen.getByLabelText('Draft') as HTMLInputElement).value).toBe('Which step is unclear?');
  });
  it('returns to Conversation after either selected mobile side pane collapses', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    for (const [view, collapse] of [['Source', 'Collapse video pane'], ['Deliverables', 'Collapse output pane']]) {
      fireEvent.click(screen.getByRole('button', { name: view }));
      fireEvent.click(screen.getByRole('button', { name: collapse }));
      expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('chat');
      expect(screen.getByRole('button', { name: 'Conversation' }).getAttribute('aria-pressed')).toBe('true');
    }
  });
  it('supports arrow and Home/End keys within the view toolbar', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    fireEvent.keyDown(screen.getByRole('button', { name: 'Conversation' }), { key: 'ArrowRight' });
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('output');
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Deliverables' }));
    fireEvent.keyDown(screen.getByRole('button', { name: 'Deliverables' }), { key: 'Home' });
    expect(screen.getByTestId('studio-ide-shell').dataset.mobilePane).toBe('video');
  });
  it('restores a collapsed pane through the mobile view controls', () => {
    vi.stubGlobal('React', React);
    render(<StudioIdeShell toolbar={null} videoPane={<p>Source</p>} chatPane={<p>Chat</p>} outputPane={<p>Files</p>} />);
    fireEvent.click(screen.getByRole('button', { name: 'Collapse video pane' }));
    expect(screen.queryByTestId('studio-ide-video-pane')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Source' }));
    expect(screen.getByTestId('studio-ide-video-pane')).toBeTruthy();
  });
});
