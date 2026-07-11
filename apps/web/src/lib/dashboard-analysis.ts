import type { Video } from '@/store/dashboard-types';

/** True when the pipeline finished but returned no usable intelligence payload. */
export function isThinDashboardAnalysis(video: Pick<Video, 'insights' | 'transcript' | 'events'>): boolean {
  const summary = video.insights?.summary?.trim() ?? '';
  const genericSummary =
    summary === 'Analysis complete' ||
    summary.startsWith('Local fallback package') ||
    summary.startsWith('Deploy handoff prepared');
  const hasActions = (video.insights?.actions?.length ?? 0) > 0;
  const hasTopics = (video.insights?.topics?.length ?? 0) > 0;
  const hasEvents = (video.events?.length ?? 0) > 0;
  const transcript = video.transcript?.trim() ?? '';
  const hasTranscript = transcript.length >= 50;

  return genericSummary && !hasActions && !hasTopics && !hasEvents && !hasTranscript;
}

export function hasRichDashboardInsights(
  video: Pick<Video, 'insights' | 'transcript' | 'events'>,
): boolean {
  if (!video.insights) return false;
  if (isThinDashboardAnalysis(video)) return false;
  return (
    video.insights.summary !== 'Analysis complete' ||
    video.insights.actions.length > 0 ||
    (video.transcript?.trim().length ?? 0) >= 50
  );
}