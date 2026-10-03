'use client';

import { useState } from 'react';
import type { Video } from '@/store/dashboard-types';
import type { ExtractedEvent } from '@/lib/types';

type OutputSection = 'events' | 'lingo' | 'tools' | 'intent' | 'signals' | 'spec' | 'transcript';

const SECTIONS: Array<{ id: OutputSection; label: string }> = [
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
}: {
  video: Video | undefined;
  specReview?: React.ReactNode;
}) {
  const [active, setActive] = useState<OutputSection>('events');

  const hasContent = Boolean(video?.videoPack || video?.events?.length || video?.insights);

  const pack = video?.videoPack?.pack;
  const events: ExtractedEvent[] = video?.events ?? [];
  const topics: string[] = video?.insights?.topics ?? [];
  const actionItems = pack?.action_items ?? [];
  const stackTools = pack?.stack?.tools ?? [];
  const visualContext = pack?.visual_context;
  const keyframes = pack?.keyframes ?? [];
  const linkedSop = video?.insights?.linkedSop;

  const toolNames: string[] = stackTools
    .map((t) => t.name?.trim())
    .filter((t): t is string => Boolean(t))
    .filter((t, i, arr) => arr.indexOf(t) === i);

  return (
    <div data-testid="studio-ide-output" className="flex h-full min-h-0 flex-col bg-white">
      <div
        role="tablist"
        aria-label="Output sections"
        className="flex shrink-0 gap-1 overflow-x-auto border-b border-slate-100 bg-slate-50/60 px-3 py-2"
      >
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={active === s.id}
            data-testid={`studio-ide-output-tab-${s.id}`}
            onClick={() => setActive(s.id)}
            className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              active === s.id
                ? 'bg-amber-600 text-white shadow-sm'
                : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto bg-[#f2f5f9] p-4">
        {!hasContent && active !== 'transcript' ? (
          <div className="uvai-empty">
            <p className="font-medium text-slate-600">
              Run a video and the extracted actions land here
            </p>
            <p className="text-xs">Events, lingo, tools, intent, signals — as structured cards.</p>
          </div>
        ) : (
          <>
        {active === 'events' && (
          <ul className="flex flex-col gap-3" data-testid="studio-ide-output-events">
            {events.length === 0 ? (
              <EmptyNote text="No events extracted from this video yet." />
            ) : (
              events.map((e) => (
                <li key={e.id} className="uvai-card p-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-amber-800">
                      <DotIcon />
                      {e.type}
                    </span>
                    {e.timestamp ? (
                      <span className="font-mono text-[11px] text-slate-400">{e.timestamp}</span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm font-semibold text-slate-900">{e.title}</p>
                  {e.description ? (
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">{e.description}</p>
                  ) : null}
                </li>
              ))
            )}
          </ul>
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
                      className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700"
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
            {toolNames.length === 0 && !linkedSop?.steps.length ? (
              <EmptyNote text="No tools named in this video yet." />
            ) : (
              <>
                {toolNames.length > 0 ? (
                  <div className="uvai-card p-4">
                    <p className="uvai-section-label mb-3">Named tools</p>
                    <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {toolNames.map((t, i) => (
                        <li key={`${t}-${i}`} className="uvai-metric">
                          <div className="uvai-metric-icon">
                            <WrenchIcon />
                          </div>
                          <p className="font-mono text-xs font-semibold text-slate-800">{t}</p>
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
                            <p className="truncate text-sm font-medium text-slate-800">{s.title}</p>
                            <p className="text-xs text-slate-400">Step {i + 1}</p>
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
            {actionItems.length === 0 ? (
              <EmptyNote text="No action items extracted yet — what should the viewer do or make from this video?" />
            ) : (
              actionItems.map((a, i) => (
                <li key={a.id ?? i} className="uvai-card border-l-4 !border-l-amber-600 p-4">
                  <div className="flex items-start gap-3">
                    <span className="uvai-metric-icon mt-0.5 shrink-0">
                      <ArrowIcon />
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900">{a.title}</p>
                      {a.description ? (
                        <p className="mt-1 text-xs leading-relaxed text-slate-500">{a.description}</p>
                      ) : null}
                    </div>
                  </div>
                </li>
              ))
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
                    <p className="text-xs leading-relaxed text-slate-600">{visualContext.summary}</p>
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
                          <div className="flex aspect-video items-center justify-center bg-slate-100 text-[11px] font-medium text-slate-400">
                            {k.t_s != null ? `${k.t_s}s` : `Frame ${i + 1}`}
                          </div>
                        )}
                        {k.desc ? (
                          <figcaption className="border-t border-slate-100 px-3 py-2 text-[11px] leading-snug text-slate-500">
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
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-600">
                {video.transcript}
              </p>
            ) : video?.failure?.message ? (
              <p className="text-xs text-red-700">{video.failure.message}</p>
            ) : (
              <p className="py-4 text-center text-xs text-slate-400">Nothing yet.</p>
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
      <p className="text-xs text-slate-400">{text}</p>
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
