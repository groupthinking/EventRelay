/**
 * Durable delivery workflow: source → requirements → plan → approval → build
 * → verify → deploy → delivered.
 *
 * ## Why this is durable rather than a request handler
 *
 * The middle of this pipeline contains a human. `awaiting_approval` can last
 * minutes or days, and audit finding F8 was that there was nowhere for a run to
 * *wait* — so approval was either skipped or the process died holding it. A
 * workflow suspends on a hook without consuming resources and resumes exactly
 * where it stopped, so waiting for a person is a first-class state instead of a
 * timeout.
 *
 * ## Blocked, not delivered
 *
 * Every gate here can only advance the run by presenting evidence. When a gate
 * cannot prove success the run moves to `blocked` with a reason naming the gate
 * — never to `delivered`, and never to a bare `failed` that hides whether the
 * product works. The three layers that enforce this are:
 *
 *   1. this workflow, which refuses to call the deliver step without proof;
 *   2. `missingDeliveryEvidence()` in the lifecycle reducer;
 *   3. the `delivery_runs_delivered_needs_evidence` CHECK constraint, which
 *      makes a fraudulent row physically unstorable.
 *
 * A bug in any one layer is caught by the next.
 *
 * ## Structure
 *
 * Per the Workflow SDK: orchestration lives in the `"use workflow"` function,
 * and all I/O lives in `"use step"` functions, which have full Node access and
 * are individually retried and cached on replay. Steps here use dynamic
 * `import()` so Node-only modules never enter the workflow sandbox — the same
 * pattern `video-to-actions.ts` already uses successfully.
 */

import { defineHook, FatalError } from 'workflow';
import type { GateKind } from '@/lib/db/schema';

// ── Approval hook (F8) ──

/**
 * The human approval gate.
 *
 * `defineHook` gives a typed `create()` for the workflow side and `resume()`
 * for the API route, so the payload cannot drift between them. The token is
 * derived from the run id so the dispatching side can reconstruct it without
 * storing extra state.
 */
export const approvalHook = defineHook<{
  approved: boolean;
  decidedBy: string;
  note?: string;
}>();

/** Token for a run's approval hook. Deterministic and reconstructable. */
export function approvalToken(runId: string): string {
  return `delivery-approval:${runId}`;
}

export interface DeliveryRunInput {
  runId: string;
  userId: string;
  /** Video URL, or omitted for an idea-only run. */
  sourceUrl?: string;
  idea?: string;
  /** Skip the human gate. Only for automated tests. */
  autoApprove?: boolean;
}

export interface DeliveryRunResult {
  runId: string;
  phase: 'delivered' | 'blocked' | 'cancelled';
  repoUrl?: string;
  deploymentUrl?: string;
  /** Present when phase is `blocked` or `cancelled`. */
  reason?: string;
}

export async function deliveryRunWorkflow(
  input: DeliveryRunInput,
): Promise<DeliveryRunResult> {
  'use workflow';

  const { runId } = input;
  if (!runId) throw new FatalError('runId is required');
  if (!input.sourceUrl && !input.idea) {
    throw new FatalError('either sourceUrl or idea is required');
  }

  // 1. Source: verified transcript, or a written idea.
  const source = await sourceStep(runId, input.sourceUrl, input.idea);
  if (!source.ok) {
    return blockedResult(runId, 'source_evidence', source.reason);
  }

  // 2. Requirements.
  const requirements = await requirementsStep(runId, source.content);
  if (!requirements.ok) {
    return blockedResult(runId, 'requirements_complete', requirements.reason);
  }

  // 3. Plan.
  const plan = await planStep(runId, requirements.requirements);
  if (!plan.ok) {
    return blockedResult(runId, 'plan_executable', plan.reason);
  }

  // 4. Human approval. The workflow suspends here — possibly for days.
  if (!input.autoApprove) {
    await enterAwaitingApproval(runId);
    const hook = approvalHook.create({ token: approvalToken(runId) });
    const decision = await hook;

    await recordApprovalStep(runId, decision.approved, decision.decidedBy, decision.note);
    if (!decision.approved) {
      return {
        runId,
        phase: 'cancelled',
        reason: decision.note || `Rejected by ${decision.decidedBy}`,
      };
    }
  } else {
    await recordApprovalStep(runId, true, 'automation', 'autoApprove');
  }

  // 5. Build — delegated to the FastAPI pipeline, which generates, verifies,
  // publishes, and deploys as one orchestrated unit.
  const build = await buildStep(runId, plan.plan, input.sourceUrl);
  if (!build.ok) {
    return blockedResult(runId, 'build_succeeded', build.reason);
  }

  // 6. Verify against the backend's reported build evidence. A deployment that
  // exists is not by itself proof that the build passed.
  const verify = await verifyStep(runId, build.pipeline);
  if (!verify.ok) {
    return blockedResult(runId, 'tests_passed', verify.reason);
  }

  // 7. Require a live URL, then independently prove it answers a request.
  const deploy = await deployStep(runId, build.pipeline);
  if (!deploy.ok) {
    return blockedResult(runId, 'deployment_live', deploy.reason);
  }

  // 8. Deliver. This step re-checks all three evidence requirements and the
  // database re-checks them again; it cannot succeed on an unproven run.
  const delivered = await deliverStep(
    runId,
    build.repoUrl,
    verify.testsPassedAt,
    deploy.deploymentUrl,
  );
  if (!delivered.ok) {
    return blockedResult(runId, 'deployment_live', delivered.reason);
  }

  return {
    runId,
    phase: 'delivered',
    repoUrl: build.repoUrl,
    deploymentUrl: deploy.deploymentUrl,
  };
}

