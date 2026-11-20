'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { clsx } from 'clsx';
import { Pencil, Send } from 'lucide-react';
import {
  LIVE_TASK_OWNER_LABELS,
  LIVE_TASK_OWNERS,
  buildDispatchRequest,
  formatTimestamp,
  isLiveTaskOwner,
  normalizeTaskEdit,
  type LiveTask,
  type LiveTaskEdit,
  type LiveTaskEdits,
} from '@/lib/live-studio-tasks';
import {
  dispatchLiveTasks,
  executionLine,
  fetchAgentStatus,
  isTerminal,
  probeDispatchAvailability,
  type RunLine,
  type RunLineStatus,
} from '@/lib/live-studio-dispatch';
import { useProgressiveCount } from '@/lib/use-progressive-count';
import type { AgentExecution } from '@/lib/types';
import { LiveSection, SkeletonRows } from './LiveSourcePanels';

const STATUS_POLL_MS = 2_000;
const STATUS_POLL_ATTEMPTS = 90;

interface TaskEditorProps {
  task: LiveTask;
  baseTask: LiveTask;
  onSave: (edit: LiveTaskEdit | null) => void;
  onCancel: () => void;
}

function TaskEditor({ task, baseTask, onSave, onCancel }: TaskEditorProps) {
  const [title, setTitle] = useState(task.title);
  const [spec, setSpec] = useState(task.spec);
  const [check, setCheck] = useState(task.check);
  const [owner, setOwner] = useState(task.owner);
  const prefix = `live-task-${task.id}`;
  return (
    <form
      className="live-task-editor"
      data-testid={`${prefix}-editor`}
      onSubmit={(event) => {
        event.preventDefault();
        onSave(normalizeTaskEdit(baseTask, { title, spec, check, owner }));
      }}
    >
      <label htmlFor={`${prefix}-title`} className="live-field-label">Title</label>
      <input id={`${prefix}-title`} value={title} onChange={(event) => setTitle(event.target.value)} className="uvai-input w-full" />
      <label htmlFor={`${prefix}-spec`} className="live-field-label">Spec</label>
      <textarea id={`${prefix}-spec`} value={spec} rows={3} onChange={(event) => setSpec(event.target.value)} className="uvai-input w-full" />
      <label htmlFor={`${prefix}-check`} className="live-field-label">Check</label>
      <textarea
        id={`${prefix}-check`}
        value={check}
        rows={3}
        placeholder="Given…, when…, then…"
        onChange={(event) => setCheck(event.target.value)}
        className="uvai-input w-full font-mono text-[13px]"
      />
      <label htmlFor={`${prefix}-owner`} className="live-field-label">Owner agent</label>
      <select
        id={`${prefix}-owner`}
        value={owner}
        onChange={(event) => {
          if (isLiveTaskOwner(event.target.value)) setOwner(event.target.value);
        }}
        className="uvai-input w-full"
      >
        {LIVE_TASK_OWNERS.map((item) => (
          <option key={item} value={item}>{LIVE_TASK_OWNER_LABELS[item]}</option>
        ))}
      </select>
      <div className="live-task-editor__actions">
        <button type="submit" className="uvai-btn uvai-btn-primary" data-testid={`${prefix}-save`}>Save task</button>
        <button type="button" className="uvai-btn" onClick={onCancel}>Cancel</button>
        {task.edited ? (
          <button type="button" className="uvai-btn ml-auto" data-testid={`${prefix}-reset`} onClick={() => onSave(null)}>
            Reset to source
          </button>
        ) : null}
      </div>
    </form>
  );
}

const STATUS_LABEL: Record<RunLineStatus, string> = {
  queued: 'QUEUED',
  running: 'RUNNING',
  done: 'DONE',
  failed: 'FAILED',
};

function useWebMcpPresent(): boolean | null {
  const [present, setPresent] = useState<boolean | null>(null);
  useEffect(() => {
    setPresent(typeof navigator !== 'undefined' && 'modelContext' in navigator);
  }, []);
  return present;
}

