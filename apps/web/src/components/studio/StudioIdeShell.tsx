'use client';

import { ReactNode, useCallback, useState } from 'react';
import '@/styles/studio-cards.css';

type StudioIdeShellProps = {
  toolbar: ReactNode;
  videoPane: ReactNode;
  chatPane: ReactNode;
  outputPane: ReactNode;
};

const MOBILE_PANES = ['video', 'chat', 'output'] as const;
type MobilePane = (typeof MOBILE_PANES)[number];

/**
 * Horizontal Webflow + Shipper Studio shell: sticky full-width toolbar, then stacked
 * horizontal bands (Source hero stage, inline Agent Prompt/Chat bar, and full-width Deliverables).
 */
export default function StudioIdeShell({
  toolbar,
  videoPane,
  chatPane,
  outputPane,
}: StudioIdeShellProps) {
  const [mobilePane, setMobilePane] = useState<MobilePane>('chat');
  const [videoCollapsed, setVideoCollapsed] = useState(false);
  const [outputCollapsed, setOutputCollapsed] = useState(false);

  const selectMobilePane = useCallback((pane: MobilePane) => {
    setMobilePane(pane);
    if (pane === 'video') setVideoCollapsed(false);
    if (pane === 'output') setOutputCollapsed(false);
  }, []);

  return (
    <div
      data-testid="studio-ide-shell"
      data-mobile-pane={mobilePane}
      className="uvai-cards template-studio-shell flex flex-1 flex-col"
    >
      <div data-testid="studio-ide-toolbar" className="uvai-toolbar sticky top-0 z-30">
        <div className="mx-auto flex w-full max-w-[1360px] flex-wrap items-center gap-2">
          {toolbar}
        </div>
      </div>

      <div className="template-pane-tabs" role="tablist" aria-label="Studio views">
        {MOBILE_PANES.map((pane) => (
          <button
            key={pane}
            type="button"
            role="tab"
            id={`studio-tab-${pane}`}
            aria-selected={mobilePane === pane}
            aria-controls={`studio-panel-${pane}`}
            tabIndex={mobilePane === pane ? 0 : -1}
            onKeyDown={(event) => {
              const index = MOBILE_PANES.indexOf(pane);
              const next =
                event.key === 'ArrowRight'
                  ? MOBILE_PANES[(index + 1) % 3]
                  : event.key === 'ArrowLeft'
                    ? MOBILE_PANES[(index + 2) % 3]
                    : event.key === 'Home'
                      ? 'video'
                      : event.key === 'End'
                        ? 'output'
                        : null;
              if (next) {
                event.preventDefault();
                selectMobilePane(next);
                document.getElementById(`studio-tab-${next}`)?.focus();
              }
            }}
            onClick={() => selectMobilePane(pane)}
          >
            {pane === 'video' ? 'Source' : pane === 'chat' ? 'Conversation' : 'Deliverables'}
          </button>
        ))}
      </div>

      <main
        aria-label="Studio workspace"
        className="template-studio-bands mx-auto flex w-full max-w-[1360px] flex-1 flex-col gap-5 px-4 py-5 sm:px-6"
      >
        {(videoCollapsed || outputCollapsed) && (
          <div className="hidden flex-wrap items-center gap-2 min-[901px]:flex">
            {videoCollapsed ? (
              <button
                type="button"
                aria-controls="studio-panel-video"
                aria-expanded={false}
                onClick={() => setVideoCollapsed(false)}
                className="uvai-btn !px-3 !py-1.5 !text-xs"
              >
                Show video
              </button>
            ) : null}
            {outputCollapsed ? (
              <button
                type="button"
                aria-controls="studio-panel-output"
                aria-expanded={false}
                onClick={() => setOutputCollapsed(false)}
                className="uvai-btn !px-3 !py-1.5 !text-xs"
              >
                Show deliverables
              </button>
            ) : null}
          </div>
        )}

        {/* BAND 1: horizontal media + pack details stage */}
        {!videoCollapsed ? (
          <section
            id="studio-panel-video"
            data-testid="studio-ide-video-pane"
            aria-label="Video"
            role="tabpanel"
            aria-labelledby="studio-tab-video"
            className="uvai-card flex flex-col overflow-hidden"
          >
            <div className="uvai-pane-header">
              <span className="uvai-section-label">Source video</span>
              <button
                type="button"
                aria-label="Collapse video pane"
                aria-controls="studio-panel-video"
                aria-expanded={!videoCollapsed}
                onClick={() => {
                  setVideoCollapsed(true);
                  setMobilePane('chat');
                }}
                className="rounded px-1.5 py-0.5 text-[var(--uvai-ink-faint)] hover:bg-[var(--uvai-surface-warm)] hover:text-[var(--uvai-ink)]"
              >
                ▴
              </button>
            </div>
            <div className="p-4 sm:p-5">{videoPane}</div>
          </section>
        ) : null}

        {/* BAND 2: compact horizontal Shipper prompt & conversation bar */}
        <section
          id="studio-panel-chat"
          data-testid="studio-ide-chat-pane"
          aria-label="Chat"
          role="tabpanel"
          aria-labelledby="studio-tab-chat"
          className="uvai-card flex flex-col overflow-hidden"
        >
          <div className="uvai-pane-header">
            <span className="uvai-section-label">Ask UVAI · Conversation</span>
            <div className="flex items-center gap-2">
              {videoCollapsed ? (
                <button
                  type="button"
                  aria-controls="studio-panel-video"
                  aria-expanded={!videoCollapsed}
                  onClick={() => setVideoCollapsed(false)}
                  className="uvai-btn !px-2.5 !py-1 !text-xs min-[901px]:!hidden"
                >
                  Show video
                </button>
              ) : null}
            </div>
          </div>
          <div>{chatPane}</div>
        </section>

        {/* BAND 3: full-width horizontal Deliverables */}
        {!outputCollapsed ? (
          <section
            id="studio-panel-output"
            data-testid="studio-ide-output-pane"
            aria-label="Output"
            role="tabpanel"
            aria-labelledby="studio-tab-output"
            className="uvai-card flex flex-1 flex-col overflow-hidden"
          >
            <div className="uvai-pane-header">
              <span className="uvai-section-label">Deliverables</span>
              <button
                type="button"
                aria-label="Collapse output pane"
                aria-controls="studio-panel-output"
                aria-expanded={!outputCollapsed}
                onClick={() => {
                  setOutputCollapsed(true);
                  setMobilePane('chat');
                }}
                className="rounded px-1.5 py-0.5 text-[var(--uvai-ink-faint)] hover:bg-[var(--uvai-surface-warm)] hover:text-[var(--uvai-ink)]"
              >
                ▴
              </button>
            </div>
            <div className="flex-1">{outputPane}</div>
          </section>
        ) : null}
      </main>
    </div>
  );
}