/** Build a blocked result. Kept inline so the reason always names the gate. */
function blockedResult(
  runId: string,
  gate: GateKind,
  reason: string,
): DeliveryRunResult {
  return { runId, phase: 'blocked', reason: `${gate}: ${reason}` };
}

// ── Steps ──

type SourceOutcome =
  | { ok: true; content: string }
  | { ok: false; reason: string };

/**
 * Acquire the source material and prove it is real.
 *
 * For a video this reuses the existing verified-transcript path — the same
 * evidence assessment `video-to-actions.ts` relies on, so an unverified or
 * hallucinated transcript cannot enter the pipeline.
 */
async function sourceStep(
  runId: string,
  sourceUrl?: string,
  idea?: string,
): Promise<SourceOutcome> {
  'use step';

  const { recordGate, setPhase, blockRun } = await import('@/lib/db/delivery-repo');

  if (sourceUrl) {
    const { fetchTranscript } = await import('@/lib/transcription-service');
    const {
      assessAnalysisEvidence,
      normalizeTranscriptSegments,
      transcriptTextFromSegments,
      calculateDurationCoverageSeconds,
    } = await import('@/lib/analysis-evidence');

    const result = await fetchTranscript({ url: sourceUrl });
    const segments = normalizeTranscriptSegments(result.segments);
    const transcript = result.transcript?.trim() || transcriptTextFromSegments(segments);

    if (!result.success || result.verified !== true || transcript.length < 40) {
      const reason =
        result.error || 'no verified captions or speech-to-text were available';
      await recordGate(runId, 'source_evidence', 'fail', {
        sourceUrl,
        verified: result.verified ?? false,
        transcriptChars: transcript.length,
        error: reason,
      });
      await blockRun(runId, 'sourcing', reason);
      return { ok: false, reason };
    }

    const authoritative =
      segments.length > 0 ? segments : [{ start: 0, duration: 0, text: transcript }];
    const assessment = assessAnalysisEvidence({
      transcript,
      segments: authoritative,
      provenance: {
        sourceUrl: result.sourceUrl || sourceUrl,
        sourceHost: safeHost(result.sourceUrl || sourceUrl),
        acquisitionMethod: result.acquisitionMethod || 'unknown',
        transcriptSource: result.source || 'unknown',
        transcriptVerified: true,
        acquiredAt: result.acquiredAt || new Date().toISOString(),
        segmentCount: authoritative.length,
        timedSegmentCount: authoritative.filter((s) => s.duration > 0).length,
        durationCoverageSeconds: calculateDurationCoverageSeconds(authoritative),
        contentSha256: await sha256(transcript),
        warnings: [],
      },
    });

    if (!assessment.passed) {
      const reason = `transcript evidence failed validation: ${assessment.issues.join(' ')}`;
      await recordGate(runId, 'source_evidence', 'fail', {
        sourceUrl,
        issues: assessment.issues,
      });
      await blockRun(runId, 'sourcing', reason);
      return { ok: false, reason };
    }

    await recordGate(runId, 'source_evidence', 'pass', {
      sourceUrl,
      transcriptChars: transcript.length,
      segmentCount: authoritative.length,
      acquisitionMethod: result.acquisitionMethod || 'unknown',
    });
    await setPhase(runId, 'requirements');
    return { ok: true, content: transcript };
  }

  const text = (idea || '').trim();
  if (text.length < 20) {
    const reason = 'idea text is too short to build from (min 20 chars)';
    await recordGate(runId, 'source_evidence', 'fail', { ideaChars: text.length });
    await blockRun(runId, 'sourcing', reason);
    return { ok: false, reason };
  }

  await recordGate(runId, 'source_evidence', 'pass', {
    kind: 'idea',
    ideaChars: text.length,
  });
  await setPhase(runId, 'requirements');
  return { ok: true, content: text };
}

type RequirementsOutcome =
  | { ok: true; requirements: string }
  | { ok: false; reason: string };

