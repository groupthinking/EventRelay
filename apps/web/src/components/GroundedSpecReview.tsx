'use client';

import { useEffect, useId, useMemo, useState, type ReactNode } from 'react';
import { Button } from '@/components/ui/Button';
import { Alert, AlertTitle } from '@/components/ui/alert';
import type { VideoPackCitation } from '@/lib/emit-video-pack';
import { formatSeconds } from '@/lib/timestamp';
import {
  hashReviewContent, inspectGroundedSpec, reviewAcknowledgmentMatches,
  type GroundedBuildSpec, type ReviewInspection, type SpecIssue, type SpecReviewAcknowledgment,
} from '@/lib/grounded-build-spec';

export interface GroundedSpecReviewProps {
  videoId: string;
  pack: VideoPackCitation['pack'];
  acknowledgment?: unknown;
  persistenceAvailable?: boolean;
  onAcknowledge: (value: SpecReviewAcknowledgment | undefined) => boolean;
  onSeek?: (seconds: number) => void;
}

function ReviewGroup({ title, children }: { title: string; children: ReactNode }) {
  return <div className="flex flex-col gap-3"><h3 className="text-base font-semibold text-balance">{title}</h3>{children}</div>;
}

function Issues({ issues }: { issues: SpecIssue[] }) {
  return <ul className="flex flex-col gap-2">{issues.map((item, index) => (
    <li key={`${item.code}-${item.path}-${index}`} className="text-sm leading-relaxed">
      <strong>{item.severity === 'blocking' ? 'Blocker' : 'Note'}{item.path ? ` · ${item.path}` : ''}:</strong> {item.message}
    </li>
  ))}</ul>;
}

function Requirement({ requirement, onSeek }: { requirement: GroundedBuildSpec['requirements'][number]; onSeek?: (seconds: number) => void }) {
  return (
    <li className="flex flex-col gap-2 rounded-lg border border-ink/10 p-4">
      <p className="font-medium">{requirement.title}</p>
      <p className="text-ink/65">{requirement.id} · {requirement.classification} · {requirement.required ? 'Required' : 'Optional'} · {requirement.capabilities.join(', ')}</p>
      <p>{requirement.detail}</p>
      {requirement.rationale ? <p>Rationale: {requirement.rationale}</p> : null}
      {requirement.citations.length ? (
        <details>
          <summary className="cursor-pointer rounded-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-4">Supporting source</summary>
          <ul className="flex flex-col gap-3 py-3">
            {requirement.citations.map((ref, index) => (
              <li key={index} className="flex flex-col gap-2">
                <p className="text-ink/65">{ref.kind === 'visual' ? 'Model-described visual observation — not a verified frame' : 'Source-linked transcript quotation'}</p>
                <blockquote className="text-pretty">{ref.quote}</blockquote>
                <div className="flex flex-wrap items-center gap-3">
                  {onSeek ? <Button type="button" variant="secondary" onClick={() => onSeek(ref.startSeconds)}>Seek to {formatSeconds(ref.startSeconds)}</Button> : null}
                  <a className="rounded-sm underline underline-offset-4 focus-visible:outline-2" href={`https://www.youtube.com/watch?v=${ref.videoId}&t=${Math.floor(ref.startSeconds)}s`} target="_blank" rel="noopener noreferrer">Open source at {formatSeconds(ref.startSeconds)}</a>
                </div>
              </li>
            ))}
          </ul>
        </details>
      ) : <p className="text-ink/65">No observed source citation for this choice.</p>}
    </li>
  );
}

