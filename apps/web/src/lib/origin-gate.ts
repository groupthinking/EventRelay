import 'server-only';

import { createHmac, createPublicKey, timingSafeEqual, verify } from 'node:crypto';
import { z } from 'zod';
import { canonicalGateJson, hashCanonical, type GateDecision, type GateEvaluation, type GateReceipt, type ZeroSimVerdict } from '@/lib/gate-transition';
import { probeLiveDeploymentUrl } from '@/lib/live-deployment-probe';
import { studioVerifiedLiveUrl } from '@/lib/studio-pipeline-status';

const identifier = z.string().min(1).max(200).regex(/^[a-zA-Z0-9_.:-]+$/);
const digest = z.string().regex(/^[a-f0-9]{64}$/);
const targetSchema = z.object({
  provider: z.literal('vercel'),
  projectId: identifier,
  environment: z.enum(['preview', 'production']),
  liveUrl: z.string().max(2048).refine((value) => studioVerifiedLiveUrl(value) === value),
}).strict();
const bindingSchema = z.object({
  transitionId: identifier,
  kind: z.literal('studio.deploy'),
  fromState: z.literal('proposed'),
  toState: z.literal('live'),
  subject: z.string().min(1).max(512),
  runId: identifier,
  artifactHash: digest,
  target: targetSchema,
}).strict();
const attestationSchema = z.object({
  payload: z.object({
    version: z.literal('origin.attestation.v1'),
    type: z.enum(['approval', 'deployment']),
    issuer: identifier,
    nonce: identifier,
    issuedAt: z.string().datetime(),
    expiresAt: z.string().datetime(),
    binding: bindingSchema,
    verdict: z.string().min(1).max(32),
    providerReceiptId: identifier.optional(),
    providerReceiptHash: digest.optional(),
  }).strict(),
  signature: z.string().regex(/^[A-Za-z0-9_-]{86}$/),
}).strict();
const requestSchema = bindingSchema.omit({ subject: true }).extend({
  runId: identifier.optional(),
  artifactHash: digest.optional(),
  target: targetSchema.optional(),
  approval: attestationSchema.optional(),
  evidence: attestationSchema.optional(),
}).strict();
const policySchema = z.object({
  version: z.literal(1),
  issuers: z.array(z.object({
    id: identifier,
    role: z.enum(['loop', 'deployment-verifier']),
    publicKey: z.string().min(1).max(4096),
    projectIds: z.array(identifier).min(1).max(100),
    revoked: z.boolean(),
  }).strict()).max(100),
}).strict().refine((policy) => new Set(policy.issuers.map((issuer) => issuer.id)).size === policy.issuers.length);

type Proposal = z.infer<typeof requestSchema>;
type Attestation = z.infer<typeof attestationSchema>;
type Policy = z.infer<typeof policySchema>;
type Finding = { decision: GateDecision; code: string; reason: string; verdict?: ZeroSimVerdict };

export interface OriginGateReceipt extends GateReceipt {
  version: 'eventrelay.gate-receipt.v2';
  request_hash: string;
  artifact_hash: string | null;
  run_id: string | null;
  target: z.infer<typeof targetSchema> | null;
  policy_hash: string | null;
  retained: boolean;
  signature: string | null;
}
export interface OriginGateEvaluation extends GateEvaluation { receipt: OriginGateReceipt }
export interface OriginGateStore {
  readPolicy(): Promise<unknown>;
  commit(input: {
    requestHash: string;
    transitionKey: string;
    nonceKeys: string[];
    evaluation: OriginGateEvaluation;
  }): Promise<{ status: 'stored' | 'conflict' | 'quota' } | { status: 'existing'; evaluation: unknown }>;
}
export interface OriginGateContext {
  subject: string | null;
  signingSecret: string;
  store: OriginGateStore;
  now?: number;
}

const missing: Finding = { decision: 'HOLD', code: 'GATE_HOLD_MISSING_EVIDENCE', reason: 'A run, artifact hash, permitted target, signed Loop approval, and independent verification receipt are required. An evidence workspace is not a verified deployment.' };
const unavailable: Finding = { decision: 'HOLD', code: 'GATE_HOLD_RUNTIME_UNAVAILABLE', reason: 'The trusted signing or receipt-retention runtime is unavailable. No transition is permitted.' };
const replay: Finding = { decision: 'REJECT', code: 'GATE_REJECT_REPLAY', reason: 'This transition or attestation nonce was already accepted for a different request.' };

