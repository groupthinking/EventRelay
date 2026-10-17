'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { formatSeconds } from '@/lib/timestamp';
import {
  clampRunbookStep,
  parseRunbookStepHash,
  runbookAnchorLabel,
  runbookStepForTime,
  runbookStepHash,
  runbookStepKindLabel,
  type Runbook,
  type RunbookProgress,
  type RunbookStep,
} from '@/lib/runbook-steps';

/** Player slice the runner drives. `null` when the loaded player is not this pack's video. */
export interface StepRunnerPlayer {
  ready: boolean;
  currentTime: number;
  isPlaying: boolean;
  seekTo: (seconds: number, options?: { autoplay?: boolean }) => void;
  pause: () => void;
}

export interface StepRunnerProps {
  runbook: Runbook;
  player: StepRunnerPlayer | null;
  progress: RunbookProgress | null | undefined;
  onProgressChange: (progress: RunbookProgress) => void;
  /** Fires on mount and on every step change; `null` + index 0 is the prerequisites card. */
  onActiveStepChange?: (step: RunbookStep | null, index: number) => void;
  /** "Troubleshoot this step" — the parent re-grounds chat to this step and focuses the composer. */
  onTroubleshoot?: (step: RunbookStep) => void;
}

const AUTOPLAY_STORAGE_KEY = 'uvai:step-runner:autoplay:v1';
/** Grace after the clip end before the runner stops reacting (user scrubbed past on purpose). */
const CLIP_END_GRACE_SECONDS = 5;

function emptyProgress(): RunbookProgress {
  return { version: 1, checkedPrerequisites: [], completedSteps: [] };
}

function readAutoplayPreference(): boolean {
  try {
    const stored = window.localStorage.getItem(AUTOPLAY_STORAGE_KEY);
    return stored === null ? true : stored === '1';
  } catch {
    return true;
  }
}

function writeAutoplayPreference(value: boolean): void {
  try {
    window.localStorage.setItem(AUTOPLAY_STORAGE_KEY, value ? '1' : '0');
  } catch {
    // Private mode / quota: the toggle still works for this session.
  }
}

function toggleId(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((item) => item !== id) : [...list, id];
}

function rangeText(range: [number, number] | null): string {
  if (!range) return 'No verified timestamp';
  return range[0] === range[1]
    ? formatSeconds(range[0])
    : `${formatSeconds(range[0])}–${formatSeconds(range[1])}`;
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="uvai-btn !px-2 !py-1 !text-[11px]"
      onClick={() => {
        void navigator.clipboard?.writeText(text).then(
          () => {
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1500);
          },
          () => undefined,
        );
      }}
    >
      {copied ? 'Copied' : label}
    </button>
  );
}

