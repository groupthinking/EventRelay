'use client';

import { ReactNode, useCallback, useEffect, useRef, useState } from 'react';

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
 */
export default function StudioIdeShell({
  toolbar,
  videoPane,
  chatPane,
  outputPane,
}: StudioIdeShellProps) {
  const shellRef = useRef<HTMLDivElement>(null);
  const [leftWidth, setLeftWidth] = useState(380);
  const [rightWidth, setRightWidth] = useState(420);
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
    <div ref={shellRef} data-testid="studio-ide-shell" className="flex min-h-0 flex-1 flex-col">
      <div
        data-testid="studio-ide-toolbar"
        className="flex flex-wrap items-center gap-2 border-b border-white/10 bg-[#11131a] px-3 py-2"
      >
        {toolbar}
      </div>
      <div className="flex min-h-0 flex-1">
        {/* LEFT: video */}
        {!leftCollapsed ? (
          <aside
            data-testid="studio-ide-video-pane"
            aria-label="Video"
            className="flex min-h-0 w-[var(--ide-left-w)] shrink-0 flex-col border-r border-white/10"
          >
            <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-white/50">
                Video
              </span>
              <button
                type="button"
                aria-label="Collapse video pane"
                onClick={() => setLeftCollapsed(true)}
                className="rounded px-1 text-white/40 hover:bg-white/10 hover:text-white/70"
              >
                ‹
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-3">{videoPane}</div>
          </aside>
        ) : null}
        {!leftCollapsed ? (
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize video pane"
            data-testid="studio-ide-splitter-left"
            className="w-1 shrink-0 cursor-col-resize bg-white/5 hover:bg-amber-500/40"
            onPointerDown={(e) => {
              e.preventDefault();
              startResize('left', e.currentTarget);
            }}
          />
        ) : null}

        {/* CENTER: chat */}
        <main
          data-testid="studio-ide-chat-pane"
          aria-label="Chat"
          className="flex min-h-0 min-w-0 flex-1 flex-col"
        >
          <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-white/50">
              Chat
            </span>
            {leftCollapsed ? (
              <button
                type="button"
                onClick={() => setLeftCollapsed(false)}
                className="rounded border border-white/15 px-2 py-0.5 text-xs text-white/60 hover:bg-white/5"
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
            className="w-1 shrink-0 cursor-col-resize bg-white/5 hover:bg-amber-500/40"
            onPointerDown={(e) => {
              e.preventDefault();
              startResize('right', e.currentTarget);
            }}
          />
        ) : null}

        {/* RIGHT: output */}
        {!rightCollapsed ? (
          <aside
            data-testid="studio-ide-output-pane"
            aria-label="Output"
            className="flex min-h-0 w-[var(--ide-right-w)] shrink-0 flex-col border-l border-white/10"
          >
            <div className="flex items-center justify-between border-b border-white/10 px-3 py-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-white/50">
                Output
              </span>
              <button
                type="button"
                aria-label="Collapse output pane"
                onClick={() => setRightCollapsed(true)}
                className="rounded px-1 text-white/40 hover:bg-white/10 hover:text-white/70"
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
            className="shrink-0 border-l border-white/10 px-2 text-xs text-white/60 hover:bg-white/5"
            aria-label="Show output pane"
          >
            Output
          </button>
        )}
      </div>
    </div>
  );
}