function verifyAttestation(envelope: Attestation, type: 'approval' | 'deployment', binding: z.infer<typeof bindingSchema>, policy: Policy, now: number): Finding | null {
  const payload = envelope.payload;
  const issuer = policy.issuers.find((candidate) => candidate.id === payload.issuer);
  if (!issuer) return { decision: 'ESCALATE', code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN', reason: 'The attestation issuer is not registered by the trusted runtime.' };
  const expectedRole = type === 'approval' ? 'loop' : 'deployment-verifier';
  if (issuer.revoked || issuer.role !== expectedRole || !issuer.projectIds.includes(binding.target.projectId)) {
    return { decision: 'REJECT', code: 'GATE_REJECT_AUTHORITY_SCOPE', reason: 'The signer is revoked or lacks the required role and project scope.' };
  }
  let valid = false;
  try {
    const key = createPublicKey(issuer.publicKey);
    valid = key.asymmetricKeyType === 'ed25519' && verify(null, Buffer.from(`origin.attestation.v1\n${canonicalGateJson(payload)}`), key, Buffer.from(envelope.signature, 'base64url'));
  } catch {
    return { decision: 'ESCALATE', code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN', reason: 'The registered verification key is invalid.' };
  }
  if (!valid || payload.type !== type || canonicalGateJson(payload.binding) !== canonicalGateJson(binding)) {
    return { decision: 'REJECT', code: 'GATE_REJECT_ATTESTATION_MISMATCH', reason: 'Signature or user/run/artifact/target/transition binding does not match.', verdict: 'unreal' };
  }
  const issued = Date.parse(payload.issuedAt);
  const expires = Date.parse(payload.expiresAt);
  if (issued > now + 30_000 || expires <= now || expires <= issued || expires - issued > 900_000) {
    return { decision: 'HOLD', code: 'GATE_HOLD_STALE_EVIDENCE', reason: 'The attestation is expired, future-dated, or exceeds the 15-minute validity window.' };
  }
  if (type === 'approval') {
    if (payload.verdict === 'deny') return { decision: 'REJECT', code: 'GATE_REJECT_AUTHORITY_DENIED', reason: 'Loop denied this exact transition.' };
    if (payload.verdict !== 'allow') return { decision: 'ESCALATE', code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN', reason: 'The signed approval decision is unknown.' };
    return null;
  }
  if (!['real', 'unverified', 'unreal'].includes(payload.verdict)) return { decision: 'ESCALATE', code: 'GATE_ESCALATE_ZERO_SIM_UNKNOWN', reason: 'The signed Zero-Sim verdict is unknown.' };
  if (payload.verdict === 'unreal') return { decision: 'REJECT', code: 'GATE_REJECT_UNREAL_EVIDENCE', reason: 'The trusted verifier marked this evidence unreal.', verdict: 'unreal' };
  if (payload.verdict === 'unverified') return { decision: 'HOLD', code: 'GATE_HOLD_WEAK_EVIDENCE', reason: 'The trusted verifier has not verified this deployment.', verdict: 'unverified' };
  if (!payload.providerReceiptId || !payload.providerReceiptHash) return missing;
  return null;
}

function validStoredReceipt(value: unknown, expected: OriginGateEvaluation, secret: string): value is OriginGateEvaluation {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as OriginGateEvaluation;
  if (!candidate.receipt || candidate.decision !== expected.decision || candidate.receipt.request_hash !== expected.receipt.request_hash || candidate.receipt.retained !== true) return false;
  const { signature, receipt_hash, ...body } = candidate.receipt;
  if (typeof signature !== 'string' || !/^[a-f0-9]{64}$/.test(signature)) return false;
  if (receipt_hash !== hashCanonical(canonicalGateJson(body))) return false;
  if (candidate.decision !== body.decision || candidate.reason !== body.reason || candidate.reason_code !== body.reason_code) return false;
  const expectedSignature = createHmac('sha256', secret).update(`origin.gate-receipt.v2\n${receipt_hash}`).digest();
  return timingSafeEqual(Buffer.from(signature, 'hex'), expectedSignature);
}

export async function evaluateOriginGate(input: unknown, context: OriginGateContext): Promise<OriginGateEvaluation> {
  const now = context.now ?? Date.now();
  const parsed = requestSchema.safeParse(input);
  const proposal: Partial<Proposal> = parsed.success ? parsed.data : {};
  let policyHash: string | null = null;
  let requestHash = hashCanonical(canonicalGateJson({ input: parsed.success ? parsed.data : null, subject: context.subject }));
  const canSign = context.signingSecret.length >= 32;
  const issue = (finding: Finding, retained: boolean): OriginGateEvaluation => {
    const body = {
      version: 'eventrelay.gate-receipt.v2' as const,
      id: `er:gate:v2:${requestHash}`,
      kind: proposal.kind ?? 'studio.deploy',
      transition_id: proposal.transitionId ?? 'invalid',
      from_state: proposal.fromState ?? 'proposed',
      to_state: proposal.toState ?? 'live',
      decision: finding.decision,
      reason_code: finding.code,
      reason: finding.reason,
      evidence_refs: [proposal.approval, proposal.evidence].flatMap((envelope) => envelope ? [{ kind: envelope.payload.type, id: `${envelope.payload.issuer}:${envelope.payload.nonce}`, hash: hashCanonical(canonicalGateJson(envelope)) }] : []),
      authority: { actor: context.subject ? 'signed-in' : 'anonymous', claim: context.subject ?? '' },
      zero_sim: { verdict: finding.verdict ?? 'unverified' as ZeroSimVerdict, reason_code: finding.verdict === 'real' ? 'ZERO_SIM_REAL' : finding.verdict === 'unreal' ? 'ZERO_SIM_UNREAL' : 'ZERO_SIM_UNVERIFIED' },
      issued_at: new Date(now).toISOString(),
      request_hash: requestHash,
      artifact_hash: proposal.artifactHash ?? null,
      run_id: proposal.runId ?? null,
      target: proposal.target ?? null,
      policy_hash: policyHash,
      retained,
    };
    const receipt_hash = hashCanonical(canonicalGateJson(body));
    const signature = canSign ? createHmac('sha256', context.signingSecret).update(`origin.gate-receipt.v2\n${receipt_hash}`).digest('hex') : null;
    return { decision: finding.decision, reason: finding.reason, reason_code: finding.code, receipt: { ...body, receipt_hash, signature } };
  };
  const retain = async (finding: Finding): Promise<OriginGateEvaluation> => {
    const evaluation = issue(finding, true);
    try {
      const result = await context.store.commit({
        requestHash,
        transitionKey: hashCanonical(canonicalGateJson({ subject: context.subject, transitionId: proposal.transitionId })),
        nonceKeys: finding.decision === 'PASS' ? [proposal.approval!, proposal.evidence!].map(({ payload }) => hashCanonical(`${payload.issuer}:${payload.nonce}`)) : [],
        evaluation,
      });
      if (result.status === 'conflict') return issue(replay, false);
      if (result.status === 'quota') return issue({ decision: 'HOLD', code: 'GATE_HOLD_RETENTION_LIMIT', reason: 'Temporary receipt storage limit reached. No transition is permitted; retry after retained non-PASS receipts expire.' }, false);
      if (result.status === 'existing') return validStoredReceipt(result.evaluation, evaluation, context.signingSecret) ? result.evaluation : issue(unavailable, false);
      return evaluation;
    } catch {
      return issue(unavailable, false);
    }
  };

  if (!context.subject) return issue({ decision: 'ESCALATE', code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN', reason: 'A verified server session is required; browser actor labels do not authorize transitions.' }, false);
  if (!parsed.success) return issue({ decision: 'REJECT', code: 'GATE_REJECT_INVALID_TRANSITION', reason: 'Only the strict studio.deploy proposed-to-live contract is accepted.' }, false);
  if (!canSign) return issue(unavailable, false);
  if (proposal.target?.liveUrl && !proposal.evidence) return retain({ decision: 'REJECT', code: 'GATE_REJECT_CLAIM_MISMATCH', reason: 'A live URL without a signed, artifact-bound verification receipt is not accepted.' });
  if (!proposal.runId || !proposal.artifactHash || !proposal.target || !proposal.approval || !proposal.evidence) return retain(missing);
  let policy: Policy;
  try {
    const trusted = policySchema.safeParse(await context.store.readPolicy());
    if (!trusted.success || !trusted.data.issuers.length) return retain({ decision: 'ESCALATE', code: 'GATE_ESCALATE_AUTHORITY_UNKNOWN', reason: 'Loop and verifier public keys have not been registered in the trusted runtime.' });
    policy = trusted.data;
  } catch {
    return issue(unavailable, false);
  }
  policyHash = hashCanonical(canonicalGateJson(policy));
  requestHash = hashCanonical(canonicalGateJson({ input: parsed.data, subject: context.subject, policyHash }));
  const binding = bindingSchema.parse({ transitionId: proposal.transitionId, kind: proposal.kind, fromState: proposal.fromState, toState: proposal.toState, subject: context.subject, runId: proposal.runId, artifactHash: proposal.artifactHash, target: proposal.target });
  const approvalFinding = verifyAttestation(proposal.approval, 'approval', binding, policy, now);
  if (approvalFinding) return retain(approvalFinding);
  const evidenceFinding = verifyAttestation(proposal.evidence, 'deployment', binding, policy, now);
  if (evidenceFinding) return retain(evidenceFinding);
  const approvalKey = createPublicKey(policy.issuers.find((issuer) => issuer.id === proposal.approval!.payload.issuer)!.publicKey).export({ type: 'spki', format: 'der' });
  const evidenceKey = createPublicKey(policy.issuers.find((issuer) => issuer.id === proposal.evidence!.payload.issuer)!.publicKey).export({ type: 'spki', format: 'der' });
  if (approvalKey.equals(evidenceKey)) {
    return retain({ decision: 'REJECT', code: 'GATE_REJECT_AUTHORITY_SCOPE', reason: 'Loop approval and deployment verification require independent signing keys.' });
  }
  const probe = await probeLiveDeploymentUrl(proposal.target.liveUrl);
  if (!probe.ok) {
    return retain({
      decision: 'HOLD',
      code: 'GATE_HOLD_DEPLOYMENT_UNREACHABLE',
      reason: 'Signed deployment evidence did not pass HTTP reachability probe. Plane stays proposed.',
      verdict: 'unverified',
    });
  }
  return retain({ decision: 'PASS', code: 'GATE_PASS', reason: 'Trusted Loop approval and independent verification permit this exact artifact-bound transition. This receipt does not execute deployment or authorize a later phase.', verdict: 'real' });
}