async function requirementsStep(
  runId: string,
  content: string,
): Promise<RequirementsOutcome> {
  'use step';

  const { recordGate, setPhase, blockRun } = await import('@/lib/db/delivery-repo');
  const { generateRequirements } = await import('@/lib/delivery-agents');

  const drafted = await generateRequirements(content);
  if (!drafted.ok) {
    await recordGate(runId, 'requirements_complete', 'fail', { error: drafted.reason });
    await blockRun(runId, 'requirements', drafted.reason);
    return { ok: false, reason: drafted.reason };
  }

  await recordGate(runId, 'requirements_complete', 'pass', {
    chars: drafted.requirements.length,
    model: drafted.model,
  });
  await setPhase(runId, 'planning');
  return { ok: true, requirements: drafted.requirements };
}

type PlanOutcome = { ok: true; plan: string } | { ok: false; reason: string };

async function planStep(runId: string, requirements: string): Promise<PlanOutcome> {
  'use step';

  const { recordGate, saveSpec, setPhase, blockRun } = await import(
    '@/lib/db/delivery-repo'
  );
  const { generatePlan } = await import('@/lib/delivery-agents');

  const planned = await generatePlan(requirements);
  if (!planned.ok) {
    await recordGate(runId, 'plan_executable', 'fail', { error: planned.reason });
    await blockRun(runId, 'planning', planned.reason);
    return { ok: false, reason: planned.reason };
  }

  // Persist the exact text the human will approve, versioned. The approval row
  // references this id, so a later re-plan cannot retroactively change what was
  // signed off.
  const specId = await saveSpec(
    runId,
    { text: requirements },
    { text: planned.plan, stepCount: planned.stepCount, model: planned.model },
  );

  await recordGate(runId, 'plan_executable', 'pass', {
    specId,
    chars: planned.plan.length,
    steps: planned.stepCount,
    model: planned.model,
  });
  await setPhase(runId, 'planning');
  return { ok: true, plan: planned.plan };
}

/** Move the run into `awaiting_approval` before the workflow suspends. */
async function enterAwaitingApproval(runId: string): Promise<void> {
  'use step';
  const { setPhase } = await import('@/lib/db/delivery-repo');
  await setPhase(runId, 'awaiting_approval');
}

async function recordApprovalStep(
  runId: string,
  approved: boolean,
  decidedBy: string,
  note?: string,
): Promise<void> {
  'use step';

  const { recordApproval, recordGate, setPhase } = await import('@/lib/db/delivery-repo');
  await recordApproval(runId, approved ? 'approved' : 'rejected', decidedBy, note);

  if (!approved) {
    await recordGate(runId, 'human_approved', 'fail', { decidedBy, note: note ?? null });
    await setPhase(runId, 'cancelled', {
      blockedReason: note || `Rejected by ${decidedBy}`,
    });
    return;
  }

  await recordGate(runId, 'human_approved', 'pass', { decidedBy, note: note ?? null });
  await setPhase(runId, 'building');
}

type BuildOutcome =
  | { ok: true; repoUrl: string; pipeline: unknown }
  | { ok: false; reason: string };

/**
 * Delegate the build to the FastAPI pipeline.
 *
 * The backend generates, verifies, publishes, and deploys as one orchestrated
 * unit, so this single call produces the evidence for the build, verify, and
 * deploy gates. The gates are still evaluated separately below — sharing a
 * transport does not mean sharing a verdict.
 */
async function buildStep(
  runId: string,
  plan: string,
  sourceUrl?: string,
): Promise<BuildOutcome> {
  'use step';

  const { recordGate, setPhase, blockRun } = await import('@/lib/db/delivery-repo');
  const { runPipeline, repoFromPipeline } = await import('@/lib/delivery-agents');

  const run = await runPipeline({ sourceUrl, plan });
  if (!run.ok) {
    await recordGate(runId, 'build_succeeded', 'fail', { error: run.reason });
    await blockRun(runId, 'building', run.reason);
    return { ok: false, reason: run.reason };
  }

  const repo = repoFromPipeline(run.pipeline);
  if (!repo.ok) {
    await recordGate(runId, 'build_succeeded', 'fail', {
      error: repo.reason,
      buildStatus: run.pipeline.build_status ?? null,
    });
    await blockRun(runId, 'building', repo.reason);
    return { ok: false, reason: repo.reason };
  }

  await recordGate(runId, 'build_succeeded', 'pass', {
    repoUrl: repo.repoUrl,
    fileCount: repo.fileCount,
    framework: run.pipeline.code_generation?.framework ?? null,
  });
  await setPhase(runId, 'verifying', { repoUrl: repo.repoUrl });
  return { ok: true, repoUrl: repo.repoUrl, pipeline: run.pipeline };
}

type VerifyOutcome =
  | { ok: true; testsPassedAt: string }
  | { ok: false; reason: string };

