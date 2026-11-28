'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Play, Quote } from 'lucide-react';
import StudioIdeChat from '@/components/studio/StudioIdeChat';
import StudioPackTimeline from '@/components/studio/StudioPackTimeline';
import { downloadTextFile } from '@/lib/download-file';
import type { EmittedVideoPack } from '@/lib/emit-video-pack';
import {
  filterTranscriptRows,
  formatTranscriptJson,
  formatTranscriptMarkdown,
  resolvePackTranscriptSegments,
  type ProjectFolder,
} from '@/lib/projects/project-workspace';
import type { ProjectRecord } from '@/lib/projects/project-types';
import { buildEmbedUrl, formatSeconds } from '@/lib/timestamp';
import { formatSrt, formatVtt, resolveCaptionSourceLabel } from '@/lib/transcript-export';
import type { PackStatus } from './ProjectBriefView';
import '@/styles/studio-cards.css';
import '@/styles/studio-workbench.css';

const SAFE_VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
const YOUTUBE_ORIGIN = 'https://www.youtube-nocookie.com';

type SourceTab = 'transcript' | 'subtitles' | 'chapters';
type RightTab = 'notes' | 'chat';
type SubtitleFormat = 'srt' | 'vtt';

const SOURCE_TABS: ReadonlyArray<{ id: SourceTab; label: string }> = [
  { id: 'transcript', label: 'Transcript' },
  { id: 'subtitles', label: 'Subtitles' },
  { id: 'chapters', label: 'Chapters' },
];

const MORE_ACTIONS: ReadonlyArray<{ id: string; label: string; prompt: string }> = [
  { id: 'actions', label: 'Extract action items', prompt: 'Extract action items from this video' },
  { id: 'stack', label: 'Extract tools & stack', prompt: 'Extract tools, commands & stack' },
  { id: 'sop', label: 'Draft an SOP', prompt: 'Draft a step-by-step SOP from this video' },
  { id: 'spec', label: 'Build implementation spec', prompt: 'Plan a build from this Video Pack' },
];

type Props = {
  project: ProjectRecord;
  pack: EmittedVideoPack | null;
  packStatus: PackStatus;
  folder: ProjectFolder;
  /** `?t=` deep-link seconds. */
  t: number | null;
  onSeekUrl: (seconds: number) => void;
  onSelectFolder: (folderId: string) => void;
  onExtractPack: () => void;
};