export interface LiveTaskPanelProps {
  tasks: readonly LiveTask[];
  baseTasks: readonly LiveTask[];
  live: boolean;
  canSeek: boolean;
  videoId: string | null;
  jobId?: string;
  transcript?: string;
  onSeek: (seconds: number) => void;
  onSaveEdits: (edits: LiveTaskEdits) => void;
  edits: LiveTaskEdits | undefined;
}

export default function LiveTaskPanel({
  tasks,
  baseTasks,
  live,
  canSeek,
  videoId,
  jobId,
  transcript,
  onSeek,
  onSaveEdits,
  edits,
}: LiveTaskPanelProps) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [editing, setEditing] = useState<string | null>(null);
  const [lines, setLines] = useState<RunLine[]>([]);
  const [dispatching, setDispatching] = useState(false);
  const [upgradeRequired, setUpgradeRequired] = useState(false);
  const [backend, setBackend] = useState<boolean | null>(null);
  const seqRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const logRef = useRef<HTMLOListElement | null>(null);

  useEffect(() => {
    const log = logRef.current;
    if (log && lines.length) log.scrollTop = log.scrollHeight;
  }, [lines.length]);
  const webMcp = useWebMcpPresent();
  const visible = useProgressiveCount(tasks.length, { stepMs: 110 });
  const baseById = useMemo(() => new Map(baseTasks.map((task) => [task.id, task])), [baseTasks]);
  const taskIds = useMemo(() => new Set(tasks.map((task) => task.id)), [tasks]);
  const chosen = tasks.filter((task) => selected.has(task.id));

  useEffect(() => {
    const controller = new AbortController();
    void probeDispatchAvailability().then((available) => {
      if (!controller.signal.aborted) setBackend(available);
    });
    return () => controller.abort();
  }, []);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    setSelected((current) => {
      const next = new Set([...current].filter((id) => taskIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [taskIds]);

  const log = useCallback((status: RunLineStatus, subject: string, text: string) => {
    seqRef.current += 1;
    const line: RunLine = { seq: seqRef.current, status, subject, text };
    setLines((current) => [...current, line]);
  }, []);

  const pollExecutions = useCallback(
    async (executions: AgentExecution[], signal: AbortSignal) => {
      const last = new Map(executions.map((execution) => [execution.agent_id, `${execution.status}:${execution.progress}`]));
      let pending = executions.filter((execution) => !isTerminal(execution.status));
      for (let attempt = 0; attempt < STATUS_POLL_ATTEMPTS && pending.length > 0; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, STATUS_POLL_MS));
        if (signal.aborted) return;
        const next: AgentExecution[] = [];
        for (const execution of pending) {
          const outcome = await fetchAgentStatus(execution.agent_id, { signal });
          if (signal.aborted) return;
          if (outcome.kind !== 'status') {
            log('failed', execution.agent_type, `status unavailable: ${outcome.message}`);
            continue;
          }
          const merged = { ...outcome.execution, event_id: outcome.execution.event_id ?? execution.event_id };
          const key = `${merged.status}:${merged.progress}`;
          if (last.get(merged.agent_id) !== key) {
            last.set(merged.agent_id, key);
            seqRef.current += 1;
            const line = executionLine(merged, seqRef.current);
            setLines((current) => [...current, line]);
          }
          if (!isTerminal(merged.status)) next.push(merged);
        }
        pending = next;
      }
      if (pending.length > 0) log('failed', 'status', `stopped polling after ${STATUS_POLL_ATTEMPTS} checks; agents may still be running`);
    },
    [log],
  );

  const dispatch = async () => {
    if (chosen.length === 0 || dispatching) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setDispatching(true);
    setUpgradeRequired(false);
    for (const task of chosen) log('queued', `${LIVE_TASK_OWNER_LABELS[task.owner]} → ${task.id}`, task.title);
    const outcome = await dispatchLiveTasks(buildDispatchRequest({ tasks: chosen, videoId, jobId, transcript }), {
      signal: controller.signal,
    });
    if (controller.signal.aborted) return;
    switch (outcome.kind) {
      case 'dispatched': {
        log('running', `dispatch ${outcome.dispatchId}`, `accepted · ${outcome.executions.length} agent execution${outcome.executions.length === 1 ? '' : 's'}`);
        for (const execution of outcome.executions) {
          seqRef.current += 1;
          const line = executionLine(execution, seqRef.current);
          setLines((current) => [...current, line]);
        }
        await pollExecutions(outcome.executions, controller.signal);
        break;
      }
      case 'upgrade-required':
        setUpgradeRequired(true);
        log('failed', 'dispatch', `402 · ${outcome.message}`);
        break;
      case 'unavailable':
        log('failed', 'dispatch', `503 · ${outcome.message}`);
        break;
      case 'error':
        log('failed', 'dispatch', `${outcome.status ?? 'network'} · ${outcome.message}`);
        break;
      default: {
        const unreachable: never = outcome;
        void unreachable;
      }
    }
    if (abortRef.current === controller) setDispatching(false);
  };

  const saveEdit = (taskId: string, edit: LiveTaskEdit | null) => {
    const next: LiveTaskEdits = { ...(edits ?? {}) };
    if (edit) next[taskId] = edit;
    else delete next[taskId];
    onSaveEdits(next);
    setEditing(null);
  };

  const allSelected = tasks.length > 0 && chosen.length === tasks.length;

  return (
    <div className="live-task-column">
      <LiveSection
        id="live-tasks"
        title="Tasks"
        className="live-tasks"
        meta={
          tasks.length ? (
            <label className="live-select-all">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={() => setSelected(allSelected ? new Set() : new Set(tasks.map((task) => task.id)))}
                data-testid="live-tasks-select-all"
              />
              {chosen.length}/{tasks.length} selected
            </label>
          ) : undefined
        }
      >
        <ul className="live-task-list">
          {tasks.slice(0, visible).map((task) => {
            const base = baseById.get(task.id) ?? task;
            const isEditing = editing === task.id;
            return (
              <li
                key={task.id}
                data-testid={`live-task-${task.id}`}
                data-selected={selected.has(task.id) || undefined}
                className={clsx('live-task live-row-enter', selected.has(task.id) && 'live-task--selected')}
              >
                <div className="live-task__head">
                  <input
                    type="checkbox"
                    aria-label={`Select ${task.title}`}
                    checked={selected.has(task.id)}
                    onChange={() =>
                      setSelected((current) => {
                        const next = new Set(current);
                        if (next.has(task.id)) next.delete(task.id);
                        else next.add(task.id);
                        return next;
                      })
                    }
                    data-testid={`live-task-${task.id}-select`}
                  />
                  <button
                    type="button"
                    className="live-task__title"
                    aria-expanded={isEditing}
                    onClick={() => setEditing(isEditing ? null : task.id)}
                    data-testid={`live-task-${task.id}-open`}
                  >
                    <span className="live-task__id">{task.id}</span>
                    <span>{task.title}</span>
                    <Pencil className="live-task__edit-icon" aria-hidden />
                  </button>
                </div>
                <div className="live-task__meta">
                  <span className="uvai-chip live-owner-chip" data-testid={`live-task-${task.id}-owner`}>{LIVE_TASK_OWNER_LABELS[task.owner]}</span>
                  {task.edited ? <span className="uvai-chip live-chip-edited">Edited</span> : null}
                  {task.source ? (
                    <button
                      type="button"
                      disabled={!canSeek}
                      onClick={() => task.source && onSeek(task.source.startSeconds)}
                      className="live-timestamp"
                      data-testid={`live-task-${task.id}-timestamp`}
                      title={task.source.label}
                    >
                      ▶ {formatTimestamp(task.source.startSeconds)}
                      <span className="live-timestamp__basis">
                        {task.source.basis === 'cited' ? task.source.label : 'inferred · chapter match'}
                      </span>
                    </button>
                  ) : (
                    <span className="live-timestamp live-timestamp--none">No source timestamp</span>
                  )}
                </div>
                {task.keyframe ? (
                  <button
                    type="button"
                    disabled={!canSeek}
                    onClick={() => task.keyframe && onSeek(task.keyframe.t_s)}
                    className="live-task__frame"
                    data-testid={`live-task-${task.id}-keyframe`}
                  >
                    {task.keyframe.image_path ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={task.keyframe.image_path} alt="" width={96} height={54} loading="lazy" />
                    ) : null}
                    <span>Keyframe {formatTimestamp(task.keyframe.t_s)}{task.keyframe.desc ? ` · ${task.keyframe.desc}` : ''}</span>
                  </button>
                ) : null}
                {isEditing ? (
                  <TaskEditor
                    key={`${task.id}-${task.edited}`}
                    task={task}
                    baseTask={base}
                    onSave={(edit) => saveEdit(task.id, edit)}
                    onCancel={() => setEditing(null)}
                  />
                ) : (
                  <>
                    <p className="live-task__spec">{task.spec}</p>
                    {task.check ? (
                      <p className="live-task__check" data-testid={`live-task-${task.id}-check`}>
                        <span className="live-task__check-label">Check · not run</span>
                        {task.check}
                      </p>
                    ) : null}
                    {task.source?.quote ? <blockquote className="live-task__quote">“{task.source.quote}”</blockquote> : null}
                  </>
                )}
              </li>
            );
          })}
        </ul>
        <SkeletonRows
          count={tasks.length > visible ? Math.min(2, tasks.length - visible) : live && tasks.length === 0 ? 3 : 0}
          label="Tasks still arriving"
          testId="live-tasks-skeleton"
        />
        {!live && tasks.length === 0 ? <p className="live-empty">Tasks and proposed checks are bound to the video once a pack is extracted.</p> : null}
      </LiveSection>

      <LiveSection
        id="live-dispatch"
        title="Dispatch"
        className="live-dispatch"
        meta={
          <span className="live-dispatch__status" data-testid="live-dispatch-backend">
            Agent backend: {backend === null ? 'checking…' : backend ? 'connected' : 'not configured'}
            {' · '}WebMCP: {webMcp === null ? '…' : webMcp ? 'browser tools on' : 'not in this browser'}
          </span>
        }
      >
        <button
          type="button"
          className="uvai-btn uvai-btn-primary live-dispatch__button"
          disabled={chosen.length === 0 || dispatching}
          onClick={() => void dispatch()}
          data-testid="live-dispatch-button"
        >
          <Send className="h-4 w-4" aria-hidden />
          {dispatching
            ? 'Dispatching…'
            : chosen.length
              ? `Dispatch ${chosen.length} task${chosen.length === 1 ? '' : 's'}`
              : 'Dispatch tasks'}
        </button>
        <ol ref={logRef} className="live-run-log" role="log" aria-live="polite" aria-label="Agent run log" data-testid="live-run-log">
          {lines.length === 0 ? (
            <li className="live-run-log__idle">$ select tasks, then dispatch — status lines stream here</li>
          ) : (
            lines.map((line) => (
              <li key={line.seq} data-status={line.status}>
                <span className="live-run-log__status">{STATUS_LABEL[line.status]}</span>
                <span className="live-run-log__subject">{line.subject}</span>
                <span className="live-run-log__text">{line.text}</span>
              </li>
            ))
          )}
        </ol>
        {upgradeRequired ? (
          <p className="live-dispatch__note" data-testid="live-dispatch-upgrade">
            Agent dispatch is part of Workflow Pro. <Link href="/pricing">See plans</Link>
          </p>
        ) : null}
      </LiveSection>
    </div>
  );
}
