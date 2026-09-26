/**
 * Studio workbench pane model (layout/selection only).
 *
 * The Studio result view is a single-pane workbench: a left outline picks one
 * main pane at a time instead of stacking the whole pack (transcript, events,
 * SOP, stack, architecture, and raw JSON) into one enormous scroll. These pure
 * helpers decide which tabs exist, which pane is active, how the collapsed
 * transcript summarizes itself, and how to de-duplicate the same insight across
 * the Events, SOP, and Summary surfaces. No React, no side effects.
 */

export type StudioPaneId =
  | 'video'
  | 'transcript'
  | 'actions'
  | 'events'
  | 'workflow'
  | 'spec'
  | 'summary'
  | 'pack';

export interface StudioPaneTab {
  id: StudioPaneId;
  label: string;
}

export interface StudioWorkbenchContent {
  hasTranscript: boolean;
  hasActions: boolean;
  hasEvents: boolean;
  hasWorkflow: boolean;
  hasSpec: boolean;
  hasSummary: boolean;
  hasPack: boolean;
}

const PANE_ORDER: ReadonlyArray<{ id: StudioPaneId; label: string; key?: keyof StudioWorkbenchContent }> = [
  { id: 'video', label: 'Video' },
  { id: 'transcript', label: 'Transcript', key: 'hasTranscript' },
  { id: 'actions', label: 'Actions', key: 'hasActions' },
  { id: 'events', label: 'Events', key: 'hasEvents' },
  { id: 'workflow', label: 'Workflow', key: 'hasWorkflow' },
  { id: 'spec', label: 'Spec', key: 'hasSpec' },
  { id: 'summary', label: 'Summary', key: 'hasSummary' },
  { id: 'pack', label: 'Pack', key: 'hasPack' },
];

/**
 * Build the workbench tab list. `Video` is always first and default; every
 * other pane appears only when it has content, so the default paint is just the
 * video + short status rather than a stacked dump.
 */
export function studioWorkbenchTabs(content: StudioWorkbenchContent): StudioPaneTab[] {
  return PANE_ORDER.filter((pane) => !pane.key || content[pane.key]).map(({ id, label }) => ({
    id,
    label,
  }));
}

/** Keep the requested pane only if it still has a tab; otherwise fall back to the first (Video). */
export function studioResolveActivePane(
  requested: StudioPaneId | null | undefined,
  tabs: StudioPaneTab[],
): StudioPaneId {
  if (requested && tabs.some((tab) => tab.id === requested)) {
    return requested;
  }
  return tabs[0]?.id ?? 'video';
}

/** Map a left-outline section id (video/transcript/result/pack/sop/chapter/…) to a pane. */
export function studioOutlineSectionToPane(sectionId: string): StudioPaneId | null {
  if (sectionId === 'studio-shell-video') return 'video';
  if (sectionId === 'studio-shell-transcript') return 'transcript';
  if (sectionId === 'studio-shell-result' || sectionId === 'studio-shell-spec') return 'spec';
  if (sectionId === 'studio-shell-pack') return 'pack';
  if (sectionId === 'studio-shell-sop' || sectionId === 'studio-shell-workflow') return 'workflow';
  if (sectionId === 'studio-shell-events') return 'events';
  if (sectionId === 'studio-shell-summary') return 'summary';
  if (sectionId === 'studio-shell-actions') return 'actions';
  if (sectionId.startsWith('studio-shell-chapter-')) return 'video';
  return null;
}

/** Section id used by the left outline for a given pane (inverse of the mapping above). */
export function studioPaneToOutlineSection(pane: StudioPaneId): string {
  if (pane === 'spec') return 'studio-shell-result';
  if (pane === 'workflow') return 'studio-shell-sop';
  return `studio-shell-${pane}`;
}

/**
 * Collapsed-transcript summary line. When a transcript exists we show
 * "<N> words · Transcript ready"; otherwise we surface the live stage label so
 * the pane never has to print every segment just to say something.
 */
export function studioTranscriptSummaryLabel(input: {
  transcript?: string | null;
  stageLabel: string;
}): string {
  const words = countTranscriptWords(input.transcript);
  if (words > 0) {
    return `${words} words · Transcript ready`;
  }
  return input.stageLabel;
}

export function countTranscriptWords(transcript?: string | null): number {
  const trimmed = transcript?.trim() ?? '';
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

function normalizeInsight(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

/**
 * De-duplicate the SOP list against the Events list so the same five insights
 * do not appear verbatim in both. Events own an insight first; a SOP step whose
 * title collides with an event title is dropped from the SOP surface.
 */
export function studioDedupeSopStepsAgainstEvents<
  E extends { title?: string | null },
  S extends { title?: string | null },
>(events: readonly E[], sopSteps: readonly S[]): S[] {
  const eventTitles = new Set(
    events.map((event) => normalizeInsight(event.title ?? '')).filter((title) => title.length > 0),
  );
  return sopSteps.filter((step) => {
    const title = normalizeInsight(step.title ?? '');
    return title.length === 0 || !eventTitles.has(title);
  });
}

/**
 * A Summary that only echoes the already-listed events/SOP titles is noise on a
 * single-pane workbench. Return the summary only when it adds prose beyond the
 * list items it would otherwise repeat.
 */
export function studioSummaryIsRedundant(
  summary: string | null | undefined,
  listedTitles: readonly (string | null | undefined)[],
): boolean {
  const text = normalizeInsight(summary ?? '');
  if (!text) return true;
  const titles = listedTitles
    .map((title) => normalizeInsight(title ?? ''))
    .filter((title) => title.length > 0);
  if (titles.length === 0) return false;
  // Redundant when the summary is just the titles concatenated (any order/join).
  const joined = normalizeInsight(titles.join(' '));
  const stripped = normalizeInsight(text.replace(/[.,;:]/g, ' '));
  return stripped === joined || titles.every((title) => text === title);
}
