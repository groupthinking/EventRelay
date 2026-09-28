'use client';

import Link from 'next/link';
import {
  FormEvent,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import type { AppBuilderChapter, AppBuilderSopStep } from '@/lib/emit-app-builder-sandbox';
import {
  loadStudioShellFlag,
  loadStudioShellNumber,
  saveStudioShellFlag,
  saveStudioShellNumber,
  studioShellStoragePrefix,
} from '@/lib/studio-shell-storage';
import './studio-three-panel-shell.css';

const MIN_NAV = 180;
const MAX_NAV = 420;
const MIN_CHAT = 260;
const MAX_CHAT = 480;

export type StudioShellOutlineSection = {
  id: string;
  label: string;
};

export type StudioThreePanelShellProps = {
  youtubeVideoId: string;
  sourceHash: string;
  sourceUrl: string;
  chapters: AppBuilderChapter[];
  sopSteps: AppBuilderSopStep[];
  outlineSections: StudioShellOutlineSection[];
  onOutlineSelect: (sectionId: string) => void;
  activeOutlineId?: string | null;
  children: ReactNode;
};

const WORKSPACE_TABS: StudioShellOutlineSection[] = [
  { id: 'studio-shell-video', label: 'Video' },
  { id: 'studio-shell-transcript', label: 'Transcript' },
  { id: 'studio-shell-result', label: 'Result Ready' },
  { id: 'studio-shell-pack', label: 'Video pack' },
];

export default function StudioThreePanelShell({
  youtubeVideoId,
  sourceHash,
  sourceUrl,
  chapters,
  sopSteps,
  outlineSections,
  onOutlineSelect,
  activeOutlineId,
  children,
}: StudioThreePanelShellProps) {
  const storagePrefix = studioShellStoragePrefix(youtubeVideoId, sourceHash);
  const shellRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const [navCollapsed, setNavCollapsed] = useState(false);
  const [chatClosed, setChatClosed] = useState(false);
  const [navWidth, setNavWidth] = useState(240);
  const [chatWidth, setChatWidth] = useState(320);
  const [draft, setDraft] = useState('');
  const [bubbles, setBubbles] = useState<Array<{ id: string; kind: 'user' | 'system'; text: string }>>(
    [],
  );
  const bubbleId = useId();

  useEffect(() => {
    setNavWidth(loadStudioShellNumber(storagePrefix, 'nav-w', 240));
    setChatWidth(loadStudioShellNumber(storagePrefix, 'chat-w', 320));
    setNavCollapsed(loadStudioShellFlag(storagePrefix, 'nav-collapsed'));
    setChatClosed(loadStudioShellFlag(storagePrefix, 'chat-closed'));
  }, [storagePrefix]);

  useEffect(() => {
    const root = shellRef.current;
    if (!root) return;
    root.style.setProperty('--shell-nav-w', `${navWidth}px`);
    root.style.setProperty('--shell-chat-w', `${chatWidth}px`);
  }, [navWidth, chatWidth]);

  const toggleNavCollapsed = useCallback(() => {
    setNavCollapsed((prev) => {
      const next = !prev;
      saveStudioShellFlag(storagePrefix, 'nav-collapsed', next);
      return next;
    });
  }, [storagePrefix]);

  const setChatPanelClosed = useCallback(
    (closed: boolean) => {
      setChatClosed(closed);
      saveStudioShellFlag(storagePrefix, 'chat-closed', closed);
    },
    [storagePrefix],
  );

  const appendBubble = useCallback((text: string, kind: 'user' | 'system') => {
    setBubbles((prev) => [...prev, { id: `${bubbleId}-${prev.length}`, kind, text }]);
    requestAnimationFrame(() => {
      const node = messagesRef.current;
      if (node) node.scrollTop = node.scrollHeight;
    });
  }, [bubbleId]);

  const onComposerSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    appendBubble(text, 'user');
    setDraft('');
    appendBubble(
      'Preview only — your message was not sent to a model. M2 will connect live UVAI chat; this rail does not call /api/chat.',
      'system',
    );
  };

  const onCta = (kind: 'summarize' | 'extract' | 'open-d') => {
    if (kind === 'open-d') return;
    if (kind === 'summarize') {
      setDraft('Summarize the transcript and pack fields already shown in Studio for this video.');
    } else {
      setDraft('List ship actions and SOP steps already on this page — do not invent new ones.');
    }
  };

  const startResize = (
    side: 'left' | 'right',
    splitter: HTMLElement,
    onMove: (clientX: number) => void,
  ) => {
    splitter.dataset.dragging = 'true';
    const onPointerMove = (event: PointerEvent) => onMove(event.clientX);
    const onPointerUp = () => {
      splitter.dataset.dragging = 'false';
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
    };
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  };

  const hostedPath = `/d/${youtubeVideoId}`;

  const sectionButtons = outlineSections.length > 0 ? outlineSections : WORKSPACE_TABS;

  return (
    <div
      ref={shellRef}
      className="studio-shell-viewport"
      data-testid="saas-three-panel-shell"
    >
      <div className="studio-saas-shell" data-testid="saas-shell-panels">
        <aside
          className="studio-shell-nav"
          data-testid="shell-nav-panel"
          data-collapsed={navCollapsed ? 'true' : 'false'}
          aria-label="Pack navigation"
        >
          <div className="studio-shell-nav-header">
            <h2>Outline</h2>
            <button
              type="button"
              className="studio-shell-icon-btn"
              data-testid="shell-nav-collapse"
              aria-label={navCollapsed ? 'Expand navigation' : 'Collapse navigation'}
              title={navCollapsed ? 'Expand' : 'Collapse'}
              onClick={toggleNavCollapsed}
            >
              {navCollapsed ? '›' : '‹'}
            </button>
          </div>
          <nav className="studio-outline-body" aria-label="Pack outline">
            <div className="studio-outline-group" data-testid="outline-workspace">
              <h3>Workspace</h3>
              <ul className="studio-outline-list">
                {sectionButtons.map((tab) => (
                  <li key={tab.id}>
                    <button
                      type="button"
                      data-testid="outline-tab"
                      data-active={activeOutlineId === tab.id ? 'true' : 'false'}
                      onClick={() => onOutlineSelect(tab.id)}
                    >
                      {tab.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
            <div className="studio-outline-group" data-testid="outline-chapters">
              <h3>Chapters</h3>
              <ul className="studio-outline-list">
                {chapters.length === 0 ? (
                  <li>
                    <p className="px-2 py-1.5 text-white/40">No chapters on this pack.</p>
                  </li>
                ) : (
                  chapters.map((chapter, index) => (
                    <li key={`${chapter.start}-${chapter.topic}`}>
                      <button
                        type="button"
                        data-testid="outline-chapter"
                        onClick={() => onOutlineSelect(`studio-shell-chapter-${index}`)}
                      >
                        {chapter.topic.length > 56 ? `${chapter.topic.slice(0, 55)}…` : chapter.topic}
                      </button>
                    </li>
                  ))
                )}
              </ul>
            </div>
            {sopSteps.length > 0 ? (
              <div className="studio-outline-group" data-testid="outline-sop">
                <h3>SOP</h3>
                <ul className="studio-outline-list">
                  {sopSteps.map((step) => (
                    <li key={step.id}>
                      <button
                        type="button"
                        data-testid="outline-sop-jump"
                        onClick={() => onOutlineSelect('studio-shell-sop')}
                      >
                        {step.title.length > 52 ? `${step.title.slice(0, 51)}…` : step.title}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </nav>
        </aside>

        {!navCollapsed ? (
          <div
            className="studio-shell-splitter shell-splitter-left"
            data-testid="shell-splitter-left"
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize navigation"
            onPointerDown={(event) => {
              event.preventDefault();
              const splitter = event.currentTarget;
              startResize('left', splitter, (clientX) => {
                const bounds = shellRef.current?.querySelector('[data-testid="saas-shell-panels"]')?.getBoundingClientRect();
                if (!bounds) return;
                const next = Math.min(MAX_NAV, Math.max(MIN_NAV, clientX - bounds.left));
                setNavWidth(next);
                saveStudioShellNumber(storagePrefix, 'nav-w', next);
              });
            }}
          />
        ) : null}

        <main className="studio-shell-center workbench" data-testid="studio-shell-center">
          {children}
        </main>

        {!chatClosed ? (
          <div
            className="studio-shell-splitter shell-splitter-right"
            data-testid="shell-splitter-right"
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize assistant"
            onPointerDown={(event) => {
              event.preventDefault();
              const splitter = event.currentTarget;
              startResize('right', splitter, (clientX) => {
                const bounds = shellRef.current?.querySelector('[data-testid="saas-shell-panels"]')?.getBoundingClientRect();
                if (!bounds) return;
                const next = Math.min(MAX_CHAT, Math.max(MIN_CHAT, bounds.right - clientX));
                setChatWidth(next);
                saveStudioShellNumber(storagePrefix, 'chat-w', next);
              });
            }}
          />
        ) : null}

        <aside
          className="studio-shell-chat"
          data-testid="shell-chat-panel"
          data-closed={chatClosed ? 'true' : 'false'}
          aria-label="UVAI assistant"
        >
          <header className="studio-shell-chat-header">
            <h2>UVAI AI</h2>
            <button
              type="button"
              className="studio-shell-icon-btn"
              data-testid="shell-chat-close"
              aria-label="Close assistant panel"
              onClick={() => setChatPanelClosed(true)}
            >
              ×
            </button>
          </header>
          <div className="studio-shell-chat-body" data-testid="shell-chat-messages" ref={messagesRef}>
            <div className="studio-chat-bubble studio-chat-bubble-system" data-testid="shell-chat-honesty">
              Preview rail — messages stay in this browser until M2 connects live chat. I only reference pack
              fields on this page; no invented ship receipts or G.A.T.E. PASS.
            </div>
            {bubbles.map((bubble) => (
              <div
                key={bubble.id}
                className={
                  bubble.kind === 'user'
                    ? 'studio-chat-bubble studio-chat-bubble-user'
                    : 'studio-chat-bubble studio-chat-bubble-system'
                }
              >
                {bubble.text}
              </div>
            ))}
            <div className="studio-chat-cta-row" data-testid="shell-chat-ctas" role="group" aria-label="Pack actions">
              <button
                type="button"
                className="studio-chat-cta"
                data-testid="chat-cta-summarize"
                onClick={() => onCta('summarize')}
              >
                Summarize
              </button>
              <button
                type="button"
                className="studio-chat-cta"
                data-testid="chat-cta-extract"
                onClick={() => onCta('extract')}
              >
                Extract
              </button>
              <Link
                href={hostedPath}
                className="studio-chat-cta"
                data-testid="chat-cta-open-d"
              >
                Open /d
              </Link>
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="studio-chat-cta"
                data-testid="chat-cta-export"
              >
                Open source
              </a>
            </div>
          </div>
          <form className="studio-shell-chat-composer" data-testid="shell-chat-composer" onSubmit={onComposerSubmit}>
            <textarea
              name="message"
              rows={3}
              placeholder="Ask about this pack…"
              aria-label="Message UVAI AI"
              data-testid="shell-chat-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
            <p className="composer-note">Local preview composer — not a deploy or G.A.T.E. claim.</p>
            <button type="submit" data-testid="shell-chat-send" disabled={draft.trim().length === 0}>
              Send (preview)
            </button>
          </form>
        </aside>
      </div>
      <button
        type="button"
        className="studio-shell-chat-reopen"
        data-testid="shell-chat-reopen"
        data-visible={chatClosed ? 'true' : 'false'}
        aria-label="Open UVAI assistant"
        onClick={() => setChatPanelClosed(false)}
      >
        UVAI AI
      </button>
    </div>
  );
}
