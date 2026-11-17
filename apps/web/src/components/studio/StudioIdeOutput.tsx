'use client';

import { useState, type ReactNode } from 'react';
import type { Video } from '@/store/dashboard-types';
import type { ExtractedEvent } from '@/lib/types';
import { studioActionCard } from '@/lib/studio-pipeline-status';
import type { StudioStackCheckView } from '@/lib/official-templates';
import StudioBoundTasks from './StudioBoundTasks';

export type StudioReviewActionInput = {
  tool: string;
  input?: Record<string, unknown>;
  status: string;
  result?: string;
};

type OutputSection = 'tasks' | 'events' | 'lingo' | 'tools' | 'intent' | 'signals' | 'spec' | 'transcript';

const SECTIONS: Array<{ id: OutputSection; label: string }> = [
  { id: 'tasks', label: 'Tasks' },
  { id: 'events', label: 'Events' },
  { id: 'lingo', label: 'Lingo' },
  { id: 'tools', label: 'Tools' },
  { id: 'intent', label: 'Intent' },
  { id: 'signals', label: 'Signals' },
  { id: 'spec', label: 'Spec' },
  { id: 'transcript', label: 'Transcript' },
];

/**
 * Right-pane output for the Studio IDE, structured around ACTION EXTRACTION:
 * what the viewer can do or make from the video — not a summary.
 *
 * Presented in the locked light card system (DESIGN_LANGUAGE.md):
 * white cards on soft blue-gray. Card = one structured idea —
 * small icon, label, value. Documents are first-class rows.
 *
 * - Events: timestamped things that happened (from the event extractor)
 * - Lingo: domain verbiage / topics the video uses
 * - Tools: named tools, stack, and SOP steps
 * - Intent: action items — what to do next
 * - Signals: visual / nonverbal cues from keyframes and visual context
 * - Spec: grounded spec review (G.A.T.E. acknowledgment surface)
 */
