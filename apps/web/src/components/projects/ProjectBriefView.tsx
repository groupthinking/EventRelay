'use client';

import Link from 'next/link';
import type { EmittedVideoPack } from '@/lib/emit-video-pack';
import { downloadTextFile } from '@/lib/download-file';
import {
  buildProjectBrief,
  formatProjectBriefMarkdown,
} from '@/lib/projects/project-workspace';
import type { ProjectRecord } from '@/lib/projects/project-types';
import { formatSeconds } from '@/lib/timestamp';

export type PackStatus = 'loading' | 'ready' | 'processing' | 'missing' | 'error';

type Props = {
  project: ProjectRecord;
  pack: EmittedVideoPack | null;
  packStatus: PackStatus;
  packError: string | null;
  onExtractPack: () => void;
  onOpenChapter: (chapterNumber: number, startSeconds: number) => void;
};

/** Deterministic Brief: every section comes from real pack fields; empty sections say so. */
export default function ProjectBriefView({
  project,
  pack,
  packStatus,
  packError,
  onExtractPack,
  onOpenChapter,
}: Props) {
  const brief = buildProjectBrief(project, pack);
  const extracting = packStatus === 'processing' || packStatus === 'loading';

  return (
    <div className="pw-main" data-testid="project-brief">
      {!pack ? (
        <div className="pw-banner" data-testid="project-brief-no-pack">
          <span>
            {packStatus === 'loading'
              ? 'Checking for a stored Video Pack…'
              : packStatus === 'processing'
                ? 'The Video Pack is being extracted. This page updates when it is ready.'
                : packStatus === 'error'
                  ? (packError ?? 'The Video Pack could not be loaded.')
                  : 'No Video Pack has been extracted for this video yet.'}
          </span>
          <button
            type="button"
            className="pw-btn"
            data-primary="true"
            disabled={extracting}
            onClick={onExtractPack}
          >
            Extract Video Pack
          </button>
        </div>
      ) : null}

      <section className="pw-card" aria-labelledby="brief-summary-heading">
        <h2 id="brief-summary-heading">Summary</h2>
        {brief.summary ? <p>{brief.summary}</p> : <p className="pw-muted">No summary was extracted.</p>}
        <div className="pw-badges">
          <span className="pw-badge" data-testid="brief-caption-source">
            {brief.captionSource}
          </span>
          {brief.sourceHash ? <span className="pw-badge">{brief.sourceHash.slice(0, 12)}</span> : null}
        </div>
        <div>
          <button
            type="button"
            className="pw-btn"
            data-testid="brief-download-md"
            onClick={() =>
              downloadTextFile(
                `${project.videoId}-brief.md`,
                formatProjectBriefMarkdown(brief),
                'text/markdown;charset=utf-8',
              )
            }
          >
            Download Brief (.md)
          </button>
        </div>
      </section>

      <div className="pw-grid-2">
        <section className="pw-card" aria-labelledby="brief-chapters-heading">
          <h2 id="brief-chapters-heading">Chapters</h2>
          {brief.chapters.length === 0 ? (
            <p className="pw-muted">No chapters were extracted.</p>
          ) : (
            <ol className="pw-list" data-testid="brief-chapters">
              {brief.chapters.map((chapter) => (
                <li key={chapter.number}>
                  <button
                    type="button"
                    className="pw-btn"
                    data-testid={`brief-chapter-${chapter.number}`}
                    onClick={() => onOpenChapter(chapter.number, chapter.start)}
                  >
                    {chapter.number}. {chapter.topic}
                    <span className="pw-muted">
                      {formatSeconds(chapter.start)}–{formatSeconds(chapter.end)}
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="pw-card" aria-labelledby="brief-stack-heading">
          <h2 id="brief-stack-heading">Detected stack</h2>
          {brief.stack.length === 0 ? (
            <p className="pw-muted">No tools were detected.</p>
          ) : (
            <ul className="pw-list" data-testid="brief-stack">
              {brief.stack.map((tool) => (
                <li key={tool.name}>
                  <strong>{tool.name}</strong>
                  {tool.kind ? <span className="pw-muted"> · {tool.kind}</span> : null}
                  {tool.evidence ? <div className="pw-muted">{tool.evidence}</div> : null}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="pw-card" aria-labelledby="brief-actions-heading">
          <h2 id="brief-actions-heading">Action items</h2>
          {brief.actionItems.length === 0 ? (
            <p className="pw-muted">No action items were extracted.</p>
          ) : (
            <ul className="pw-list" data-testid="brief-actions">
              {brief.actionItems.map((item) => (
                <li key={`${item.title}-${item.description}`}>
                  <strong>{item.title}</strong>
                  {item.priority ? <span className="pw-muted"> · {item.priority}</span> : null}
                  <div className="pw-muted">{item.description}</div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="pw-card" aria-labelledby="brief-questions-heading">
          <h2 id="brief-questions-heading">Open questions</h2>
          {brief.openQuestions.length === 0 ? (
            <p className="pw-muted">None recorded.</p>
          ) : (
            <ul className="pw-list" data-testid="brief-questions">
              {brief.openQuestions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <p className="pw-sub">
        Source:{' '}
        <a href={project.sourceUrl} target="_blank" rel="noopener noreferrer">
          {project.sourceUrl}
        </a>{' '}
        · <Link href={`/studio?video=${encodeURIComponent(project.sourceUrl)}`}>Open in Studio</Link>
      </p>
    </div>
  );
}
