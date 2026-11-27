'use client';

import Link from 'next/link';
import { ReactNode, useState } from 'react';
import {
  Code2,
  Film,
  FolderOpen,
  LayoutTemplate,
  MessageSquare,
  Wrench,
} from 'lucide-react';
import {
  studioContextSurfaceForActivity,
  type StudioActivityMode,
} from '@/lib/studio-ia-modes';
import '@/styles/studio-cards.css';
import '@/styles/studio-workbench.css';

export const MOBILE_PANES = ['video', 'chat', 'output'] as const;
export type MobilePane = (typeof MOBILE_PANES)[number];
export type { StudioActivityMode };

const ACTIVITY_ITEMS = [
  { id: 'video', label: 'Video', Icon: Film },
  { id: 'agents', label: 'Agents', Icon: MessageSquare },
  { id: 'tools', label: 'Tools', Icon: Wrench },
  { id: 'files', label: 'Files', Icon: FolderOpen },
  { id: 'canvas', label: 'Canvas', Icon: LayoutTemplate },
  { id: 'code', label: 'Code', Icon: Code2 },
] as const satisfies ReadonlyArray<{
  id: StudioActivityMode;
  label: string;
  Icon: typeof Film;
}>;

export type StudioIdeShellProps = {
  toolbar: ReactNode;
  videoPane: ReactNode;
  chatPane: ReactNode;
  outputPane: ReactNode;
  detailsRail?: ReactNode;
  /** Controlled activity mode (Cut 4 IA rename). */
  activityMode?: StudioActivityMode;
  onActivityChange?: (mode: StudioActivityMode) => void;
};

function mobilePaneFor(mode: StudioActivityMode): MobilePane {
  switch (mode) {
    case 'video':
      return 'video';
    case 'agents':
      return 'chat';
    case 'tools':
    case 'files':
    case 'canvas':
    case 'code':
      return 'output';
    default: {
      const _exhaustive: never = mode;
      return _exhaustive;
    }
  }
}

function activityForMobilePane(pane: MobilePane): StudioActivityMode {
  switch (pane) {
    case 'video':
      return 'video';
    case 'chat':
      return 'agents';
    case 'output':
      return 'tools';
    default: {
      const _exhaustive: never = pane;
      return _exhaustive;
    }
  }
}

function contextLabel(mode: StudioActivityMode): string {
  switch (mode) {
    case 'video':
    case 'agents':
      return 'Agents';
    case 'tools':
      return 'Tools';
    case 'files':
      return 'Files';
    case 'canvas':
      return 'Canvas';
    case 'code':
      return 'Code';
    default: {
      const _exhaustive: never = mode;
      return _exhaustive;
    }
  }
}

/**
 * Hybrid D stage shell (Cut 1) + Cut 4 IA rename wiring:
 * - Desktop: Builder-pattern activity rail + dominant video/pack stage + context rail.
 * - Mobile (<=679px): stage-first tabs (Source | Conversation | Deliverables).
 * - Activity modes wire Agents→chat and Tools/Files/Canvas/Code→deliverable tabs (parent-controlled).
 * Media owns the first viewport; chat never eats the stage; no persona grid.
 */
