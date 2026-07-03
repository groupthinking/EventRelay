import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import type { ReactNode } from 'react';

/**
 * These tests exercise the accessibility attributes (aria-pressed, aria-label,
 * aria-hidden, aria-expanded, aria-controls) added to VideoWorkflowStudio.
 *
 * The project's vitest config runs in the `node` environment (no jsdom) since
 * no component-rendering tests existed prior to this suite. Rather than
 * pulling in new dependencies (jsdom / @testing-library/react), these tests
 * use `react-dom/server`'s `renderToStaticMarkup`, which works in plain
 * Node.js and is sufficient for asserting on the static markup/attributes a
 * given component state produces. Interactive state transitions that require
 * simulated clicks (e.g. opening the "Developer details" panel) are outside
 * what this rendering approach can exercise and are not covered here.
 */

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => <a href={href}>{children}</a>,
}));

const useRealtimeVoiceMock = vi.fn();

vi.mock('@/hooks/use-realtime-voice', () => ({
  useRealtimeVoice: () => useRealtimeVoiceMock(),
}));

import VideoWorkflowStudio from '@/components/VideoWorkflowStudio';

type RealtimeStatus = 'idle' | 'connecting' | 'connected' | 'muted' | 'error';

function mockRealtime(overrides: Partial<{
  status: RealtimeStatus;
  isActive: boolean;
  error: string | null;
  events: unknown[];
}> = {}) {
  useRealtimeVoiceMock.mockReturnValue({
    status: 'idle',
    isActive: false,
    error: null,
    events: [],
    start: vi.fn(),
    stop: vi.fn(),
    disconnect: vi.fn(),
    toggleMute: vi.fn(),
    ...overrides,
  });
}

/** Extract the nearest enclosing <button>...</button> containing `marker`. */
function extractButton(html: string, marker: string): string {
  const markerIndex = html.indexOf(marker);
  if (markerIndex === -1) {
    throw new Error(`Could not find marker text "${marker}" in rendered output`);
  }
  const start = html.lastIndexOf('<button', markerIndex);
  const closeIndex = html.indexOf('</button>', markerIndex);
  if (start === -1 || closeIndex === -1) {
    throw new Error(`Could not locate enclosing <button> for marker "${marker}"`);
  }
  return html.slice(start, closeIndex + '</button>'.length);
}

describe('VideoWorkflowStudio accessibility attributes', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('voice toggle button', () => {
    it('is unpressed with an "enable" label and a hidden MicOff icon when voice is off', () => {
      mockRealtime({ status: 'idle', isActive: false });
      const html = renderToStaticMarkup(<VideoWorkflowStudio />);
      const button = extractButton(html, 'Voice off');

      expect(button).toContain('aria-pressed="false"');
      expect(button).toContain('aria-label="Enable voice input"');
      expect(button).toContain('aria-hidden="true"');
    });

    it('is pressed with a "disable" label while connecting', () => {
      mockRealtime({ status: 'connecting', isActive: false });
      const html = renderToStaticMarkup(<VideoWorkflowStudio />);
      const button = extractButton(html, 'Voice connecting');

      expect(button).toContain('aria-pressed="true"');
      expect(button).toContain('aria-label="Disable voice input"');
    });

    it('is pressed with a "disable" label once connected', () => {
      mockRealtime({ status: 'connected', isActive: true });
      const html = renderToStaticMarkup(<VideoWorkflowStudio />);
      const button = extractButton(html, 'Voice on');

      expect(button).toContain('aria-pressed="true"');
      expect(button).toContain('aria-label="Disable voice input"');
    });
  });

  describe('mute button', () => {
    it('is not rendered while voice is inactive', () => {
      mockRealtime({ status: 'idle', isActive: false });
      const html = renderToStaticMarkup(<VideoWorkflowStudio />);

      expect(html).not.toContain('aria-label="Mute voice session"');
      expect(html).not.toContain('aria-label="Resume voice session"');
    });

    it('is unpressed and labeled to mute when connected and unmuted', () => {
      mockRealtime({ status: 'connected', isActive: true });
      const html = renderToStaticMarkup(<VideoWorkflowStudio />);
      const button = extractButton(html, 'Mute');

      expect(button).toContain('aria-pressed="false"');
      expect(button).toContain('aria-label="Mute voice session"');
    });

    it('is pressed and labeled to resume when muted', () => {
      mockRealtime({ status: 'muted', isActive: true });
      const html = renderToStaticMarkup(<VideoWorkflowStudio />);
      const button = extractButton(html, 'Resume');

      expect(button).toContain('aria-pressed="true"');
      expect(button).toContain('aria-label="Resume voice session"');
    });
  });

  describe('developer details toggle', () => {
    it('is collapsed by default with correct aria-expanded/aria-controls wiring', () => {
      mockRealtime();
      const html = renderToStaticMarkup(<VideoWorkflowStudio />);
      const button = extractButton(html, 'Developer details');

      expect(button).toContain('aria-expanded="false"');
      expect(button).toContain('aria-controls="developer-details-panel"');
      expect(button).toContain('aria-hidden="true"');
    });

    it('does not render the panel content while collapsed', () => {
      mockRealtime();
      const html = renderToStaticMarkup(<VideoWorkflowStudio />);

      expect(html).not.toContain('id="developer-details-panel"');
      expect(html).not.toContain('Voice events appear here when the toggle is on.');
    });
  });
});