export default function StepRunner({
  runbook,
  player,
  progress,
  onProgressChange,
  onActiveStepChange,
  onTroubleshoot,
}: StepRunnerProps) {
  const total = runbook.steps.length;
  const [active, setActive] = useState(0);
  const [autoplayClip, setAutoplayClip] = useState(true);
  const rootRef = useRef<HTMLElement | null>(null);
  const clipPausedForRef = useRef<string | null>(null);
  const hashAppliedRef = useRef(false);

  const current = progress ?? emptyProgress();
  const activeStep: RunbookStep | null = active >= 1 ? (runbook.steps[active - 1] ?? null) : null;
  const canSeek = Boolean(player?.ready);
  const stepsCompleted = useMemo(
    () => runbook.steps.filter((step) => current.completedSteps.includes(step.id)).length,
    [runbook.steps, current.completedSteps],
  );
  const prereqsChecked = useMemo(
    () => runbook.prerequisites.filter((row) => current.checkedPrerequisites.includes(row.id)).length,
    [runbook.prerequisites, current.checkedPrerequisites],
  );

  // Hash → initial step, applied after mount so SSR and the first client paint agree.
  useEffect(() => {
    if (hashAppliedRef.current) return;
    hashAppliedRef.current = true;
    setAutoplayClip(readAutoplayPreference());
    const fromHash = parseRunbookStepHash(window.location.hash);
    if (fromHash !== null) setActive(clampRunbookStep(fromHash, total));
  }, [total]);

  useEffect(() => {
    onActiveStepChange?.(activeStep, active);
    // Re-ground on step identity only; the callback itself may be re-created each parent render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeStep?.id, active]);

  const selectStep = useCallback(
    (next: number, options: { seek: boolean }) => {
      const clamped = clampRunbookStep(next, total);
      setActive(clamped);
      clipPausedForRef.current = null;
      try {
        window.history.replaceState(window.history.state, '', runbookStepHash(clamped));
      } catch {
        // Some embedded contexts block history writes; the step still changes.
      }
      const node = rootRef.current;
      if (node && typeof node.scrollIntoView === 'function') {
        node.scrollIntoView({ block: 'start', behavior: 'smooth' });
      }
      const step = clamped >= 1 ? runbook.steps[clamped - 1] : null;
      if (options.seek && step?.timestamp_range && player?.ready) {
        player.seekTo(step.timestamp_range[0], { autoplay: autoplayClip });
      }
    },
    [total, runbook.steps, player, autoplayClip],
  );

  // Clip mode: pause once when playback crosses the active step's end.
  const currentTime = player?.currentTime ?? 0;
  const isPlaying = player?.isPlaying ?? false;
  const pause = player?.pause;
  useEffect(() => {
    if (!autoplayClip || !isPlaying || !pause || !activeStep?.timestamp_range) return;
    const [start, end] = activeStep.timestamp_range;
    if (end <= start) return;
    if (
      currentTime >= end &&
      currentTime < end + CLIP_END_GRACE_SECONDS &&
      clipPausedForRef.current !== activeStep.id
    ) {
      clipPausedForRef.current = activeStep.id;
      pause();
    }
  }, [autoplayClip, isPlaying, pause, currentTime, activeStep]);

  const playingStep = useMemo(
    () => (player && isPlaying ? runbookStepForTime(runbook, currentTime) : null),
    [player, isPlaying, runbook, currentTime],
  );

  const updateProgress = (patch: Partial<Omit<RunbookProgress, 'version'>>) => {
    onProgressChange({ ...current, ...patch, version: 1, updatedAt: new Date().toISOString() });
  };

  return (
    <section
      ref={rootRef}
      data-testid="step-runner"
      aria-label="Step-by-step runner"
      className="flex flex-col gap-3"
    >
      <nav
        aria-label="Runbook steps"
        className="uvai-card flex flex-col gap-2 p-3"
        onKeyDown={(event) => {
          if (event.key === 'ArrowRight') {
            event.preventDefault();
            selectStep(active + 1, { seek: true });
          } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            selectStep(active - 1, { seek: true });
          }
        }}
      >
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            data-testid="step-runner-prev"
            className="uvai-btn !px-2.5 disabled:opacity-40"
            disabled={active <= 0}
            onClick={() => selectStep(active - 1, { seek: true })}
          >
            ‹ Previous
          </button>
          <p data-testid="step-runner-position" className="text-xs font-semibold text-slate-700">
            {active === 0 ? `Prerequisites · 0 of ${total}` : `Step ${active} of ${total}`}
          </p>
          <button
            type="button"
            data-testid="step-runner-next"
            className="uvai-btn uvai-btn-primary !px-2.5 disabled:opacity-40"
            disabled={active >= total}
            onClick={() => selectStep(active + 1, { seek: true })}
          >
            Next ›
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="step-runner-jump">
            Jump to step
          </label>
          <select
            id="step-runner-jump"
            data-testid="step-runner-jump"
            value={active}
            onChange={(event) => selectStep(Number(event.target.value), { seek: true })}
            className="uvai-input min-w-0 flex-1 truncate !py-1 !text-xs"
          >
            <option value={0}>0 · Prerequisites &amp; Environment</option>
            {runbook.steps.map((step) => (
              <option key={step.id} value={step.step_number}>
                {step.step_number} · {step.title}
                {current.completedSteps.includes(step.id) ? ' ✓' : ''}
              </option>
            ))}
          </select>
          <label className="inline-flex items-center gap-1.5 text-[11px] text-slate-600">
            <input
              type="checkbox"
              data-testid="step-runner-autoplay"
              checked={autoplayClip}
              onChange={(event) => {
                setAutoplayClip(event.target.checked);
                writeAutoplayPreference(event.target.checked);
              }}
            />
            Autoplay step clip
          </label>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
            <div
              className="h-full rounded-full bg-amber-500 transition-[width]"
              style={{ width: `${total > 0 ? Math.round((stepsCompleted / total) * 100) : 0}%` }}
            />
          </div>
          <p data-testid="step-runner-progress" className="font-mono text-[11px] text-slate-500">
            {stepsCompleted} / {total} steps · {prereqsChecked} / {runbook.prerequisites.length} prerequisites
          </p>
        </div>
        {playingStep && playingStep.step_number !== active ? (
          <div
            data-testid="step-runner-playing"
            className="flex items-center justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-800"
          >
            <span className="truncate">
              Playing: Step {playingStep.step_number} — {playingStep.title}
            </span>
            <button
              type="button"
              className="uvai-btn !px-2 !py-0.5 !text-[11px]"
              onClick={() => selectStep(playingStep.step_number, { seek: false })}
            >
              Jump
            </button>
          </div>
        ) : null}
      </nav>

      {active === 0 ? (
        <article data-testid="step-runner-prerequisites" className="uvai-card flex flex-col gap-3 p-4">
          <header>
            <p className="uvai-section-label">Step 0</p>
            <h3 className="mt-1 text-sm font-semibold text-slate-900">Prerequisites &amp; Environment</h3>
            <p className="mt-1 text-xs text-slate-500">
              Tools, stack checks, access and runtimes the pack names before Step 1. Checking a box is a
              local note, not evidence the environment is ready.
            </p>
          </header>
          {runbook.prerequisites.length === 0 ? (
            <p className="text-xs text-slate-400">No prerequisites named in this pack.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {runbook.prerequisites.map((row) => {
                const checked = current.checkedPrerequisites.includes(row.id);
                return (
                  <li key={row.id} className="uvai-doc-row">
                    <input
                      type="checkbox"
                      data-testid="step-runner-prereq-toggle"
                      aria-label={`Mark ready: ${row.title}`}
                      checked={checked}
                      onChange={() =>
                        updateProgress({ checkedPrerequisites: toggleId(current.checkedPrerequisites, row.id) })
                      }
                      className="mt-0.5 accent-amber-600"
                    />
                    <div className="min-w-0 flex-1">
                      <p className={`text-sm font-medium ${checked ? 'text-slate-400 line-through' : 'text-slate-800'}`}>
                        {row.title}
                      </p>
                      <p className="text-[11px] uppercase tracking-wide text-slate-400">{row.kind.replace('_', ' ')}</p>
                      {row.detail ? <p className="mt-0.5 text-xs text-slate-500">{row.detail}</p> : null}
                      {row.evidence ? (
                        <p className="mt-0.5 text-[11px] italic text-slate-400">{row.evidence}</p>
                      ) : null}
                      {row.href ? (
                        <a
                          href={row.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-0.5 inline-block text-[11px] text-blue-700 underline"
                        >
                          Official docs
                        </a>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
          {total > 0 ? (
            <button
              type="button"
              className="uvai-btn uvai-btn-primary self-start"
              onClick={() => selectStep(1, { seek: true })}
            >
              Start Step 1
            </button>
          ) : null}
        </article>
      ) : activeStep ? (
        <StepCard
          step={activeStep}
          completed={current.completedSteps.includes(activeStep.id)}
          canSeek={canSeek}
          onSeek={() => {
            if (activeStep.timestamp_range && player?.ready) {
              player.seekTo(activeStep.timestamp_range[0], { autoplay: autoplayClip });
            }
          }}
          onToggleComplete={() =>
            updateProgress({ completedSteps: toggleId(current.completedSteps, activeStep.id) })
          }
          onTroubleshoot={onTroubleshoot ? () => onTroubleshoot(activeStep) : undefined}
        />
      ) : null}
    </section>
  );
}

function StepCard({
  step,
  completed,
  canSeek,
  onSeek,
  onToggleComplete,
  onTroubleshoot,
}: {
  step: RunbookStep;
  completed: boolean;
  canSeek: boolean;
  onSeek: () => void;
  onToggleComplete: () => void;
  onTroubleshoot?: () => void;
}) {
  const range = step.timestamp_range;
  return (
    <article data-testid="step-runner-card" className="uvai-card flex flex-col gap-3 p-4">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            data-testid="step-runner-kind"
            className="inline-flex rounded-full bg-neutral-900 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white"
          >
            {runbookStepKindLabel(step.kind)}
          </span>
          <span
            data-testid="step-runner-range"
            title={runbookAnchorLabel(step.anchor)}
            className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[11px] ${
              range ? 'border-amber-300 bg-amber-50 text-amber-800' : 'border-slate-200 bg-slate-50 text-slate-500'
            }`}
          >
            {rangeText(range)}
            <span className="font-sans text-[10px] normal-case text-slate-400"> · {runbookAnchorLabel(step.anchor)}</span>
          </span>
          {step.priority ? <span className="uvai-chip !px-2 !py-0.5 !text-[11px]">Priority: {step.priority}</span> : null}
          {step.difficulty ? <span className="uvai-chip !px-2 !py-0.5 !text-[11px]">Difficulty: {step.difficulty}</span> : null}
        </div>
        <h3 data-testid="step-runner-title" className="text-base font-semibold text-slate-900">
          {step.title}
        </h3>
        {range ? (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="step-runner-seek"
              className="uvai-btn !px-2.5 !py-1 !text-xs disabled:opacity-40"
              disabled={!canSeek}
              onClick={onSeek}
              title={canSeek ? 'Seek the source video to this step' : 'Load this pack’s video in the player to seek'}
            >
              ▶ Seek to {formatSeconds(range[0])}
            </button>
            {!canSeek ? (
              <span className="text-[11px] text-slate-400">Player is not showing this pack’s video.</span>
            ) : null}
          </div>
        ) : (
          <p className="text-[11px] text-slate-500">
            Pack evidence does not anchor this step to the timeline, so seeking is disabled. Follow the
            source video manually.
          </p>
        )}
      </header>

      {step.evidence.keyframe?.image_path ? (
        <figure className="overflow-hidden rounded-lg border border-slate-200">
          {/* eslint-disable-next-line @next/next/no-img-element -- pack frame path, not an optimized asset */}
          <img
            data-testid="step-runner-keyframe"
            src={step.evidence.keyframe.image_path}
            alt={step.evidence.keyframe.desc ?? `Frame at ${formatSeconds(step.evidence.keyframe.t_s)}`}
            className="aspect-video w-full object-cover"
            loading="lazy"
          />
          <figcaption className="px-3 py-1.5 text-[11px] text-slate-500">
            Frame at {formatSeconds(step.evidence.keyframe.t_s)}
            {step.evidence.keyframe.desc ? ` — ${step.evidence.keyframe.desc}` : ''}
          </figcaption>
        </figure>
      ) : null}

      {step.detail ? <p className="text-sm leading-relaxed text-slate-700">{step.detail}</p> : null}

      {step.evidence.quote ? (
        <blockquote className="border-l-2 border-amber-300 pl-3 text-xs italic leading-relaxed text-slate-600">
          “{step.evidence.quote}”
          {range ? <span className="not-italic text-slate-400"> — {rangeText(range)}</span> : null}
        </blockquote>
      ) : null}

      {step.command ? (
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <p className="uvai-section-label">Terminal</p>
            <CopyButton text={step.command} label="Copy command" />
          </div>
          <pre
            data-testid="step-runner-command"
            className="overflow-auto rounded-lg bg-slate-900 p-3 font-mono text-[12px] leading-5 text-slate-100"
          >
            {step.command}
          </pre>
        </div>
      ) : null}

      {step.snippet ? (
        <div className="flex flex-col gap-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate font-mono text-[11px] text-blue-700">
              {step.snippet.path_hint ?? 'snippet'}
              {step.snippet.lang ? ` · ${step.snippet.lang}` : ''}
            </p>
            <CopyButton text={step.snippet.content} label="Copy snippet" />
          </div>
          <pre
            data-testid="step-runner-snippet"
            className="overflow-auto rounded-lg bg-slate-900 p-3 font-mono text-[11px] leading-5 text-slate-200"
          >
            {step.snippet.content}
          </pre>
        </div>
      ) : null}

      <dl className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
        <div>
          <dt className="uvai-section-label">Inputs</dt>
          <dd className="mt-1 text-slate-700">{step.inputs.length ? step.inputs.join(', ') : 'None named in pack'}</dd>
        </div>
        <div>
          <dt className="uvai-section-label">Outputs</dt>
          <dd className="mt-1 font-mono text-[11px] text-slate-700">
            {step.outputs.length ? step.outputs.join(', ') : 'None named in pack'}
          </dd>
        </div>
        {step.architecture_stage ? (
          <div>
            <dt className="uvai-section-label">Architecture stage</dt>
            <dd className="mt-1 text-slate-700">{step.architecture_stage}</dd>
          </div>
        ) : null}
        {step.tags.length ? (
          <div>
            <dt className="uvai-section-label">Tags</dt>
            <dd className="mt-1 flex flex-wrap gap-1">
              {step.tags.map((tag) => (
                <span key={tag} className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600">
                  {tag}
                </span>
              ))}
            </dd>
          </div>
        ) : null}
      </dl>

      <div
        data-testid="step-runner-verification"
        className={`rounded-lg border p-3 ${completed ? 'border-emerald-200 bg-emerald-50/60' : 'border-slate-200 bg-slate-50'}`}
      >
        <p className="uvai-section-label">
          Verification
          <span className="ml-1 font-normal normal-case tracking-normal text-slate-400">
            · {step.verification_source === 'grounded_spec'
              ? 'grounded-spec acceptance criteria'
              : step.verification_source === 'stack_check'
                ? 'stack.tools check'
                : 'no explicit check in pack'}
          </span>
        </p>
        <p className="mt-1 whitespace-pre-wrap text-xs leading-relaxed text-slate-700">{step.verification}</p>
        <label className="mt-2 inline-flex items-center gap-2 text-xs text-slate-700">
          <input
            type="checkbox"
            data-testid="step-runner-complete"
            checked={completed}
            onChange={onToggleComplete}
            className="accent-emerald-600"
          />
          Mark step complete
        </label>
        <p className="mt-1 text-[11px] text-slate-400">A local note, not evidence the step was performed.</p>
      </div>

      {onTroubleshoot ? (
        <button
          type="button"
          data-testid="step-runner-troubleshoot"
          className="uvai-btn self-start"
          onClick={onTroubleshoot}
        >
          Troubleshoot this step in chat
        </button>
      ) : null}
    </article>
  );
}
