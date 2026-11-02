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
const RESIZE_STEP = 20;
const MOBILE_PANES = ['video', 'chat', 'output'] as const;
type MobilePane = (typeof MOBILE_PANES)[number];

function clampPaneWidth(value: number): number {
  return Math.min(MAX_SIDE, Math.max(MIN_SIDE, value));
}

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
  const [mobilePane, setMobilePane] = useState<MobilePane>('chat');
  const shellRef = useRef<HTMLDivElement>(null);
  const [leftWidth, setLeftWidth] = useState(280);
  const [rightWidth, setRightWidth] = useState(340);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  const selectMobilePane = useCallback((pane: MobilePane) => {
    setMobilePane(pane);
    if (pane === 'video') setLeftCollapsed(false);
    if (pane === 'output') setRightCollapsed(false);
  }, []);

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
          setLeftWidth(clampPaneWidth(clientX - bounds.left));
        } else {
          setRightWidth(clampPaneWidth(bounds.right - clientX));
        }
      };
      const onUp = () => {
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerup', onUp);
        splitter.dataset.dragging = 'false';
      };
      const onPointerMove = (e: PointerEvent) => onMove(e.clientX);
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onUp);
      splitter.dataset.dragging = 'true';
    },
    [],
  );

  const onSplitterKeyDown = useCallback(
    (side: 'left' | 'right', key: string) => {
      const update = side === 'left' ? setLeftWidth : setRightWidth;
      const current = side === 'left' ? leftWidth : rightWidth;
      let next: number | null = null;
      if (key === 'Home') next = MIN_SIDE;
      if (key === 'End') next = MAX_SIDE;
      if (key === 'ArrowRight') next = current + (side === 'left' ? RESIZE_STEP : -RESIZE_STEP);
      if (key === 'ArrowLeft') next = current + (side === 'left' ? -RESIZE_STEP : RESIZE_STEP);
      if (key === 'ArrowUp') next = current + RESIZE_STEP;
      if (key === 'ArrowDown') next = current - RESIZE_STEP;
      if (next === null) return false;
      update(clampPaneWidth(next));
      return true;
    },
    [leftWidth, rightWidth],
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
        {MOBILE_PANES.map((pane) => (
          <button key={pane} type="button" role="tab" id={`studio-tab-${pane}`}
            aria-selected={mobilePane === pane} aria-controls={`studio-panel-${pane}`}
            tabIndex={mobilePane === pane ? 0 : -1}
            onKeyDown={(event) => {
              const index = MOBILE_PANES.indexOf(pane);
              const next = event.key === 'ArrowRight' ? MOBILE_PANES[(index + 1) % 3]
                : event.key === 'ArrowLeft' ? MOBILE_PANES[(index + 2) % 3]
                  : event.key === 'Home' ? 'video' : event.key === 'End' ? 'output' : null;
              if (next) {
                event.preventDefault();
                selectMobilePane(next);
                document.getElementById(`studio-tab-${next}`)?.focus();
              }
            }}
            onClick={() => selectMobilePane(pane)}
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
            role="tabpanel"
            aria-labelledby="studio-tab-video"
            className="uvai-card flex min-h-0 w-[var(--ide-left-w)] shrink-0 flex-col overflow-hidden"
          >
            <div className="uvai-pane-header">
              <span className="uvai-section-label">Source video</span>
              <button
                type="button"
                aria-label="Collapse video pane"
                aria-controls="studio-panel-video"
                aria-expanded={!leftCollapsed}
                onClick={() => { setLeftCollapsed(true); setMobilePane('chat'); }}
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
            aria-controls="studio-panel-video"
            aria-valuemin={MIN_SIDE}
            aria-valuemax={MAX_SIDE}
            aria-valuenow={leftWidth}
            data-testid="studio-ide-splitter-left"
            className="uvai-splitter"
            tabIndex={0}
            onPointerDown={(e) => {
              e.preventDefault();
              startResize('left', e.currentTarget);
            }}
            onKeyDown={(event) => {
              if (onSplitterKeyDown('left', event.key)) event.preventDefault();
            }}
          />
        ) : null}

        {/* CENTER: chat */}
        <main
          id="studio-panel-chat"
          data-testid="studio-ide-chat-pane"
          aria-label="Chat"
          role="tabpanel"
          aria-labelledby="studio-tab-chat"
          className="uvai-card flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
        >
          <div className="uvai-pane-header">
            <span className="uvai-section-label">Conversation</span>
            {leftCollapsed ? (
              <button
                type="button"
                aria-controls="studio-panel-video"
                aria-expanded={!leftCollapsed}
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
            aria-controls="studio-panel-output"
            aria-valuemin={MIN_SIDE}
            aria-valuemax={MAX_SIDE}
            aria-valuenow={rightWidth}
            data-testid="studio-ide-splitter-right"
            className="uvai-splitter"
            tabIndex={0}
            onPointerDown={(e) => {
              e.preventDefault();
              startResize('right', e.currentTarget);
            }}
            onKeyDown={(event) => {
              if (onSplitterKeyDown('right', event.key)) event.preventDefault();
            }}
          />
        ) : null}

        {/* RIGHT: output */}
        {!rightCollapsed ? (
          <aside
            id="studio-panel-output"
            data-testid="studio-ide-output-pane"
            aria-label="Output"
            role="tabpanel"
            aria-labelledby="studio-tab-output"
            className="uvai-card flex min-h-0 w-[var(--ide-right-w)] shrink-0 flex-col overflow-hidden"
          >
            <div className="uvai-pane-header">
              <span className="uvai-section-label">Deliverables</span>
              <button
                type="button"
                aria-label="Collapse output pane"
                aria-controls="studio-panel-output"
                aria-expanded={!rightCollapsed}
                onClick={() => { setRightCollapsed(true); setMobilePane('chat'); }}
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
            aria-controls="studio-panel-output"
            aria-expanded={!rightCollapsed}
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
