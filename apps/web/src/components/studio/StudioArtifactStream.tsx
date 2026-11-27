'use client';

import { CheckCircle2, Circle, Code2, Loader2, XCircle } from 'lucide-react';
import type {
  StudioArtifactStreamPhase,
  StudioArtifactStreamPreview,
  StudioArtifactStreamRow,
} from '@/lib/studio-artifact-stream';

export type StudioArtifactStreamProps = {
  phase: StudioArtifactStreamPhase;
  rows: StudioArtifactStreamRow[];
  preview?: StudioArtifactStreamPreview | null;
  statusText?: string;
  videoId?: string | null;
};

function RowIcon({ state }: { state: StudioArtifactStreamRow['state'] }) {
  switch (state) {
    case 'done':
      return <CheckCircle2 size={13} className="shrink-0 text-[#1e9a80]" aria-hidden="true" />;
    case 'active':
      return (
        <Loader2
          size={13}
          className="shrink-0 text-[var(--uvai-accent-ink)] motion-safe:animate-spin"
          aria-hidden="true"
        />
      );
    case 'failed':
      return <XCircle size={13} className="shrink-0 text-[var(--uvai-danger-ink)]" aria-hidden="true" />;
    case 'skeletal':
      return (
        <span
          className="studio-artifact-stream__bone studio-artifact-stream__bone--icon"
          aria-hidden="true"
        />
      );
    case 'pending':
      return <Circle size={13} className="shrink-0 text-[var(--uvai-ink-faint)]" aria-hidden="true" />;
    default: {
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}

/**
 * Cut 3 — pack-forming artifact in the Agents chat stream (motion #1).
 * Skeletal panel → extract rows fill from real stages → settle into real
 * architecture / artifacts / stack preview. Never invents pack content.
 */
export default function StudioArtifactStream({
  phase,
  rows,
  preview = null,
  statusText,
  videoId,
}: StudioArtifactStreamProps) {
  if (phase === 'hidden' || rows.length === 0) return null;

  const title =
    phase === 'settled'
      ? 'Video Pack ready'
      : phase === 'failed'
        ? 'Extraction failed'
        : 'Extracting Video Pack…';

  const detail =
    statusText?.trim() ||
    (phase === 'settled'
      ? 'Architecture, artifacts, and stack from the video — no invented pack content.'
      : phase === 'failed'
        ? 'Retry from the stage controls. Chat stays locked until a real pack lands.'
        : 'Building transcript, chapters, events, and runnable specs. Chat unlocks when ready.');

  const showPreview =
    (phase === 'settled' || phase === 'filling') && preview !== null;

  return (
    <article
      data-testid="studio-artifact-stream"
      data-phase={phase}
      data-video-id={videoId ?? undefined}
      role="status"
      aria-live="polite"
      className="studio-artifact-stream"
    >
      <header className="studio-artifact-stream__head">
        <div
          className="studio-artifact-stream__badge"
          data-state={phase}
          aria-hidden="true"
        >
          {phase === 'settled' ? (
            <Code2 size={14} />
          ) : phase === 'failed' ? (
            <XCircle size={14} />
          ) : (
            <Loader2 size={14} className="motion-safe:animate-spin" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="studio-artifact-stream__title">{title}</p>
          <p className="studio-artifact-stream__detail">{detail}</p>
        </div>
      </header>

      <ol className="studio-artifact-stream__rows" aria-label="Extract stages">
        {rows.map((row) => (
          <li
            key={row.id}
            data-step={row.id}
            data-state={row.state}
            className="studio-artifact-stream__row"
          >
            <RowIcon state={row.state} />
            {row.state === 'skeletal' ? (
              <span
                className="studio-artifact-stream__bone studio-artifact-stream__bone--label"
                aria-hidden="true"
              />
            ) : (
              <span className="studio-artifact-stream__label">{row.label}</span>
            )}
          </li>
        ))}
      </ol>

      {showPreview && preview ? (
        <div
          data-testid="studio-artifact-stream-preview"
          className="studio-artifact-stream__preview"
        >
          {preview.architectureSummary || preview.architectureStages.length > 0 ? (
            <section data-testid="studio-artifact-stream-architecture">
              <h3 className="studio-artifact-stream__preview-label">Architecture</h3>
              {preview.architectureSummary ? (
                <p className="studio-artifact-stream__preview-body">
                  {preview.architectureSummary}
                </p>
              ) : null}
              {preview.architectureStages.length > 0 ? (
                <ol className="studio-artifact-stream__preview-list">
                  {preview.architectureStages.map((stage) => (
                    <li key={stage.id}>{stage.name}</li>
                  ))}
                </ol>
              ) : null}
            </section>
          ) : null}

          {preview.artifacts.length > 0 ? (
            <section data-testid="studio-artifact-stream-artifacts">
              <h3 className="studio-artifact-stream__preview-label">Artifacts</h3>
              <ul className="studio-artifact-stream__preview-list">
                {preview.artifacts.map((artifact) => (
                  <li key={artifact.path_hint}>
                    <code>{artifact.path_hint}</code>
                    {artifact.purpose ? (
                      <span className="studio-artifact-stream__preview-soft">
                        {' '}
                        — {artifact.purpose}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {preview.tools.length > 0 ? (
            <section data-testid="studio-artifact-stream-tools">
              <h3 className="studio-artifact-stream__preview-label">Stack</h3>
              <ul className="studio-artifact-stream__preview-list">
                {preview.tools.map((tool) => (
                  <li key={tool.name}>{tool.name}</li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
