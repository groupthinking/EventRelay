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
    <div data-testid="studio-ide-output" className="flex h-full min-h-0 flex-col">
      <div
        role="tablist"
        aria-label="Output sections"
        className="flex shrink-0 gap-1 border-b border-white/10 px-2 py-1.5"
      >
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={active === s.id}
            data-testid={`studio-ide-output-tab-${s.id}`}
            onClick={() => setActive(s.id)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium ${
              active === s.id
                ? 'bg-amber-500/15 text-amber-200'
                : 'text-white/50 hover:bg-white/5 hover:text-white/75'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {!hasContent && active !== 'transcript' ? (
          <div className="flex h-full items-center justify-center px-6 text-center">
            <p className="text-sm text-white/40">
              Run a video and the extracted actions land here — events, lingo, tools, intent, signals.
            </p>
          </div>
        ) : (
          <>
        {active === 'events' && (
          <ul className="flex flex-col gap-2" data-testid="studio-ide-output-events">
            {events.length === 0 ? (
              <EmptyNote text="No events extracted from this video yet." />
            ) : (
              events.map((e) => (
                <li
                  key={e.id}
                  className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-amber-200/80">
                      {e.type}
                    </span>
                    {e.timestamp ? (
                      <span className="font-mono text-[11px] text-white/40">{e.timestamp}</span>
                    ) : null}
                  </div>
                  <p className="mt-1 text-sm text-white/85">{e.title}</p>
                  {e.description ? (
                    <p className="mt-0.5 text-xs text-white/50">{e.description}</p>
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
              <div className="flex flex-wrap gap-1.5">
                {topics.map((t, i) => (
                  <span
                    key={`${t}-${i}`}
                    className="rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-xs text-white/75"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {active === 'tools' && (
          <div data-testid="studio-ide-output-tools">
            {toolNames.length === 0 && !linkedSop?.steps.length ? (
              <EmptyNote text="No tools named in this video yet." />
            ) : (
              <>
                {toolNames.length > 0 ? (
                  <ul className="flex flex-col gap-1.5">
                    {toolNames.map((t, i) => (
                      <li
                        key={`${t}-${i}`}
                        className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 font-mono text-xs text-white/80"
                      >
                        {t}
                      </li>
                    ))}
                  </ul>
                ) : null}
                {linkedSop?.steps?.length ? (
                  <div className="mt-3">
                    <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-white/50">
                      SOP steps
                    </h4>
                    <ol className="flex list-decimal flex-col gap-1.5 pl-5">
                      {linkedSop.steps.map((s, i) => (
                        <li key={s.id ?? i} className="text-xs text-white/70">
                          {s.title}
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
          <ul className="flex flex-col gap-2" data-testid="studio-ide-output-intent">
            {actionItems.length === 0 ? (
              <EmptyNote text="No action items extracted yet — what should the viewer do or make from this video?" />
            ) : (
              actionItems.map((a, i) => (
                <li
                  key={a.id ?? i}
                  className="rounded-lg border border-amber-500/25 bg-amber-500/[0.06] px-3 py-2"
                >
                  <p className="text-sm text-white/85">{a.title}</p>
                  {a.description ? (
                    <p className="mt-0.5 text-xs text-white/50">{a.description}</p>
                  ) : null}
                </li>
              ))
            )}
          </ul>
        )}

        {active === 'signals' && (
          <div data-testid="studio-ide-output-signals">
            {!visualContext && keyframes.length === 0 ? (
              <EmptyNote text="No visual signals captured yet." />
            ) : (
              <>
                {visualContext?.summary ? (
                  <p className="mb-3 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-white/70">
                    {visualContext.summary}
                  </p>
                ) : null}
                {keyframes.length > 0 ? (
                  <div className="grid grid-cols-2 gap-2">
                    {keyframes.map((k, i) => (
                      <figure
                        key={k.t_s ?? i}
                        className="overflow-hidden rounded-lg border border-white/10"
                      >
                        {k.image_path ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={k.image_path}
                            alt={k.desc || `Keyframe ${i + 1}`}
                            className="aspect-video w-full object-cover"
                            loading="lazy"
                          />
                        ) : (
                          <div className="flex aspect-video items-center justify-center bg-black/40 text-[11px] text-white/40">
                            {k.t_s != null ? `${k.t_s}s` : `Frame ${i + 1}`}
                          </div>
                        )}
                        {k.desc ? (
                          <figcaption className="px-2 py-1 text-[11px] text-white/55">
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
          <div data-testid="studio-transcript-body" className="px-1">
            {video?.transcript?.trim() ? (
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-white/75">
                {video.transcript}
              </p>
            ) : video?.failure?.message ? (
              <p className="text-xs text-red-200/80">{video.failure.message}</p>
            ) : (
              <p className="py-4 text-center text-xs text-white/35">Nothing yet.</p>
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
  return <p className="px-1 py-4 text-center text-xs text-white/35">{text}</p>;
}