/** YTToText-style run view: player + transcript tools on the left, AI notes / chat on the right. */
export default function ProjectRunView({
  project,
  pack,
  packStatus,
  folder,
  t,
  onSeekUrl,
  onSelectFolder,
  onExtractPack,
}: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const loadedRef = useRef(false);
  const tRef = useRef<number | null>(t);
  const [sourceTab, setSourceTab] = useState<SourceTab>('transcript');
  const [rightTab, setRightTab] = useState<RightTab>('notes');
  const [subtitleFormat, setSubtitleFormat] = useState<SubtitleFormat>('srt');
  const [query, setQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playerDuration, setPlayerDuration] = useState<number | null>(null);
  const [quoteSignal, setQuoteSignal] = useState<{ text: string; timestampSec?: number; nonce: number } | null>(null);
  const [quickAction, setQuickAction] = useState<{ prompt: string; nonce: number } | null>(null);

  // CodeQL-safe sink: only an allowlisted 11-char id ever reaches the iframe src.
  const safeVideoId = SAFE_VIDEO_ID.exec(project.videoId)?.[0] ?? null;
  const embedSrc = safeVideoId
    ? buildEmbedUrl(encodeURIComponent(safeVideoId), typeof window !== 'undefined' ? window.location.origin : undefined)
    : null;

  const allRows = useMemo(() => resolvePackTranscriptSegments(pack), [pack]);
  const rows = useMemo(() => filterTranscriptRows(allRows, folder, query), [allRows, folder, query]);
  const exportSegments = useMemo(
    () => rows.map((row) => ({ text: row.text, start: row.start, duration: row.duration })),
    [rows],
  );
  const captionSource = resolveCaptionSourceLabel({
    timedSegmentCount: allRows.length,
    hasTranscriptText: Boolean(pack?.transcript?.full_text?.trim()) && allRows.length > 0,
  });
  const chapters = pack?.chapters ?? [];
  const subtitleText = subtitleFormat === 'srt' ? formatSrt(exportSegments) : formatVtt(exportSegments);

  const moments = useMemo(() => {
    if (!pack) return [] as Array<{ t: number; label: string }>;
    const items: Array<{ t: number; label: string }> = (pack.chapters ?? []).map((chapter) => ({
      t: chapter.start,
      label: chapter.topic,
    }));
    for (const frame of pack.keyframes ?? []) {
      const desc = frame.desc?.trim();
      if (desc) items.push({ t: frame.t_s, label: desc });
    }
    return items.sort((a, b) => a.t - b.t).slice(0, 6);
  }, [pack]);

  const postSeek = useCallback((seconds: number) => {
    const frame = iframeRef.current?.contentWindow;
    if (!frame || !loadedRef.current) return;
    frame.postMessage(JSON.stringify({ event: 'command', func: 'seekTo', args: [seconds, true] }), YOUTUBE_ORIGIN);
  }, []);

  const seek = useCallback(
    (seconds: number) => {
      postSeek(seconds);
      onSeekUrl(seconds);
    },
    [onSeekUrl, postSeek],
  );

  useEffect(() => {
    tRef.current = t;
    if (t != null) postSeek(t);
  }, [t, postSeek]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== YOUTUBE_ORIGIN || event.source !== iframeRef.current?.contentWindow) return;
      if (typeof event.data !== 'string') return;
      try {
        const data = JSON.parse(event.data) as { event?: string; info?: { currentTime?: number; duration?: number } };
        if (data.event !== 'infoDelivery' || !data.info) return;
        if (typeof data.info.currentTime === 'number' && Number.isFinite(data.info.currentTime)) {
          setCurrentTime(data.info.currentTime);
        }
        if (typeof data.info.duration === 'number' && data.info.duration > 0) {
          setPlayerDuration(data.info.duration);
        }
      } catch {
        // Ignore non-JSON player messages.
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  const askChat = (prompt: string) => {
    setRightTab('chat');
    setQuickAction((prev) => ({ prompt, nonce: (prev?.nonce ?? 0) + 1 }));
  };

  const quoteLine = (text: string, timestampSec?: number) => {
    setRightTab('chat');
    setQuoteSignal((prev) => ({ text, timestampSec, nonce: (prev?.nonce ?? 0) + 1 }));
  };

  const copyTranscript = async () => {
    try {
      if (rows.length > 0 && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(rows.map((row) => row.text).join('\n'));
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1800);
      }
    } catch {
      // Clipboard blocked: leave the button unchanged.
    }
  };

  const base = project.videoId;
  const noRows = rows.length === 0;
  const extracting = packStatus === 'processing' || packStatus === 'loading';

  return (
    <div className="pw-run" data-testid="project-run">
      <div className="pw-run-col">
        {embedSrc ? (
          <iframe
            ref={iframeRef}
            title={`Player for ${project.title}`}
            className="pw-player"
            src={embedSrc}
            allow="encrypted-media; picture-in-picture"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
            onLoad={() => {
              loadedRef.current = true;
              iframeRef.current?.contentWindow?.postMessage(
                JSON.stringify({ event: 'listening', id: 1 }),
                YOUTUBE_ORIGIN,
              );
              if (tRef.current != null) postSeek(tRef.current);
            }}
          />
        ) : (
          <p className="pw-banner" role="alert">
            This project has an invalid video id, so the player is unavailable.
          </p>
        )}

        <div className="pw-meta" data-testid="project-run-meta">
          <strong>{project.title}</strong>
          <span className="pw-badge">{pack?.transcript?.language ?? 'Language unknown'}</span>
          <span className="pw-badge" data-testid="project-run-caption-source">
            {captionSource}
          </span>
          {allRows.length > 0 ? <span className="pw-badge">{allRows.length} lines</span> : null}
          {folder.id !== 'all' ? (
            <span className="pw-badge" data-testid="project-run-folder-chip">
              {folder.label} · {folder.topic}
              <button
                type="button"
                className="pw-btn"
                aria-label="Clear folder filter"
                onClick={() => onSelectFolder('all')}
              >
                Clear
              </button>
            </span>
          ) : null}
        </div>

        {pack ? (
          <div data-testid="studio-timeline-bar">
            <StudioPackTimeline
              pack={pack}
              canSeek={Boolean(embedSrc)}
              onSeek={seek}
              currentTime={currentTime}
              playerDuration={playerDuration}
            />
          </div>
        ) : null}

        <div className="pw-card">
          <div className="pw-tabs" role="tablist" aria-label="Run source views">
            {SOURCE_TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                id={`run-tab-${tab.id}`}
                aria-selected={sourceTab === tab.id}
                aria-controls="run-source-panel"
                className="pw-tab"
                onClick={() => setSourceTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {sourceTab !== 'chapters' ? (
            <div className="pw-toolbar">
              <label htmlFor="project-transcript-search" className="sr-only">
                Search transcript
              </label>
              <input
                id="project-transcript-search"
                name="projectTranscriptSearch"
                type="search"
                autoComplete="off"
                placeholder="Search transcript"
                className="pw-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <button
                type="button"
                className="pw-btn"
                data-testid="run-copy"
                disabled={noRows}
                onClick={() => void copyTranscript()}
              >
                {copied ? 'Copied' : 'Copy'}
              </button>
              <button
                type="button"
                className="pw-btn"
                data-testid="run-download-md"
                disabled={noRows}
                onClick={() =>
                  downloadTextFile(
                    `${base}-transcript.md`,
                    formatTranscriptMarkdown(rows, project.title, project.sourceUrl),
                    'text/markdown;charset=utf-8',
                  )
                }
              >
                .md
              </button>
              <button
                type="button"
                className="pw-btn"
                data-testid="run-download-srt"
                disabled={noRows}
                onClick={() => downloadTextFile(`${base}.srt`, formatSrt(exportSegments), 'application/x-subrip;charset=utf-8')}
              >
                .srt
              </button>
              <button
                type="button"
                className="pw-btn"
                data-testid="run-download-vtt"
                disabled={noRows}
                onClick={() => downloadTextFile(`${base}.vtt`, formatVtt(exportSegments), 'text/vtt;charset=utf-8')}
              >
                .vtt
              </button>
              <button
                type="button"
                className="pw-btn"
                data-testid="run-download-json"
                disabled={noRows}
                onClick={() =>
                  downloadTextFile(`${base}.json`, formatTranscriptJson(rows, base), 'application/json;charset=utf-8')
                }
              >
                .json
              </button>
            </div>
          ) : null}

          <div id="run-source-panel" role="tabpanel" aria-labelledby={`run-tab-${sourceTab}`}>
            {sourceTab === 'transcript' ? (
              noRows ? (
                <p className="pw-muted" data-testid="run-transcript-empty">
                  {allRows.length > 0
                    ? 'No transcript lines match this folder and search.'
                    : pack
                      ? 'This pack has no timed transcript, so there is nothing to show or export.'
                      : 'Extract the Video Pack to load the transcript.'}
                </p>
              ) : (
                <ol className="pw-rows" aria-label="Timestamped transcript" data-testid="run-transcript">
                  {rows.map((row) => (
                    <li key={`${row.idx}-${row.start}`} className="pw-row">
                      <button
                        type="button"
                        className="pw-row-btn"
                        data-testid={`run-seek-${row.idx}`}
                        aria-label={`Seek to ${formatSeconds(row.start)}`}
                        onClick={() => seek(row.start)}
                      >
                        <Play size={10} aria-hidden="true" /> {formatSeconds(row.start)}
                      </button>
                      <span className="pw-row-text">{row.text}</span>
                      <button
                        type="button"
                        className="pw-btn"
                        data-testid={`run-quote-${row.idx}`}
                        aria-label={`Quote transcript at ${formatSeconds(row.start)}`}
                        onClick={() => quoteLine(row.text, row.start)}
                      >
                        <Quote size={12} aria-hidden="true" /> Quote
                      </button>
                    </li>
                  ))}
                </ol>
              )
            ) : null}

            {sourceTab === 'subtitles' ? (
              <div className="pw-run-col">
                <div className="pw-tabs" role="group" aria-label="Subtitle format">
                  {(['srt', 'vtt'] as const).map((format) => (
                    <button
                      key={format}
                      type="button"
                      className="pw-btn"
                      aria-pressed={subtitleFormat === format}
                      onClick={() => setSubtitleFormat(format)}
                    >
                      {format.toUpperCase()}
                    </button>
                  ))}
                </div>
                {noRows ? (
                  <p className="pw-muted">No timed lines to preview.</p>
                ) : (
                  <pre className="pw-pre" data-testid="run-subtitles-preview">
                    {subtitleText}
                  </pre>
                )}
              </div>
            ) : null}

            {sourceTab === 'chapters' ? (
              chapters.length === 0 ? (
                <p className="pw-muted">No chapters were extracted.</p>
              ) : (
                <div className="pw-run-col" data-testid="run-chapters">
                  {chapters.map((chapter, index) => (
                    <article
                      key={`${chapter.start}-${index}`}
                      className="pw-chapter"
                      data-active={folder.id === `ch-${index + 1}` ? 'true' : 'false'}
                    >
                      <div className="pw-chapter-head">
                        <button type="button" className="pw-row-btn" onClick={() => seek(chapter.start)}>
                          <Play size={10} aria-hidden="true" /> {formatSeconds(chapter.start)}
                        </button>
                        <strong>
                          {index + 1}. {chapter.topic}
                        </strong>
                      </div>
                      {chapter.key_points?.length ? (
                        <ul>
                          {chapter.key_points.map((point) => (
                            <li key={point}>{point}</li>
                          ))}
                        </ul>
                      ) : null}
                      <div className="pw-toolbar">
                        <button type="button" className="pw-btn" onClick={() => onSelectFolder(`ch-${index + 1}`)}>
                          Filter to CH{index + 1}
                        </button>
                        <button
                          type="button"
                          className="pw-btn"
                          data-testid={`run-ask-chapter-${index + 1}`}
                          onClick={() =>
                            askChat(
                              `Summarize chapter ${index + 1}: "${chapter.topic}" (${formatSeconds(chapter.start)}–${formatSeconds(chapter.end)}).`,
                            )
                          }
                        >
                          Ask about chapter
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )
            ) : null}
          </div>
        </div>
      </div>

      <div className="pw-run-col">
        <div className="pw-tabs" role="tablist" aria-label="AI panel">
          <button
            type="button"
            role="tab"
            id="run-right-notes"
            aria-selected={rightTab === 'notes'}
            aria-controls="run-notes-panel"
            className="pw-tab"
            onClick={() => setRightTab('notes')}
          >
            AI Notes
          </button>
          <button
            type="button"
            role="tab"
            id="run-right-chat"
            aria-selected={rightTab === 'chat'}
            aria-controls="run-chat-panel"
            className="pw-tab"
            data-testid="run-tab-chat"
            onClick={() => setRightTab('chat')}
          >
            AI Chat
          </button>
        </div>

        <div
          id="run-notes-panel"
          role="tabpanel"
          aria-labelledby="run-right-notes"
          className="pw-notes pw-run-col"
          hidden={rightTab !== 'notes'}
        >
          <section className="pw-card">
            <h2>Get the point of this video</h2>
            <p>Ask for the main points and the moments that matter, with timestamps.</p>
            <div>
              <button
                type="button"
                className="pw-btn"
                data-primary="true"
                data-testid="run-summarize"
                disabled={!pack || extracting}
                onClick={() => askChat('Summarize key steps & decisions')}
              >
                Summarize this video
              </button>
            </div>
            {!pack ? (
              <div className="pw-banner">
                <span>Extract the Video Pack to enable notes and chat.</span>
                <button type="button" className="pw-btn" disabled={extracting} onClick={onExtractPack}>
                  Extract Video Pack
                </button>
              </div>
            ) : null}
          </section>

          <section className="pw-card" aria-labelledby="run-moments-heading">
            <h2 id="run-moments-heading">From this transcript</h2>
            {moments.length === 0 ? (
              <p className="pw-muted">No chapters or described keyframes were extracted.</p>
            ) : (
              <ul className="pw-list" data-testid="run-moments">
                {moments.map((moment, index) => (
                  <li key={`${moment.t}-${index}`}>
                    <button type="button" className="pw-row-btn" onClick={() => seek(moment.t)}>
                      {formatSeconds(moment.t)}
                    </button>{' '}
                    {moment.label}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="pw-card" aria-labelledby="run-more-heading">
            <h2 id="run-more-heading">More you can do</h2>
            <ul className="pw-list">
              {MORE_ACTIONS.map((action) => (
                <li key={action.id}>
                  <button
                    type="button"
                    className="pw-btn"
                    data-testid={`run-more-${action.id}`}
                    disabled={!pack || extracting}
                    onClick={() => askChat(action.prompt)}
                  >
                    {action.label}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div
          id="run-chat-panel"
          role="tabpanel"
          aria-labelledby="run-right-chat"
          className="pw-chat uvai-cards template-studio-shell"
          hidden={rightTab !== 'chat'}
        >
          <StudioIdeChat
            videoId={safeVideoId}
            packId={pack?.id ?? null}
            isWorking={packStatus === 'processing'}
            videoTitle={project.title}
            onSeek={seek}
            quoteSignal={quoteSignal}
            quickActionSignal={quickAction}
          />
        </div>
      </div>
    </div>
  );
}