export default function GroundedSpecReview({ videoId, pack, acknowledgment, persistenceAvailable = true, onAcknowledge, onSeek }: GroundedSpecReviewProps) {
  const titleId = useId();
  const scopeId = useId();
  const inspection = useMemo(() => inspectGroundedSpec(pack), [pack]);
  const [digest, setDigest] = useState<{ inspection: ReviewInspection; videoId: string; status: 'valid' | 'mismatch' | 'unavailable' } | null>(null);
  const [saveResult, setSaveResult] = useState<{ inspection: ReviewInspection; videoId: string; saved: boolean; clearing: boolean } | null>(null);
  useEffect(() => {
    if (inspection.status !== 'available') return;
    let active = true;
    void hashReviewContent(inspection.canonical).then((hash) => {
      if (active) setDigest({ inspection, videoId, status: hash === inspection.contentHash ? 'valid' : 'mismatch' });
    }).catch(() => {
      if (active) setDigest({ inspection, videoId, status: 'unavailable' });
    });
    return () => { active = false; };
  }, [inspection, videoId]);

  const digestStatus = digest?.inspection === inspection && digest.videoId === videoId ? digest.status : 'checking';
  const currentSave = saveResult?.inspection === inspection && saveResult.videoId === videoId ? saveResult : null;
  const available = inspection.status === 'available' ? inspection : null;
  const reviewed = available && digestStatus === 'valid' && reviewAcknowledgmentMatches(acknowledgment, available.spec.source.sourceHash, available.contentHash);
  const save = (clearing: boolean) => {
    if (!available || digestStatus !== 'valid') return;
    const value: SpecReviewAcknowledgment | undefined = clearing ? undefined : {
      version: '1', sourceHash: available.spec.source.sourceHash, specHash: available.contentHash, acknowledgedAt: new Date().toISOString(),
    };
    let saved = false;
    try { saved = onAcknowledge(value); } catch { /* A persistence error must never imply that the review was saved. */ }
    setSaveResult({ inspection, videoId, saved, clearing });
  };

  return (
    <section data-testid="grounded-spec-review" aria-labelledby={titleId} className="min-w-0 rounded-xl border border-ink/15 bg-void p-4 font-sans text-sm leading-relaxed text-ink lg:col-span-2 sm:p-6">
      <div className="flex flex-col gap-6 break-words">
        <header className="flex flex-col gap-2">
          <h2 id={titleId} className="text-xl font-semibold text-balance">Grounded specification</h2>
          <p className="text-ink/65">Browser-only interactive apps · Specification review only</p>
          <p id={scopeId}>Acknowledgment records inspection, not acceptance of proposals or authorization. It does not verify evidence, lock builder inputs, run tests, or produce a G.A.T.E. receipt.</p>
        </header>
        {!available ? (
          <div className="flex flex-col gap-3">
            <p>{inspection.status === 'unavailable' ? 'Grounded specification unavailable for this pack. Older cached packs remain readable; cache upgrades and re-extraction are outside this phase.' : inspection.status === 'source-unavailable' ? 'No usable source. Provide a usable source video; no application blueprint was produced.' : 'Invalid grounded specification. It cannot be acknowledged.'}</p>
            <Issues issues={inspection.issues} />
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-2">
              <h3 className="text-lg font-medium text-balance">{available.spec.app.name || 'Application purpose unresolved'}</h3>
              <p>{available.spec.app.purpose || 'No purpose supplied.'}</p>
              <p className="text-ink/65">Model-reported source coverage: {available.spec.sourceStatus} · confidence: {Math.round(available.spec.confidence * 100)}%</p>
              <ul className="flex flex-col gap-1">{available.spec.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul>
            </div>
            <ReviewGroup title="Blockers and source limitations"><Issues issues={available.issues} /></ReviewGroup>
            <details>
              <summary className="cursor-pointer rounded-sm font-medium focus-visible:outline-2">Screens and browser state</summary>
              <div className="flex flex-col gap-3 py-3">
                {available.spec.screens.map((row) => <p key={row.id}><strong>{row.name}</strong> · {row.id}: {row.purpose}</p>)}
                {available.spec.state.map((row) => <p key={row.id}><strong>{row.name}</strong> · {row.persistence}: {row.description}</p>)}
              </div>
            </details>
            {([
              ['Observed requirements', ['observed']],
              ['Inferred and proposed choices', ['inferred', 'proposed']],
              ['Unknown requirements', ['unknown']],
            ] as const).map(([title, classifications]) => {
              const rows = available.spec.requirements.filter((row) => (classifications as readonly string[]).includes(row.classification));
              return <ReviewGroup key={title} title={title}>{rows.length ? <ul className="flex flex-col gap-3">{rows.map((row) => <Requirement key={row.id} requirement={row} onSeek={onSeek} />)}</ul> : <p className="text-ink/65">None reported.</p>}</ReviewGroup>;
            })}
            <ReviewGroup title="Unresolved questions">
              {available.spec.unresolved.length ? <ul className="flex flex-col gap-2">{available.spec.unresolved.map((row) => <li key={row.id}>{row.question} · Affects: {row.requirementIds.join(', ') || 'Application scope'}</li>)}</ul> : <p className="text-ink/65">None reported.</p>}
            </ReviewGroup>
            <ReviewGroup title="Unsupported capabilities">
              <p className="text-ink/65">Servers, accounts, shared databases, payments, secrets, native devices, and privileged/background execution are outside this scope. No local fake is substituted.</p>
              <ul className="flex flex-col gap-2">{available.spec.unsupported.map((row) => <li key={row.id}><strong>{row.capability}</strong>: {row.reason} · Affects: {row.requirementIds.join(', ') || 'Application scope'}</li>)}</ul>
            </ReviewGroup>
            <ReviewGroup title="Proposed acceptance criteria">
              <p className="text-ink/65">Proposed checks only. These tests have not been executed.</p>
              <ul className="flex flex-col gap-3">{available.spec.acceptanceCriteria.map((row) => <li key={row.id}><strong>{row.id} · {row.requirementId}</strong><p>Given: {row.given}</p><p>When: {row.when}</p><p>Expected: {row.then}</p></li>)}</ul>
            </ReviewGroup>
            <footer className="flex flex-col gap-3">
              <p role="status">{digestStatus === 'checking' ? 'Checking exact review content…' : digestStatus === 'mismatch' ? 'Content digest does not match. Acknowledgment is disabled.' : digestStatus === 'unavailable' ? 'Content verification unavailable. Acknowledgment is disabled.' : reviewed ? 'Review acknowledged locally. Blockers remain unresolved.' : 'Exact-content digest checked. This is not independent source verification.'}</p>
              {(!persistenceAvailable || currentSave?.saved === false) ? <Alert><AlertTitle>Browser storage unavailable</AlertTitle><p className="col-start-2">{currentSave?.clearing ? 'Cleared in this session only. The stored acknowledgment may return after reload.' : 'Session-only review state — not saved for reload.'}</p></Alert> : null}
              {acknowledgment && !reviewed && digestStatus === 'valid' ? <p>Previous review metadata is stale or invalid. Review this content again.</p> : null}
              <div className="flex flex-wrap gap-3">
                <Button type="button" variant="secondary" disabled={digestStatus !== 'valid' || Boolean(reviewed)} aria-describedby={scopeId} onClick={() => save(false)}>Acknowledge review</Button>
                {reviewed ? <Button type="button" variant="ghost" onClick={() => save(true)}>Clear local acknowledgment</Button> : null}
              </div>
              <details><summary className="cursor-pointer rounded-sm focus-visible:outline-2">Review identity</summary><p className="break-all font-mono">Schema {available.spec.version} · {available.spec.source.packId}<br />SHA-256 {available.contentHash}</p></details>
            </footer>
          </>
        )}
      </div>
    </section>
  );
}