export default function StudioIdeShell({
  toolbar,
  videoPane,
  chatPane,
  outputPane,
  detailsRail,
  activityMode: controlledActivity,
  onActivityChange,
}: StudioIdeShellProps) {
  const [uncontrolledActivity, setUncontrolledActivity] = useState<StudioActivityMode>('video');
  const activityMode = controlledActivity ?? uncontrolledActivity;
  const [contextCollapsed, setContextCollapsed] = useState(false);
  const mobilePane = mobilePaneFor(activityMode);
  const showOutputContext = studioContextSurfaceForActivity(activityMode) === 'output';
  const chatHidden = showOutputContext;
  const outputHidden = !showOutputContext;

  const selectActivity = (mode: StudioActivityMode) => {
    if (controlledActivity === undefined) {
      setUncontrolledActivity(mode);
    }
    onActivityChange?.(mode);
    setContextCollapsed(false);
  };

  const selectMobilePane = (pane: MobilePane) => {
    selectActivity(activityForMobilePane(pane));
  };

  return (
    <div
      data-testid="studio-ide-shell"
      data-shell="hybrid-d"
      data-mobile-pane={mobilePane}
      data-activity={activityMode}
      data-context-collapsed={contextCollapsed ? 'true' : undefined}
      data-context-mode={showOutputContext ? 'output' : 'agents'}
      className="uvai-cards template-studio-shell studio-stage-shell flex flex-1 flex-col min-w-0"
    >
      <div data-testid="studio-ide-toolbar" className="uvai-toolbar sticky top-0 z-30">
        <div className="mx-auto flex w-full max-w-none flex-wrap items-center gap-2 min-w-0">
          {toolbar}
          {contextCollapsed ? (
            <div className="hidden flex-wrap items-center gap-2 min-[680px]:flex">
              <button
                type="button"
                data-testid="studio-context-restore"
                aria-controls="studio-context-rail"
                aria-expanded={false}
                onClick={() => setContextCollapsed(false)}
                className="uvai-btn !px-3 !py-1 !text-xs"
              >
                Show {contextLabel(activityMode).toLowerCase()}
              </button>
            </div>
          ) : null}
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
        data-context-collapsed={contextCollapsed ? 'true' : undefined}
        data-details-rail={detailsRail ? 'true' : undefined}
        data-testid="studio-stage-workspace"
        className="template-studio-bands studio-stage-bands mx-auto flex w-full max-w-none flex-1 min-w-0"
      >
        <nav
          data-testid="studio-activity-rail"
          aria-label="Studio activity"
          className="studio-activity-rail"
        >
          <div className="studio-activity-rail__items" role="toolbar" aria-label="Activity modes">
            {ACTIVITY_ITEMS.map(({ id, label, Icon }) => {
              const selected = activityMode === id;
              return (
                <button
                  key={id}
                  type="button"
                  data-testid={`studio-activity-${id}`}
                  aria-label={label}
                  aria-pressed={selected}
                  title={label}
                  onClick={() => selectActivity(id)}
                  className="studio-activity-rail__btn"
                  data-active={selected ? 'true' : undefined}
                >
                  <Icon aria-hidden className="studio-activity-rail__icon" strokeWidth={1.75} />
                  <span className="studio-activity-rail__label">{label}</span>
                </button>
              );
            })}
          </div>
          <Link
            href="/#get-pro"
            data-testid="studio-activity-get-pro"
            className="studio-activity-rail__pro"
            title="Get Pro"
          >
            Pro
          </Link>
        </nav>

        <section
          id="studio-panel-video"
          data-testid="studio-ide-video-pane"
          aria-label="Stage"
          role="tabpanel"
          aria-labelledby="studio-tab-video"
          className="uvai-card studio-stage-pane flex min-w-0 flex-col overflow-hidden"
        >
          <div className="uvai-pane-header studio-stage-header">
            <span className="uvai-section-label">Stage</span>
            <span className="studio-stage-badge" data-testid="studio-stage-plane">
              proposed
            </span>
          </div>
          <div className="studio-pane-body studio-pane-body--video studio-stage-body min-w-0">
            {videoPane}
          </div>
        </section>

        <aside
          id="studio-context-rail"
          data-testid="studio-context-rail"
          aria-label={`${contextLabel(activityMode)} context`}
          data-collapsed={contextCollapsed ? 'true' : undefined}
          className="studio-context-rail flex min-w-0 flex-col overflow-hidden"
        >
          <button
            type="button"
            data-testid="studio-context-rail-collapsed"
            aria-label={`Show ${contextLabel(activityMode)}`}
            aria-controls="studio-context-rail"
            aria-expanded={!contextCollapsed}
            aria-hidden={!contextCollapsed}
            tabIndex={contextCollapsed ? 0 : -1}
            onClick={() => setContextCollapsed(false)}
            className="studio-context-rail__strip"
          >
            <span className="studio-context-rail__restore-label">{contextLabel(activityMode)}</span>
          </button>

          <div className="studio-context-rail__body flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            <div className="uvai-pane-header studio-context-header">
              <span className="uvai-section-label">{contextLabel(activityMode)}</span>
              <button
                type="button"
                data-testid="studio-context-collapse"
                aria-label="Collapse context rail"
                aria-controls="studio-context-rail"
                aria-expanded={!contextCollapsed}
                onClick={() => setContextCollapsed(true)}
                className="rounded px-1.5 py-0.5 text-[var(--uvai-ink-faint)] hover:bg-[var(--uvai-surface-warm)] hover:text-[var(--uvai-ink)]"
              >
                ›
              </button>
            </div>

            <section
              id="studio-panel-chat"
              data-testid="studio-ide-chat-pane"
              aria-label="Chat"
              role="tabpanel"
              aria-labelledby="studio-tab-chat"
              hidden={chatHidden}
              className="uvai-card studio-context-pane flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
            >
              <div className="studio-pane-body flex-1 min-h-0 min-w-0">{chatPane}</div>
            </section>

            <section
              id="studio-panel-output"
              data-testid="studio-ide-output-pane"
              aria-label="Output"
              role="tabpanel"
              aria-labelledby="studio-tab-output"
              hidden={outputHidden}
              className="uvai-card studio-context-pane flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
            >
              <div className="studio-pane-body flex-1 min-h-0 min-w-0">{outputPane}</div>
            </section>
          </div>
        </aside>

        {detailsRail ? (
          <aside
            data-testid="studio-ide-details-rail"
            aria-label="Workspace details"
            className="template-details-rail"
          >
            {detailsRail}
          </aside>
        ) : null}
      </main>
    </div>
  );
}
