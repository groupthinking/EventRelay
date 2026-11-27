'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Check, Copy, Download, ExternalLink, Monitor, Play, Smartphone } from 'lucide-react';
import type { Video } from '@/store/dashboard-types';
import type { ExtractedEvent } from '@/lib/types';
import { studioActionCard, studioPackExtractedEvents, studioProposedToolCard } from '@/lib/studio-pipeline-status';
import type { StudioStackCheckView } from '@/lib/official-templates';
import { formatSeconds, parseTimestampToSeconds, parseTranscriptSegments } from '@/lib/timestamp';
import { downloadMarkdownFile } from '@/lib/download-file';
import StudioBoundTasks from './StudioBoundTasks';

export type StudioReviewActionInput = {
  tool: string;
  input?: Record<string, unknown>;
  status: string;
  result?: string;
};

export type OutputSection = 'preview' | 'tasks' | 'code' | 'transcript';

const SECTIONS: Array<{ id: OutputSection; label: string }> = [
  { id: 'preview', label: 'Preview' },
  { id: 'tasks', label: 'Tasks & Tools' },
  { id: 'code', label: 'Code & Spec' },
  { id: 'transcript', label: 'Transcript' },
];

export type StudioIdeOutputProps = {
  video: Video | undefined;
  specReview?: ReactNode;
  eventsEmptyMessage?: string;
  stackChecks?: StudioStackCheckView[];
  reviewActions?: StudioReviewActionInput[];
  packWorkbench?: ReactNode;
  previewVideoId?: string | null;
  previewReady?: boolean;
  onBuildLive?: () => void;
  buildBusy?: boolean;
  focusPreviewSignal?: number | string | null;
  initialSection?: OutputSection;
  activeSection?: OutputSection;
  onSectionChange?: (section: OutputSection) => void;
  onSeek?: (seconds: number) => void;
  /** Remaining-time copy while a transcript fetch is still running. */
  transcriptEta?: string | null;
  /** True when the fetch failed or has run long enough to retry. */
  showTranscriptRetry?: boolean;
  onRetryTranscript?: () => void;
};

/**
 * Right-pane Deliverables workbench for UVAI Studio.
 * Organized into 4 plain-English single-row tabs:
 * - Preview: Live `/d/{videoId}` artifact in a Webflow-style Desktop (full width) | Mobile (390px) frame
 * - Tasks & Tools: Bound tasks, proposed actions, chapters, detected events, tools/stack, and key topics
 * - Code & Spec: Extracted code snippets, starter artifacts, G.A.T.E. spec, and verification checklist
 * - Transcript: Click-to-seek timestamped transcript and visual keyframes
 */
