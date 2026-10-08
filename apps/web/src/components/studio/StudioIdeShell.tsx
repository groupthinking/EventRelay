'use client';

import { ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import '@/styles/studio-cards.css';

type StudioIdeShellProps = {
  toolbar: ReactNode;
  videoPane: ReactNode;
  chatPane: ReactNode;
  outputPane: ReactNode;
};

const MIN_SIDE = 240;
const MAX_SIDE = 560;

/**
 * Three-pane Studio IDE shell: top toolbar, then video | chat | output.
 * Side panes are resizable; widths persist per session in memory.
 *
 * Styled in the locked light card system (DESIGN_LANGUAGE.md):
 * white cards on soft blue-gray, airy spacing.
 */
export default function StudioIdeShell({
  toolbar,
  videoPane,
  chatPane,
  outputPane,
}: StudioIdeShellProps) {
  const [mobilePane, setMobilePane] = useState<'video' | 'chat' | 'output'>('chat');
  const shellRef = useRef<HTMLDivElement>(null);
  const [leftWidth, setLeftWidth] = useState(280);
  const [rightWidth, setRightWidth] = useState(340);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  useEffect(() => {
    const root = shellRef.current;
    if (!root) return;
    root.style.setProperty('--ide-left-w', `${leftWidth}px`);
    root.style.setProperty('--ide-right-w', `${rightWidth}px`);
  }, [leftWidth, rightWidth]);

  const startResize = useCallback(
    (side: 'left' | 'right', splitter: HTMLElement) => {
      const onMove = (clientX: number) => {
        const bounds = shellRef.current?.getBoundingClientRect();
        if (!bounds) return;
        if (side === 'left') {
          setLeftWidth(Math.min(MAX_SIDE, Math.max(MIN_SIDE, clientX - bounds.left)));
        } else {
          setRightWidth(Math.min(MAX_SIDE, Math.max(MIN_SIDE, bounds.right - clientX)));
        }
      };
      const onUp = () => {
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerup', onUp);
      };
      const onPointerMove = (e: PointerEvent) => onMove(e.clientX);
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onUp);
      splitter.dataset.dragging = 'true';
    },
    [],
  );

  return (
    <div
      ref={shellRef}
      data-testid="studio-ide-shell"
      data-template="openai-responses-starter"
      data-mobile-pane={mobilePane}
      className="uvai-cards template-studio-shell flex min-h-0 flex-1 flex-col"
    >
      <div data-testid="studio-ide-toolbar" className="uvai-toolbar">
        {toolbar}
      </div>
      <div className="template-pane-tabs" role="tablist" aria-label="Studio views">
        {(['video', 'chat', 'output'] as const).map((pane) => (
          <button key={pane} type="button" role="tab" id={`studio-tab-${pane}`}
            aria-selected={mobilePane === pane} aria-controls={`studio-panel-${pane}`}
            tabIndex={mobilePane === pane ? 0 : -1}
            onKeyDown={(event) => {
              const panes = ['video', 'chat', 'output'] as const;
              const index = panes.indexOf(pane);
              const next = event.key === 'ArrowRight' ? panes[(index + 1) % 3]
                : event.key === 'ArrowLeft' ? panes[(index + 2) % 3]
                  : event.key === 'Home' ? 'video' : event.key === 'End' ? 'output' : null;
              if (next) {
                event.preventDefault(); setMobilePane(next); setLeftCollapsed(false); setRightCollapsed(false);
                document.getElementById(`studio-tab-${next}`)?.focus();
              }
            }}
            onClick={() => { setMobilePane(pane); setLeftCollapsed(false); setRightCollapsed(false); }}
          >{pane === 'video' ? 'Source' : pane === 'chat' ? 'Conversation' : 'Deliverables'}</button>
        ))}
      </div>
      <div className="template-studio-panes flex min-h-0 flex-1">
        {/* LEFT: video */}
        {!leftCollapsed ? (
          <aside
            id="studio-panel-video"
            data-testid="studio-ide-video-pane"
            aria-label="Video"
            className="uvai-card flex min-h-0 w-[var(--ide-left-w)] shrink-0 flex-col overflow-hidden"
          >
            <div className="uvai-pane-header">
              <span className="uvai-section-label">Source video</span>
              <button
                type="button"
                aria-label="Collapse video pane"
                onClick={() => setLeftCollapsed(true)}
                className="rounded-md px-1.5 py-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                ‹
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-4">{videoPane}</div>
          </aside>
        ) : null}
        {!leftCollapsed ? (
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize video pane"
            data-testid="studio-ide-splitter-left"
            className="uvai-splitter"
            onPointerDown={(e) => {
              e.preventDefault();
              startResize('left', e.currentTarget);
            }}
          />
        ) : null}

        {/* CENTER: chat */}
        <main
          id="studio-panel-chat"
          data-testid="studio-ide-chat-pane"
          aria-label="Chat"
          className="uvai-card flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
        >
          <div className="uvai-pane-header">
            <span className="uvai-section-label">Conversation</span>
            {leftCollapsed ? (
              <button
                type="button"
                onClick={() => setLeftCollapsed(false)}
                className="uvai-btn !px-2.5 !py-1 !text-xs"
              >
                Show video
              </button>
            ) : null}
          </div>
          <div className="min-h-0 flex-1">{chatPane}</div>
        </main>

        {!rightCollapsed ? (
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize output pane"
            data-testid="studio-ide-splitter-right"
            className="uvai-splitter"
            onPointerDown={(e) => {
              e.preventDefault();
              startResize('right', e.currentTarget);
            }}
          />
        ) : null}

        {/* RIGHT: output */}
        {!rightCollapsed ? (
          <aside
            id="studio-panel-output"
            data-testid="studio-ide-output-pane"
            aria-label="Output"
            className="uvai-card flex min-h-0 w-[var(--ide-right-w)] shrink-0 flex-col overflow-hidden"
          >
            <div className="uvai-pane-header">
              <span className="uvai-section-label">Deliverables</span>
              <button
                type="button"
                aria-label="Collapse output pane"
                onClick={() => setRightCollapsed(true)}
                className="rounded-md px-1.5 py-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                ›
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto">{outputPane}</div>
          </aside>
        ) : (
          <button
            type="button"
            onClick={() => setRightCollapsed(false)}
            className="uvai-card shrink-0 px-2 text-xs font-medium text-slate-500 hover:text-slate-700"
            aria-label="Show output pane"
          >
            Output
          </button>
        )}
      </div>
    </div>
  );
}