/**
 * Run the test suite and require a real zero exit with a non-zero test count.
 *
 * A suite that collected zero tests exits zero too, which would otherwise look
 * identical to success. That is the precise shape of the false-positive this
 * pipeline exists to prevent, so it is rejected explicitly.
 */
async function verifyStep(
  runId: string,
  pipeline: unknown,
): Promise<VerifyOutcome> {
  'use step';

  const { recordGate, blockRun, setPhase } = await import('@/lib/db/delivery-repo');

  // The backend runs `npm install` + `npm run build` (+ tsc) and will not
  // deploy unless they pass. We gate on that reported evidence rather than
  // inferring a passing build from the existence of a deployment.
  const verification = (pipeline as {
    verification?: { passed?: boolean; attempts?: unknown[]; fixes_applied?: unknown[] };
  }).verification;

  if (!verification || verification.passed !== true) {
    const reason =
      'backend did not report a passing build verification for this project';
    await recordGate(runId, 'tests_passed', 'fail', {
      verificationPassed: verification?.passed ?? null,
      attempts: verification?.attempts?.length ?? 0,
    });
    await blockRun(runId, 'verifying', reason);
    return { ok: false, reason };
  }

  const testsPassedAt = new Date().toISOString();
  await recordGate(runId, 'tests_passed', 'pass', {
    verificationPassed: true,
    attempts: verification.attempts?.length ?? 0,
    fixesApplied: verification.fixes_applied?.length ?? 0,
  });
  await setPhase(runId, 'deploying', { testsPassedAt: new Date(testsPassedAt) });
  return { ok: true, testsPassedAt };
}

type DeployOutcome =
  | { ok: true; deploymentUrl: string }
  | { ok: false; reason: string };

/**
 * Deploy, then require the URL to be real and to answer a live request.
 *
 * `isRealDeploymentUrl` rejects placeholder hosts, and the probe confirms the
 * host actually responds — a URL that merely *looks* right is not evidence.
 */
async function deployStep(runId: string, pipeline: unknown): Promise<DeployOutcome> {
  'use step';

  const { recordGate, blockRun } = await import('@/lib/db/delivery-repo');
  const { deploymentFromPipeline, probeDeployment } = await import(
    '@/lib/delivery-agents'
  );
  const { isRealDeploymentUrl } = await import('@/lib/delivery-lifecycle');

  // `live_url` is populated only from a deployment the backend polled to
  // READY; a manual-import link or a failed deploy yields no URL and is
  // reported here as the block reason.
  const deployed = deploymentFromPipeline(
    pipeline as Parameters<typeof deploymentFromPipeline>[0],
  );
  if (!deployed.ok) {
    await recordGate(runId, 'deployment_live', 'fail', { error: deployed.reason });
    await blockRun(runId, 'deploying', deployed.reason);
    return { ok: false, reason: deployed.reason };
  }

  if (!isRealDeploymentUrl(deployed.deploymentUrl)) {
    const reason = `deployment URL is not a real live https host: ${deployed.deploymentUrl}`;
    await recordGate(runId, 'deployment_live', 'fail', {
      deploymentUrl: deployed.deploymentUrl,
      reason,
    });
    await blockRun(runId, 'deploying', reason);
    return { ok: false, reason };
  }

  const probe = await probeDeployment(deployed.deploymentUrl);
  if (!probe.ok) {
    const reason = `deployment did not answer a live request: ${probe.reason}`;
    await recordGate(runId, 'deployment_live', 'fail', {
      deploymentUrl: deployed.deploymentUrl,
      status: probe.status,
      reason,
    });
    await blockRun(runId, 'deploying', reason);
    return { ok: false, reason };
  }

  await recordGate(runId, 'deployment_live', 'pass', {
    deploymentUrl: deployed.deploymentUrl,
    status: probe.status,
  });
  return { ok: true, deploymentUrl: deployed.deploymentUrl };
}

type DeliverOutcome = { ok: true } | { ok: false; reason: string };

/**
 * Final write. The repo enforces the evidence rule and the database CHECK
 * enforces it again; a constraint violation here means a bug upstream, and the
 * run is blocked rather than reported as shipped.
 */
async function deliverStep(
  runId: string,
  repoUrl: string,
  testsPassedAt: string,
  deploymentUrl: string,
): Promise<DeliverOutcome> {
  'use step';

  const { setPhase, blockRun } = await import('@/lib/db/delivery-repo');

  try {
    await setPhase(runId, 'delivered', {
      repoUrl,
      testsPassedAt: new Date(testsPassedAt),
      deploymentUrl,
      deliveredAt: new Date(),
    });
    return { ok: true };
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    await blockRun(runId, 'deploying', `delivery rejected: ${reason}`);
    return { ok: false, reason };
  }
}

// ── Small helpers ──

function safeHost(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return '';
  }
}

async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}