export default function StudioIdeOutput({
  video,
  specReview,
  eventsEmptyMessage,
  stackChecks = [],
  reviewActions = [],
  packWorkbench,
  previewVideoId,
  previewReady = false,
  onBuildLive,
  buildBusy = false,
  focusPreviewSignal,
  initialSection,
  activeSection,
  onSectionChange,
  onSeek,
  transcriptEta = null,
  showTranscriptRetry = false,
  onRetryTranscript,
}: StudioIdeOutputProps) {
  const [internalActive, setInternalActive] = useState<OutputSection>(
    initialSection ?? (previewReady ? 'preview' : 'tasks'),
  );
  const [previewDevice, setPreviewDevice] = useState<'desktop' | 'mobile'>('desktop');
  const [reviewingAction, setReviewingAction] = useState<string | null>(null);
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);
  const prevPreviewReadyRef = useRef(Boolean(previewReady));
  /** Last focusPreviewSignal value that already forced Preview (Cut 4 latch). */
  const appliedFocusPreviewSignalRef = useRef<number | string | null | undefined>(undefined);

  const active = activeSection ?? internalActive;

  const selectSection = (next: OutputSection) => {
    if (activeSection === undefined) {
      setInternalActive(next);
    }
    onSectionChange?.(next);
  };

  useEffect(() => {
    if (previewReady && !prevPreviewReadyRef.current) {
      if (activeSection === undefined) {
        setInternalActive('preview');
      }
      onSectionChange?.('preview');
    }
    prevPreviewReadyRef.current = Boolean(previewReady);
  }, [previewReady, activeSection, onSectionChange]);

  useEffect(() => {
    // Consume only *new* focus signals. A sticky nonzero epoch after Build live
    // must not re-force Preview whenever the controlled section changes.
    if (focusPreviewSignal == null || focusPreviewSignal === '' || focusPreviewSignal === 0) {
      return;
    }
    if (Object.is(appliedFocusPreviewSignalRef.current, focusPreviewSignal)) {
      return;
    }
    appliedFocusPreviewSignalRef.current = focusPreviewSignal;
    if (activeSection === undefined) {
      setInternalActive('preview');
    }
    onSectionChange?.('preview');
  }, [focusPreviewSignal, activeSection, onSectionChange]);

  const resolvedVideoId =
    previewVideoId?.trim() ||
    video?.videoPack?.videoId?.trim() ||
    video?.videoPack?.pack?.video_id?.trim() ||
    '';

  const pack = video?.videoPack?.pack;
  const events: ExtractedEvent[] = studioPackExtractedEvents(pack);
  const topics: string[] = video?.insights?.topics ?? [];
  const actionItems = pack?.action_items ?? [];
  const stackTools = pack?.stack?.tools ?? [];
  const visualContext = pack?.visual_context;
  const keyframes = pack?.keyframes ?? [];
  const codeSnippets = pack?.code_snippets ?? [];
  const artifacts = pack?.artifacts ?? [];
  const architecture = pack?.architecture ?? null;
  const chapters = pack?.chapters ?? [];
  const linkedSop = video?.insights?.linkedSop;

  const proposedTools = stackTools.flatMap((tool) => {
    const name = tool.name?.trim();
    return name ? [{ ...tool, name }] : [];
  }).filter((tool, index, tools) => tools.findIndex((item) => item.name === tool.name) === index);
  const toolNames: string[] = proposedTools.map((tool) => tool.name);

  const isProcessing = video?.status === 'processing' && !video?.videoPack;
  const canRenderPreview = Boolean(
    resolvedVideoId && !isProcessing && (previewReady || Boolean(video?.videoPack)),
  );

  const packSegments = pack?.transcript?.segments ?? [];
  const parsedTranscript =
    packSegments.length === 0 ? parseTranscriptSegments(video?.transcript) : null;
  const seekableSegments =
    packSegments.length > 0
      ? packSegments.map((seg) => ({
          key: `pack-seg-${seg.idx}-${seg.start_s}`,
          startSeconds: seg.start_s,
          text: seg.text,
          idx: seg.idx,
        }))
      : parsedTranscript?.hasTimings
        ? parsedTranscript.segments.map((seg, idx) => ({
            key: seg.id,
            startSeconds: seg.startTime,
            text: seg.text,
            idx,
          }))
        : [];

  const hasTasksExtras = Boolean(
    reviewActions.length > 0 ||
      actionItems.length > 0 ||
      chapters.length > 0 ||
      events.length > 0 ||
      eventsEmptyMessage ||
      packWorkbench ||
      toolNames.length > 0 ||
      linkedSop?.steps?.length ||
      topics.length > 0,
  );
  const showBoundTasks = Boolean(pack?.grounded_spec) || !hasTasksExtras;

  const hasCodeContent = Boolean(
    codeSnippets.length > 0 ||
      artifacts.length > 0 ||
      architecture ||
      stackChecks.length > 0 ||
      specReview,
  );

  const copyCode = async (key: string, content: string) => {
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(content);
        setCopiedSnippet(key);
        window.setTimeout(() => {
          setCopiedSnippet((current) => (current === key ? null : current));
        }, 1800);
      }
    } catch {
      // Clipboard access can be denied in headless or restricted contexts.
    }
  };

  const downloadMarkdownPack = () => {
    const title = video?.title || resolvedVideoId || 'uvai-video-pack';
    const lines: string[] = [
      `# ${title}`,
      '',
      `- Source URL: ${video?.url || (resolvedVideoId ? `https://www.youtube.com/watch?v=${resolvedVideoId}` : 'Not loaded')}`,
      `- Pack ID: ${pack?.id || 'pending'}`,
      '',
      '## Chapters',
      ...(chapters.length > 0
        ? chapters.map(
            (c, i) => `- ${String(i + 1).padStart(2, '0')} (${formatSeconds(c.start)}): ${c.topic}`,
          )
        : ['- No extracted chapters yet.']),
      '',
      '## Tasks & Stack',
      ...(actionItems.length > 0
        ? actionItems.map((item, i) => `- [ ] ${i + 1}. ${item}`)
        : events.length > 0
          ? events.map((ev) => `- [ ] ${ev.title} (${ev.timestamp || '0:00'})`)
          : ['- Run analysis on a YouTube URL to populate bound tasks.']),
      ...(toolNames.length > 0 ? ['', `Stack Tools: ${toolNames.join(', ')}`] : []),
      '',
      '## Build & Launch Checklist',
      '- [ ] Verify responsive breakpoints (`720x900` half-screen and `1440x900` desktop)',
      '- [ ] Confirm WebMCP structured data, canonical link, and dark/light/high-contrast tokens',
      '- [ ] Verify stack checks and `/d/` preview in Desktop and Mobile frames',
      '- [ ] Complete Accessibility & Core Web Vitals QA before publishing',
    ];
    downloadMarkdownFile(`${resolvedVideoId || 'uvai-pack'}.md`, lines.join('\n'));
  };

  return (
    <div data-testid="studio-ide-output" className="flex h-full min-h-0 flex-col bg-[var(--uvai-bg)]">
      <div className="flex shrink-0 items-center justify-between gap-1 border-b border-[var(--uvai-border-strong)] bg-[var(--uvai-surface)] px-1.5 py-1 sm:px-2 sm:py-1.5">
        <div
          role="tablist"
          aria-label="Output sections"
          data-testid="studio-ide-output-tablist"
          className="flex min-w-0 flex-1 flex-nowrap items-center gap-0.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {SECTIONS.map((s) => {
            const isSelected = active === s.id;
            return (
              <button
                key={s.id}
                type="button"
                role="tab"
                id={`studio-ide-output-tab-${s.id}`}
                aria-selected={isSelected}
                aria-controls={`studio-ide-output-panel-${s.id}`}
                data-testid={`studio-ide-output-tab-${s.id}`}
                onClick={() => selectSection(s.id)}
                onKeyDown={(event) => {
                  const idx = SECTIONS.findIndex((item) => item.id === s.id);
                  const next =
                    event.key === 'ArrowRight'
                      ? SECTIONS[(idx + 1) % SECTIONS.length]
                      : event.key === 'ArrowLeft'
                        ? SECTIONS[(idx + SECTIONS.length - 1) % SECTIONS.length]
                        : event.key === 'Home'
                          ? SECTIONS[0]
                          : event.key === 'End'
                            ? SECTIONS[SECTIONS.length - 1]
                            : null;
                  if (next) {
                    event.preventDefault();
                    selectSection(next.id);
                    document.getElementById(`studio-ide-output-tab-${next.id}`)?.focus();
                  }
                }}
                className={`shrink-0 whitespace-nowrap rounded-md px-1.5 py-1 text-[10.5px] font-medium transition-colors sm:px-2 sm:text-[11px] lg:px-2.5 lg:text-xs ${
                  isSelected
                    ? 'bg-[#146ef5] text-white'
                    : 'bg-transparent text-[var(--uvai-ink-soft)] hover:bg-[var(--uvai-surface-warm)] hover:text-[var(--uvai-ink)]'
                }`}
              >
                {s.label}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={downloadMarkdownPack}
          data-testid="studio-download-md"
          title="Download Markdown spec & launch checklist for Claude, Cursor, or ChatGPT"
          aria-label="Download Markdown pack"
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-[var(--uvai-border-strong)] bg-[var(--uvai-bg)] px-1.5 py-1 font-mono text-[10px] font-semibold text-[var(--uvai-ink-soft)] transition hover:border-[var(--uvai-accent)] hover:text-[var(--uvai-ink)]"
        >
          <Download size={11} aria-hidden="true" />
          <span>.md</span>
        </button>
      </div>

      <div
        role="tabpanel"
        id={`studio-ide-output-panel-${active}`}
        aria-labelledby={`studio-ide-output-tab-${active}`}
        className="min-h-0 flex-1 overflow-y-auto bg-[var(--uvai-bg)] p-3 sm:p-4"
      >
        {active === 'preview' && (
          <div data-testid="studio-ide-output-preview" className="flex h-full min-h-[380px] flex-col gap-3">
            {canRenderPreview ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--uvai-border)] bg-[var(--uvai-surface)] px-3 py-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="inline-flex shrink-0 items-center rounded-full border border-[#1E9A80]/45 bg-[#1E9A80]/15 px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wide text-[#1E9A80]">
                      {previewReady ? 'Live' : 'Preview'}
                    </span>
                    <span className="hidden truncate font-mono text-xs text-[var(--uvai-ink-soft)] sm:inline">
                      /d/{resolvedVideoId}
                    </span>
                  </div>

                  <div
                    role="group"
                    aria-label="Preview viewport"
                    data-testid="studio-ide-preview-viewport-toggle"
                    className="mx-auto inline-flex shrink-0 items-center rounded-lg border border-[var(--uvai-border-strong)] bg-[var(--uvai-bg)] p-0.5"
                  >
                    <button
                      type="button"
                      aria-pressed={previewDevice === 'desktop'}
                      data-testid="studio-ide-preview-mode-desktop"
                      onClick={() => setPreviewDevice('desktop')}
                      className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                        previewDevice === 'desktop'
                          ? 'bg-[var(--uvai-surface-warm)] text-[var(--uvai-ink)] shadow-xs'
                          : 'text-[var(--uvai-ink-soft)] hover:text-[var(--uvai-ink)]'
                      }`}
                    >
                      <Monitor size={13} aria-hidden="true" />
                      <span>Desktop</span>
                    </button>
                    <button
                      type="button"
                      aria-pressed={previewDevice === 'mobile'}
                      data-testid="studio-ide-preview-mode-mobile"
                      onClick={() => setPreviewDevice('mobile')}
                      className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                        previewDevice === 'mobile'
                          ? 'bg-[var(--uvai-surface-warm)] text-[var(--uvai-ink)] shadow-xs'
                          : 'text-[var(--uvai-ink-soft)] hover:text-[var(--uvai-ink)]'
                      }`}
                    >
                      <Smartphone size={13} aria-hidden="true" />
                      <span>Mobile</span>
                    </button>
                  </div>

                  <div className="flex shrink-0 items-center gap-1.5">
                    {onBuildLive ? (
                      <button
                        type="button"
                        data-testid="studio-ide-preview-verify"
                        aria-label="Verify live preview"
                        title={`Compile the stored Video Pack for ${resolvedVideoId}.`}
                        disabled={buildBusy}
                        onClick={() => onBuildLive()}
                        className="inline-flex shrink-0 items-center gap-1 rounded-md border border-[var(--uvai-border-strong)] bg-[var(--uvai-bg)] px-2.5 py-1 text-xs font-medium text-[var(--uvai-ink-soft)] transition-colors hover:border-[var(--uvai-accent)] hover:text-[var(--uvai-ink)] disabled:opacity-40"
                      >
                        {buildBusy ? 'Verifying…' : 'Verify live'}
                      </button>
                    ) : null}
                    <a
                      href={'/d/' + encodeURIComponent(resolvedVideoId)}
                      target="_blank"
                      rel="noopener noreferrer"
                      data-testid="studio-ide-preview-open-tab"
                      className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface-warm)] px-2.5 py-1 text-xs font-medium text-[var(--uvai-ink)] transition-colors hover:border-[var(--uvai-accent)]"
                    >
                      <span>Open full preview</span>
                      <ExternalLink size={12} aria-hidden="true" />
                    </a>
                  </div>
                </div>

                <div
                  data-testid="studio-ide-preview-stage"
                  data-viewport={previewDevice}
                  className="flex min-h-[340px] flex-1 justify-center overflow-auto rounded-lg border border-[var(--uvai-border)] bg-[#0c0c0c] p-2 sm:p-3"
                >
                  <div
                    data-testid="studio-ide-preview-frame"
                    data-viewport={previewDevice}
                    style={previewDevice === 'mobile' ? { width: '390px', maxWidth: '100%' } : undefined}
                    className={
                      previewDevice === 'mobile'
                        ? 'mx-auto flex h-full min-h-[320px] w-full max-w-[390px] flex-col overflow-hidden rounded-[22px] border-2 border-[var(--uvai-border-strong)] bg-white shadow-xl'
                        : 'flex h-full min-h-[320px] w-full flex-col overflow-hidden rounded-md border border-[var(--uvai-border)] bg-white'
                    }
                  >
                    <iframe
                      src={'/d/' + encodeURIComponent(resolvedVideoId)}
                      title="Live web artifact preview"
                      data-testid="studio-ide-preview-iframe"
                      className="h-full min-h-[320px] w-full flex-1 border-0 bg-white"
                    />
                  </div>
                </div>
              </>
            ) : (
              <div className="uvai-card flex flex-col items-start gap-3 p-6">
                <p className="uvai-section-label">Live preview</p>
                <p className="text-sm font-medium text-[var(--uvai-ink)]">
                  {isProcessing
                    ? `Extracting Video Pack for ${resolvedVideoId}. The live web artifact will load here automatically when ready.`
                    : resolvedVideoId
                      ? `Analyze ${resolvedVideoId} to generate its live web artifact at /d/${resolvedVideoId}.`
                      : 'Analyze a YouTube video to generate and preview its interactive web artifact here.'}
                </p>
                {!isProcessing && resolvedVideoId && onBuildLive ? (
                  <button
                    type="button"
                    data-testid="studio-ide-preview-build-cta"
                    disabled={buildBusy}
                    onClick={() => onBuildLive()}
                    className="uvai-btn uvai-btn-primary"
                  >
                    {buildBusy ? 'Generating…' : 'Generate preview'}
                  </button>
                ) : null}
              </div>
            )}
          </div>
        )}

        {active === 'tasks' && (
          <div data-testid="studio-ide-output-tasks" className="flex flex-col gap-4">
            {showBoundTasks ? <StudioBoundTasks key={video?.id ?? 'empty'} pack={pack} /> : null}

            {(reviewActions.length > 0 || actionItems.length > 0) && (
              <section aria-label="Next actions" data-testid="studio-ide-output-actions" className="flex flex-col gap-3">
                <p className="uvai-section-label px-1">Next actions</p>
                <ul className="flex flex-col gap-3">
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
                          <div className="min-w-0 flex-1">
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
                              <div
                                data-testid="studio-proposal-detail"
                                className="mt-3 rounded-md border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface-warm)] p-3 text-xs text-[var(--uvai-ink-soft)]"
                              >
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
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-[var(--uvai-ink)]">{a.title}</p>
                            {a.priority ? (
                              <span className="rounded bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-mono text-[10px] uppercase text-[var(--uvai-ink-faint)]">
                                {a.priority}
                              </span>
                            ) : null}
                          </div>
                          {a.description ? (
                            <p className="mt-1 text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{a.description}</p>
                          ) : null}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(events.length > 0 || eventsEmptyMessage || packWorkbench) && (
              <section aria-label="Detected events" className="flex flex-col gap-3" data-testid="studio-ide-output-events">
                <p className="uvai-section-label px-1">Detected events</p>
                {events.length === 0 ? (
                  eventsEmptyMessage ? (
                    <EmptyNote text={eventsEmptyMessage} />
                  ) : null
                ) : (
                  <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    {events.map((e) => {
                      const seconds = parseTimestampToSeconds(e.timestamp);
                      return (
                        <li key={e.id} className="uvai-card p-4">
                          <div className="flex items-center justify-between gap-2">
                            <span className="inline-flex items-center gap-1.5 rounded bg-[var(--uvai-accent-soft)] px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--uvai-accent-ink)]">
                              <DotIcon />
                              {e.type}
                            </span>
                            {e.timestamp ? (
                              seconds !== null ? (
                                <SeekControl
                                  seconds={seconds}
                                  label={e.timestamp}
                                  videoId={resolvedVideoId}
                                  onSeek={onSeek}
                                  testId={`studio-event-seek-${e.id}`}
                                />
                              ) : (
                                <span className="font-mono text-[11px] text-[var(--uvai-ink-faint)]">{e.timestamp}</span>
                              )
                            ) : null}
                          </div>
                          <p className="mt-2 text-sm font-semibold text-[var(--uvai-ink)]">{e.title}</p>
                          {e.description ? (
                            <p className="mt-1 text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{e.description}</p>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                )}
                {packWorkbench}
              </section>
            )}

            {(chapters.length > 0 || toolNames.length > 0 || Boolean(linkedSop?.steps?.length)) && (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-12" data-testid="studio-ide-output-tools">
                {chapters.length > 0 ? (
                  <div
                    className={`uvai-card p-4 ${toolNames.length > 0 ? 'lg:col-span-7' : 'lg:col-span-12'}`}
                    data-testid="studio-pack-chapters"
                  >
                    <p className="uvai-section-label mb-3">Chapters</p>
                    <ol className="cc_toc flex flex-col gap-2">
                      {chapters.map((chapter, index) => (
                        <li key={`${chapter.topic}-${index}`} className="cc_toc-row uvai-doc-row">
                          <span className="cc_toc-num uvai-doc-icon">{String(index + 1).padStart(2, '0')}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-2">
                              <p className="cc_toc-title text-sm font-medium text-[var(--uvai-ink)]">{chapter.topic}</p>
                              <SeekControl
                                seconds={chapter.start}
                                label={`${formatSeconds(chapter.start)}–${formatSeconds(chapter.end)}`}
                                videoId={resolvedVideoId}
                                onSeek={onSeek}
                                testId={`studio-chapter-seek-${index}`}
                              />
                            </div>
                            {chapter.key_points?.length ? (
                              <p className="cc_toc-point mt-0.5 text-xs text-[var(--uvai-ink-soft)]">
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
                  <div className={`uvai-card p-4 ${chapters.length > 0 ? 'lg:col-span-5' : 'lg:col-span-12'}`}>
                    <p className="uvai-section-label mb-3">Proposed tools</p>
                    <ul className="flex flex-col gap-2">
                      {proposedTools.map((tool) => {
                        const card = studioProposedToolCard(tool);
                        return (
                          <li
                            key={card.title}
                            data-testid="studio-proposed-tool-card"
                            className="rounded-md border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface-warm)] p-3"
                          >
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--uvai-accent-ink)]">
                              {card.statusLabel}
                            </p>
                            <p className="mt-1 font-mono text-xs font-semibold text-[var(--uvai-ink)]">{card.title}</p>
                            <p className="mt-1 text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{card.detail}</p>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ) : null}

                {linkedSop?.steps?.length ? (
                  <div className="uvai-card p-4 lg:col-span-12">
                    <p className="uvai-section-label mb-3">Workflow steps</p>
                    <ol className="flex flex-col gap-2">
                      {linkedSop.steps.map((s, i) => (
                        <li key={s.id ?? i} className="uvai-doc-row">
                          <span className="uvai-doc-icon">{String(i + 1).padStart(2, '0')}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <p className="truncate text-sm font-medium text-[var(--uvai-ink)]">{s.title}</p>
                              {typeof s.timestamp === 'number' ? (
                                <SeekControl
                                  seconds={s.timestamp}
                                  label={formatSeconds(s.timestamp)}
                                  videoId={resolvedVideoId}
                                  onSeek={onSeek}
                                />
                              ) : null}
                            </div>
                            <p className="text-xs text-[var(--uvai-ink-faint)]">Step {i + 1}</p>
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}
              </div>
            )}

            {topics.length > 0 ? (
              <section aria-label="Key topics and takeaways" data-testid="studio-ide-output-topics" className="uvai-card p-4">
                <p className="uvai-section-label mb-3">Key topics & takeaways</p>
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
              </section>
            ) : null}
          </div>
        )}

        {active === 'code' && (
          <div data-testid="studio-ide-output-code" className="flex flex-col gap-4">
            {!hasCodeContent ? (
              <EmptyNote text="Run a video to generate starter code, G.A.T.E. architecture spec, and verification checks." />
            ) : (
              <>
                {codeSnippets.length > 0 ? (
                  <div className="uvai-card p-4" data-testid="studio-pack-code-snippets">
                    <p className="uvai-section-label mb-3">Code snippets & starter files</p>
                    <div className="flex flex-col gap-3">
                      {codeSnippets.map((snippet, index) => {
                        const snippetKey = `${snippet.path_hint ?? 'snippet'}-${index}`;
                        const isCopied = copiedSnippet === snippetKey;
                        return (
                          <div
                            key={snippetKey}
                            className="overflow-hidden rounded-md border border-[var(--uvai-border-strong)] bg-[#0a0a0a]"
                          >
                            <div className="flex items-center justify-between gap-2 border-b border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-3 py-1.5 font-mono text-[11px] text-[var(--uvai-ink-soft)]">
                              <span className="truncate">{snippet.path_hint || `snippet-${index + 1}`}</span>
                              <div className="flex shrink-0 items-center gap-2">
                                {snippet.lang ? (
                                  <span className="uppercase text-[var(--uvai-accent-ink)]">{snippet.lang}</span>
                                ) : null}
                                <button
                                  type="button"
                                  onClick={() => void copyCode(snippetKey, snippet.content)}
                                  aria-label={`Copy ${snippet.path_hint || `snippet ${index + 1}`}`}
                                  className="inline-flex items-center gap-1 rounded border border-[var(--uvai-border)] px-1.5 py-0.5 text-[10px] text-[var(--uvai-ink-soft)] hover:text-[var(--uvai-ink)]"
                                >
                                  {isCopied ? <Check size={11} aria-hidden="true" /> : <Copy size={11} aria-hidden="true" />}
                                  <span>{isCopied ? 'Copied' : 'Copy'}</span>
                                </button>
                              </div>
                            </div>
                            <pre className="max-h-64 overflow-auto p-3 font-mono text-xs leading-relaxed text-[#e5e5e5]">
                              {snippet.content}
                            </pre>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : null}

                {artifacts.length > 0 ? (
                  <div className="uvai-card p-4" data-testid="studio-pack-artifacts">
                    <p className="uvai-section-label mb-3">Starter deliverables</p>
                    <ul className="space-y-2">
                      {artifacts.map((artifact) => (
                        <li key={artifact.path_hint} className="uvai-doc-row">
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-mono text-xs font-semibold text-[var(--uvai-accent-ink)]">
                              {artifact.path_hint}
                            </p>
                            <p className="mt-0.5 text-xs text-[var(--uvai-ink-soft)]">{artifact.purpose}</p>
                            <p className="mt-0.5 truncate font-mono text-[11px] text-[var(--uvai-ink-faint)]">
                              {artifact.interface}
                            </p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {architecture ? (
                  <div className="uvai-card p-4" data-testid="studio-pack-architecture">
                    <p className="uvai-section-label mb-3">Architecture</p>
                    {architecture.summary ? (
                      <p className="text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{architecture.summary}</p>
                    ) : null}
                    {architecture.stages.length > 0 ? (
                      <ol className="mt-3 space-y-1.5 text-xs text-[var(--uvai-ink-soft)]">
                        {architecture.stages.map((stage, index) => (
                          <li key={stage.id ?? index} className="flex gap-2">
                            <span className="font-mono text-[11px] text-[var(--uvai-accent-ink)]">
                              {String(index + 1).padStart(2, '0')}
                            </span>
                            <div>
                              <span className="font-medium text-[var(--uvai-ink)]">{stage.name}</span>
                              {stage.description ? ` — ${stage.description}` : ''}
                            </div>
                          </li>
                        ))}
                      </ol>
                    ) : null}
                    {architecture.mermaid ? (
                      <pre className="mt-3 max-h-56 overflow-auto rounded-md border border-[var(--uvai-border-strong)] bg-[#0a0a0a] p-3 font-mono text-[11px] leading-5 text-[#e5e5e5]">
                        {architecture.mermaid}
                      </pre>
                    ) : null}
                  </div>
                ) : null}

                {stackChecks.length > 0 ? (
                  <div className="uvai-card p-4" data-testid="studio-stack-checks">
                    <p className="uvai-section-label mb-3">Verification checklist</p>
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

                <div data-testid="studio-ide-output-spec">
                  {specReview ?? <EmptyNote text="No grounded specification on this pack yet." />}
                </div>
              </>
            )}
          </div>
        )}

        {active === 'transcript' && (
          <div data-testid="studio-ide-output-transcript" className="flex flex-col gap-4">
            <div data-testid="studio-transcript-body" className="uvai-card p-4">
              {seekableSegments.length > 0 ? (
                <ol className="flex flex-col gap-2" aria-label="Timestamped transcript">
                  {seekableSegments.map((seg) => (
                    <li
                      key={seg.key}
                      className="flex items-start gap-3 rounded-md border border-transparent px-2 py-1.5 transition-colors hover:border-[var(--uvai-border)] hover:bg-[var(--uvai-surface-warm)]"
                    >
                      <SeekControl
                        seconds={seg.startSeconds}
                        label={formatSeconds(seg.startSeconds)}
                        videoId={resolvedVideoId}
                        onSeek={onSeek}
                        testId={`studio-transcript-seek-${seg.idx}`}
                      />
                      <span className="min-w-0 flex-1 text-xs leading-relaxed text-[var(--uvai-ink-soft)]">
                        {seg.text}
                      </span>
                    </li>
                  ))}
                </ol>
              ) : video?.transcript?.trim() ? (
                <p className="whitespace-pre-wrap text-xs leading-relaxed text-[var(--uvai-ink-soft)]">
                  {video.transcript}
                </p>
              ) : video?.failure?.message ? (
                <div className="flex flex-col items-start gap-2">
                  <p className="text-xs text-[var(--uvai-danger-ink)]">{video.failure.message}</p>
                  {showTranscriptRetry && onRetryTranscript ? (
                    <button
                      type="button"
                      data-testid="studio-transcript-pane-retry"
                      onClick={onRetryTranscript}
                      className="uvai-btn !px-3 !py-1 !text-xs"
                    >
                      Retry transcript
                    </button>
                  ) : null}
                </div>
              ) : transcriptEta ? (
                <div className="flex flex-col gap-1 py-2">
                  <p data-testid="studio-transcript-eta" className="text-sm font-medium text-[var(--uvai-ink)]">
                    {transcriptEta}
                  </p>
                  <p className="text-xs text-[var(--uvai-ink-soft)]">Waiting on captions — no invented text.</p>
                </div>
              ) : (
                <p className="py-4 text-center text-xs text-[var(--uvai-ink-faint)]">Nothing yet.</p>
              )}
            </div>

            {(visualContext?.summary || keyframes.length > 0) && (
              <section aria-label="Visual keyframes" data-testid="studio-ide-output-keyframes" className="flex flex-col gap-3">
                <p className="uvai-section-label px-1">Visual keyframes</p>
                {visualContext?.summary ? (
                  <div className="uvai-card p-4">
                    <p className="uvai-section-label mb-2">Visual summary</p>
                    <p className="text-xs leading-relaxed text-[var(--uvai-ink-soft)]">{visualContext.summary}</p>
                  </div>
                ) : null}
                {keyframes.length > 0 ? (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {keyframes.map((k, i) => (
                      <figure key={`${k.t_s ?? i}-${i}`} className="uvai-card overflow-hidden !p-0">
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
                            {k.t_s != null ? formatSeconds(k.t_s) : `Frame ${i + 1}`}
                          </div>
                        )}
                        <figcaption className="flex flex-col gap-1.5 border-t border-[var(--uvai-border)] px-3 py-2 text-[11px] leading-snug text-[var(--uvai-ink-soft)]">
                          {k.t_s != null ? (
                            <div>
                              <SeekControl
                                seconds={k.t_s}
                                label={formatSeconds(k.t_s)}
                                videoId={resolvedVideoId}
                                onSeek={onSeek}
                                testId={`studio-keyframe-seek-${i}`}
                              />
                            </div>
                          ) : null}
                          {k.desc ? <span>{k.desc}</span> : null}
                        </figcaption>
                      </figure>
                    ))}
                  </div>
                ) : null}
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SeekControl({
  seconds,
  label,
  videoId,
  onSeek,
  testId,
}: {
  seconds: number;
  label: string;
  videoId?: string;
  onSeek?: (seconds: number) => void;
  testId?: string;
}) {
  const safeSeconds = Number.isFinite(seconds) && seconds >= 0 ? Math.floor(seconds) : 0;
  if (onSeek) {
    return (
      <button
        type="button"
        data-testid={testId}
        onClick={() => onSeek(safeSeconds)}
        title={`Jump player to ${label}`}
        aria-label={`Seek to ${label}`}
        className="inline-flex shrink-0 items-center gap-1 rounded border border-[var(--uvai-border-strong)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-mono text-[11px] font-medium text-[var(--uvai-accent-ink)] transition-colors hover:border-[var(--uvai-accent)] hover:text-[var(--uvai-ink)]"
      >
        <Play size={10} aria-hidden="true" />
        <span>{label}</span>
      </button>
    );
  }
  if (videoId) {
    return (
      <a
        href={`https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}&t=${safeSeconds}s`}
        target="_blank"
        rel="noopener noreferrer"
        data-testid={testId}
        className="inline-flex shrink-0 items-center gap-1 rounded border border-[var(--uvai-border)] bg-[var(--uvai-surface-warm)] px-2 py-0.5 font-mono text-[11px] text-[var(--uvai-accent-ink)] hover:border-[var(--uvai-accent)]"
      >
        <Play size={10} aria-hidden="true" />
        <span>{label}</span>
      </a>
    );
  }
  return (
    <span
      data-testid={testId}
      className="shrink-0 font-mono text-[11px] text-[var(--uvai-ink-faint)]"
    >
      {label}
    </span>
  );
}

function EmptyNote({ text }: { text: string }) {
  return (
    <div className="uvai-card p-6 text-center">
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

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}