export default function StudioIdeOutput({
  video,
  specReview,
  eventsEmptyMessage,
  stackChecks = [],
  reviewActions = [],
  packWorkbench,
}: {
  video: Video | undefined;
  specReview?: ReactNode;
  eventsEmptyMessage?: string;
  stackChecks?: StudioStackCheckView[];
  reviewActions?: StudioReviewActionInput[];
  packWorkbench?: ReactNode;
}) {
  const [active, setActive] = useState<OutputSection>('tasks');
  const [reviewingAction, setReviewingAction] = useState<string | null>(null);

  const hasContent = Boolean(
    video?.videoPack ||
      video?.events?.length ||
      video?.insights ||
      eventsEmptyMessage ||
      stackChecks.length > 0 ||
      reviewActions.length > 0 ||
      packWorkbench,
  );

  const pack = video?.videoPack?.pack;
  const events: ExtractedEvent[] = video?.events ?? [];
  const topics: string[] = video?.insights?.topics ?? [];
  const actionItems = pack?.action_items ?? [];
  const stackTools = pack?.stack?.tools ?? [];
  const visualContext = pack?.visual_context;
  const keyframes = pack?.keyframes ?? [];
  const codeSnippets = pack?.code_snippets ?? [];
  const chapters = pack?.chapters ?? [];
  const linkedSop = video?.insights?.linkedSop;

  const toolNames: string[] = stackTools
    .map((t) => t.name?.trim())
    .filter((t): t is string => Boolean(t))
    .filter((t, i, arr) => arr.indexOf(t) === i);

  return (
    <div data-testid="studio-ide-output" className="flex h-full min-h-0 flex-col bg-[var(--uvai-bg)]">
      <div
        role="tablist"
        aria-label="Output sections"
        className="flex flex-wrap shrink-0 gap-1.5 border-b border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] px-3 py-2.5"
      >
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={active === s.id}
            data-testid={`studio-ide-output-tab-${s.id}`}
            onClick={() => setActive(s.id)}
            className={`whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              active === s.id
                ? 'bg-[#146ef5] text-white'
                : 'bg-transparent text-[var(--uvai-ink-soft)] hover:bg-[var(--uvai-surface-warm)] hover:text-[var(--uvai-ink)]'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto bg-[var(--uvai-bg)] p-4">
        {!hasContent && active !== 'transcript' && active !== 'tasks' ? (
          <div className="uvai-empty">
            <p className="font-medium text-[var(--uvai-ink)]">
              Run a video and the extracted actions land here
            </p>
            <p className="text-xs text-[var(--uvai-ink-soft)]">Events, lingo, tools, intent, signals — as structured cards.</p>
          </div>
        ) : (
          <>
        {active === 'tasks' && <StudioBoundTasks key={video?.id ?? 'empty'} pack={pack} />}
        {active === 'events' && (
          <div className="flex flex-col gap-3" data-testid="studio-ide-output-events">
            {events.length === 0 ? (
              <EmptyNote
                text={
                  eventsEmptyMessage ||
                  'This run has no extracted events. Pack identity stays on this page.'
                }
              />
            ) : (
              <ul className="flex flex-col gap-3">
                {events.map((e) => (
                  <li key={e.id} className="uvai-card p-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1.5 rounded bg-[var(--uvai-accent-soft)] px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--uvai-accent-ink)]">
                        <DotIcon />
                        {e.type}
                      </span>
                      {e.timestamp ? (
                        <span className="font-mono text-[11px] text-[var(--uvai-ink-faint)]">{e.timestamp}</span>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm font-semibold text-[var(--uvai-ink)]">{e.title}</p>
                    {e.description ? (
                      <p className="mt-1 text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{e.description}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
            {packWorkbench}
          </div>
        )}

        {active === 'lingo' && (
          <div data-testid="studio-ide-output-lingo">
            {topics.length === 0 ? (
              <EmptyNote text="No domain lingo identified yet." />
            ) : (
              <div className="uvai-card p-4">
                <p className="uvai-section-label mb-3">Domain terms</p>
                <div className="flex flex-wrap gap-2">
                  {topics.map((t, i) => (
                    <span
                      key={`${t}-${i}`}
                      className="rounded-md border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface-warm)] px-3 py-1 text-xs font-medium text-[var(--uvai-ink)]"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {active === 'tools' && (
          <div data-testid="studio-ide-output-tools" className="flex flex-col gap-3">
            {toolNames.length === 0 && !linkedSop?.steps.length && stackChecks.length === 0 && codeSnippets.length === 0 && chapters.length === 0 ? (
              <EmptyNote text="No tools or code snippets extracted yet." />
            ) : (
              <>
                {chapters.length > 0 ? (
                  <div className="uvai-card p-4" data-testid="studio-pack-chapters">
                    <p className="uvai-section-label mb-3">Chapters</p>
                    <ol className="flex flex-col gap-2">
                      {chapters.map((chapter, index) => (
                        <li key={`${chapter.topic}-${index}`} className="uvai-doc-row">
                          <span className="uvai-doc-icon">{String(index + 1).padStart(2, '0')}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <p className="truncate text-sm font-medium text-[var(--uvai-ink)]">{chapter.topic}</p>
                              <span className="shrink-0 font-mono text-[11px] text-[var(--uvai-ink-faint)]">
                                {chapter.start}s–{chapter.end}s
                              </span>
                            </div>
                            {chapter.key_points?.length ? (
                              <p className="mt-0.5 truncate text-xs text-[var(--uvai-ink-soft)]">
                                {chapter.key_points[0]}
                              </p>
                            ) : null}
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}
                {toolNames.length > 0 ? (
                  <div className="uvai-card p-4">
                    <p className="uvai-section-label mb-3">Named tools</p>
                    <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {toolNames.map((t, i) => (
                        <li key={`${t}-${i}`} className="uvai-metric">
                          <div className="uvai-metric-icon">
                            <WrenchIcon />
                          </div>
                          <p className="font-mono text-xs font-semibold text-[var(--uvai-ink)]">{t}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {codeSnippets.length > 0 ? (
                  <div className="uvai-card p-4" data-testid="studio-pack-code-snippets">
                    <p className="uvai-section-label mb-3">Extracted code & signatures</p>
                    <div className="flex flex-col gap-3">
                      {codeSnippets.map((snippet, index) => (
                        <div key={`${snippet.path_hint ?? 'snippet'}-${index}`} className="overflow-hidden rounded-md border border-[var(--uvai-border-strong)] bg-[#0a0a0a]">
                          <div className="flex items-center justify-between border-b border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-3 py-1.5 font-mono text-[11px] text-[var(--uvai-ink-soft)]">
                            <span>{snippet.path_hint || `snippet-${index + 1}`}</span>
                            {snippet.lang ? <span className="uppercase text-[var(--uvai-accent-ink)]">{snippet.lang}</span> : null}
                          </div>
                          <pre className="max-h-64 overflow-auto p-3 font-mono text-xs leading-relaxed text-[#e5e5e5]">
                            {snippet.content}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {stackChecks.length > 0 ? (
                  <div className="uvai-card p-4" data-testid="studio-stack-checks">
                    <p className="uvai-section-label mb-3">Stack checks</p>
                    <ul className="flex flex-col gap-2">
                      {stackChecks.map((check) => (
                        <li
                          key={check.id}
                          data-testid={`studio-stack-check-${check.id}`}
                          className="uvai-doc-row"
                        >
                          <span className="uvai-doc-icon" aria-hidden>
                            {check.status === 'done' ? '✓' : check.status === 'pending' ? '•' : '?'}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-[var(--uvai-ink)]">{check.title}</p>
                            <p className="text-xs text-[var(--uvai-ink-faint)]">{check.statusLabel}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {linkedSop?.steps?.length ? (
                  <div className="uvai-card p-4">
                    <p className="uvai-section-label mb-3">SOP steps</p>
                    <ol className="flex flex-col gap-2">
                      {linkedSop.steps.map((s, i) => (
                        <li key={s.id ?? i} className="uvai-doc-row">
                          <span className="uvai-doc-icon">{String(i + 1).padStart(2, '0')}</span>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-[var(--uvai-ink)]">{s.title}</p>
                            <p className="text-xs text-[var(--uvai-ink-faint)]">Step {i + 1}</p>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}
              </>
            )}
          </div>
        )}

        {active === 'intent' && (
          <ul className="flex flex-col gap-3" data-testid="studio-ide-output-intent">
            {reviewActions.length === 0 && actionItems.length === 0 ? (
              <EmptyNote text="No action items extracted yet — what should the viewer do or make from this video?" />
            ) : (
              <>
                {reviewActions.map((action, i) => {
                  const card = studioActionCard(action);
                  const actionKey = `${video?.id ?? 'none'}:${action.tool}:${i}`;
                  return (
                    <li
                      key={`${action.tool}-${i}`}
                      data-testid="studio-review-action-card"
                      className="uvai-card border-l-4 !border-l-[#146ef5] p-4"
                    >
                      <div className="flex items-start gap-3">
                        <span className="uvai-metric-icon mt-0.5 shrink-0">
                          <ArrowIcon />
                        </span>
                        <div className="min-w-0">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--uvai-accent-ink)]">
                            {card.statusLabel}
                          </p>
                          <p className="mt-1 text-sm font-semibold text-[var(--uvai-ink)]">{card.title}</p>
                          <p className="mt-1 text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{card.detail}</p>
                          {card.kind === 'review' ? (
                            <button
                              type="button"
                              data-testid="studio-review-act-button"
                              onClick={() => setReviewingAction(reviewingAction === actionKey ? null : actionKey)}
                              aria-expanded={reviewingAction === actionKey}
                              className="uvai-btn uvai-btn-primary mt-3"
                            >
                              {reviewingAction === actionKey ? 'Hide proposal' : 'Review proposal'}
                            </button>
                          ) : null}
                          {reviewingAction === actionKey ? (
                            <div data-testid="studio-proposal-detail" className="mt-3 rounded-md border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface-warm)] p-3 text-xs text-[var(--uvai-ink-soft)]">
                              <p>Proposed tool: {action.tool}</p>
                              <p>Status: {action.status}. No tool has been executed from this review.</p>
                              {action.input ? (
                                <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded border border-[var(--uvai-border)] bg-[var(--uvai-bg)] p-2 text-[var(--uvai-ink)]">
                                  {JSON.stringify(action.input, null, 2)}
                                </pre>
                              ) : (
                                <p>Proposal arguments are unavailable for this run.</p>
                              )}
                              <p>{card.detail}</p>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </li>
                  );
                })}
                {actionItems.map((a, i) => (
                  <li key={a.id ?? i} className="uvai-card border-l-4 !border-l-[#146ef5] p-4">
                    <div className="flex items-start gap-3">
                      <span className="uvai-metric-icon mt-0.5 shrink-0">
                        <ArrowIcon />
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-[var(--uvai-ink)]">{a.title}</p>
                        {a.description ? (
                          <p className="mt-1 text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{a.description}</p>
                        ) : null}
                      </div>
                    </div>
                  </li>
                ))}
              </>
            )}
          </ul>
        )}

        {active === 'signals' && (
          <div data-testid="studio-ide-output-signals" className="flex flex-col gap-3">
            {!visualContext && keyframes.length === 0 ? (
              <EmptyNote text="No visual signals captured yet." />
            ) : (
              <>
                {visualContext?.summary ? (
                  <div className="uvai-card p-4">
                    <p className="uvai-section-label mb-2">Visual summary</p>
                    <p className="text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{visualContext.summary}</p>
                  </div>
                ) : null}
                {keyframes.length > 0 ? (
                  <div className="grid grid-cols-2 gap-3">
                    {keyframes.map((k, i) => (
                      <figure key={k.t_s ?? i} className="uvai-card overflow-hidden">
                        {k.image_path ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={k.image_path}
                            alt={`Keyframe ${i + 1}`}
                            className="aspect-video w-full object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <div className="flex aspect-video items-center justify-center bg-[var(--uvai-surface-warm)] text-[11px] font-medium text-[var(--uvai-ink-faint)]">
                            {k.t_s != null ? `${k.t_s}s` : `Frame ${i + 1}`}
                          </div>
                        )}
                        {k.desc ? (
                          <figcaption className="border-t border-[var(--uvai-border)] px-3 py-2 text-[11px] leading-snug text-[var(--uvai-ink-soft)]">
                            {k.desc}
                          </figcaption>
                        ) : null}
                      </figure>
                    ))}
                  </div>
                ) : null}
              </>
            )}
          </div>
        )}
        {active === 'spec' && (
          <div data-testid="studio-ide-output-spec">
            {specReview ?? <EmptyNote text="No grounded spec on this pack." />}
          </div>
        )}

        {active === 'transcript' && (
          <div data-testid="studio-transcript-body" className="uvai-card p-4">
            {video?.transcript?.trim() ? (
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-[var(--uvai-ink-soft)]">
                {video.transcript}
              </p>
            ) : video?.failure?.message ? (
              <p className="text-xs text-[var(--uvai-danger-ink)]">{video.failure.message}</p>
            ) : (
              <p className="py-4 text-center text-xs text-[var(--uvai-ink-faint)]">Nothing yet.</p>
            )}
          </div>
        )}
          </>
        )}
      </div>
    </div>
  );
}

function EmptyNote({ text }: { text: string }) {
  return (
    <div className="uvai-card p-8 text-center">
      <p className="text-xs text-[var(--uvai-ink-faint)]">{text}</p>
    </div>
  );
}

function DotIcon() {
  return (
    <svg width="6" height="6" viewBox="0 0 6 6" fill="currentColor" aria-hidden="true">
      <circle cx="3" cy="3" r="3" />
    </svg>
  );
}

function WrenchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}
