'use client';

import { useState, type ReactNode } from 'react';
import { Menu, X } from 'lucide-react';

/**
 * Adapted from openai/openai-responses-starter-app/app/page.tsx at
 * 0fae283f12ca3f71015cd9fa3f9b28df97e9ae21 (MIT; see THIRD_PARTY_NOTICES.md).
 * Keep the primary workspace/context split; use an inline mobile disclosure
 * so the existing source form remains reachable without an overlay or trap.
 */
export default function HomeTemplateShell({ children, context }: {
  children: ReactNode;
  context: ReactNode;
}) {
  const [isContextPanelOpen, setIsContextPanelOpen] = useState(false);

  return (
    <div data-template="openai-responses-starter" className="home-template-shell">
      <div className="home-template-primary">
        {children}
        <button
          type="button"
          className="home-context-toggle uvai-btn uvai-btn-secondary"
          aria-expanded={isContextPanelOpen}
          aria-controls="home-context-panel"
          onClick={() => setIsContextPanelOpen((open) => !open)}
        >
          {isContextPanelOpen ? <X size={16} aria-hidden="true" /> : <Menu size={16} aria-hidden="true" />}
          {isContextPanelOpen ? 'Hide workflow details' : 'Show workflow details'}
        </button>
      </div>
      <aside
        id="home-context-panel"
        aria-label="Video workflow context"
        className={`home-template-context ${isContextPanelOpen ? 'is-open' : ''}`}
      >
        {context}
      </aside>
    </div>
  );
}
