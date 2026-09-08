/**
 * G.A.T.E. transition contract — Governed Acceptance & Transition Engine.
 *
 * Zero-Sim asks: is the evidence real?
 * G.A.T.E. asks: do verified evidence + authority permit this state transition?
 *
 * G.A.T.E. does not build artifacts and is not a project database.
 * Missing evidence → HOLD. Weak/unverified evidence → HOLD.
 * Unreal or a live claim without a verified receipt → REJECT.
 * Unknown authority or an unknown Zero-Sim verdict → ESCALATE.
 */

import { studioVerifiedLiveUrl } from '@/lib/studio-pipeline-status';

export const GATE_RECEIPT_VERSION = 'eventrelay.gate-receipt.v1' as const;

export type GateDecision = 'PASS' | 'HOLD' | 'REJECT' | 'ESCALATE';

export type ZeroSimVerdict = 'real' | 'unverified' | 'unreal';

export type GateAuthorityActor = 'anonymous' | 'signed-in' | 'system';

export const KNOWN_AUTHORITY_ACTORS: ReadonlySet<string> = new Set([
  'anonymous',
  'signed-in',
  'system',
]);

export interface GateEvidenceRef {
  kind: string;
  id?: string;
  hash?: string;
  uri?: string;
}

export interface ZeroSimResult {
  verdict: ZeroSimVerdict;
  reason_code: string;
}

export interface GateAuthority {
  actor: string;
  claim?: string;
}

export interface GateTransitionRequest {
  transitionId: string;
  kind: string;
  fromState: string;
  toState: string;
  evidenceRefs: GateEvidenceRef[];
  authority: GateAuthority;
  zeroSim?: ZeroSimResult;
  issuedAt?: string;
}

export interface GateReceipt {
  version: typeof GATE_RECEIPT_VERSION;
  id: string;
  kind: string;
  transition_id: string;
  from_state: string;
  to_state: string;
  decision: GateDecision;
  reason_code: string;
  reason: string;
  evidence_refs: GateEvidenceRef[];
  authority: GateAuthority;
  zero_sim: ZeroSimResult;
  issued_at: string;
  receipt_hash: string;
}

export interface GateEvaluation {
  decision: GateDecision;
  reason: string;
  reason_code: string;
  receipt: GateReceipt;
}

export interface StudioDeployGateInput {
  transitionId: string;
  runId?: string;
  jobId?: string;
  liveUrl?: string | null;
  runStatus?: string | null;
  kind?: string | null;
  /** Caller-supplied backend/handoff text (e.g. missing BACKEND_URL). Cited, never invented. */
  backendReason?: string | null;
  authority: GateAuthority;
  issuedAt?: string;
}

export interface StudioGateReceiptView {
  decision: GateDecision;
  reason: string;
  reason_code: string;
  receiptId: string;
  receiptHash: string;
  version: typeof GATE_RECEIPT_VERSION;
}

const SHA256_HEX = /^[a-f0-9]{64}$/;

const SHA256_K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4,
  0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe,
  0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
  0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc,
  0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116,
  0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
  0xc67178f2,
]);

function rotr(value: number, bits: number): number {
  return (value >>> bits) | (value << (32 - bits));
}

/** SHA-256 of UTF-8 text. Client-safe (no node:crypto) so Studio can import this module. */
export function hashCanonical(message: string): string {
  const bytes = new TextEncoder().encode(message);
  const bitLen = bytes.length * 8;
  const padLen = (((bytes.length + 9 + 63) >> 6) << 6);
  const padded = new Uint8Array(padLen);
  padded.set(bytes);
  padded[bytes.length] = 0x80;
  const view = new DataView(padded.buffer);
  view.setUint32(padLen - 4, bitLen >>> 0, false);

  let h0 = 0x6a09e667;
  let h1 = 0xbb67ae85;
  let h2 = 0x3c6ef372;
  let h3 = 0xa54ff53a;
  let h4 = 0x510e527f;
  let h5 = 0x9b05688c;
  let h6 = 0x1f83d9ab;
  let h7 = 0x5be0cd19;
  const w = new Uint32Array(64);

  for (let i = 0; i < padLen; i += 64) {
    for (let t = 0; t < 16; t += 1) {
      w[t] = view.getUint32(i + t * 4, false);
    }
    for (let t = 16; t < 64; t += 1) {
      const s0 = rotr(w[t - 15], 7) ^ rotr(w[t - 15], 18) ^ (w[t - 15] >>> 3);
      const s1 = rotr(w[t - 2], 17) ^ rotr(w[t - 2], 19) ^ (w[t - 2] >>> 10);
      w[t] = (w[t - 16] + s0 + w[t - 7] + s1) >>> 0;
    }
    let a = h0;
    let b = h1;
    let c = h2;
    let d = h3;
    let e = h4;
    let f = h5;
    let g = h6;
    let h = h7;
    for (let t = 0; t < 64; t += 1) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const temp1 = (h + S1 + ch + SHA256_K[t] + w[t]) >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const temp2 = (S0 + maj) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }
    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
    h5 = (h5 + f) >>> 0;
    h6 = (h6 + g) >>> 0;
    h7 = (h7 + h) >>> 0;
  }

  return [h0, h1, h2, h3, h4, h5, h6, h7]
    .map((word) => word.toString(16).padStart(8, '0'))
    .join('');
}

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value !== null && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) {
      sorted[key] = sortValue(record[key]);
    }
    return sorted;
  }
  return value;
}

export function canonicalGateJson(value: unknown): string {
  return JSON.stringify(sortValue(value));
}

function liveRefValue(ref: GateEvidenceRef): string | null {
  return studioVerifiedLiveUrl(ref.uri ?? ref.id ?? null);
}

function presentedLiveValue(ref: GateEvidenceRef): string {
  return (ref.uri ?? ref.id ?? '').trim();
}

export function assessZeroSim(input: {
  result?: ZeroSimResult;
  evidenceRefs?: GateEvidenceRef[];
}): ZeroSimResult {
  const refs = input.evidenceRefs ?? [];
  if (input.result) {
    const candidate = input.result;
    if (candidate.verdict === 'unreal') {
      return candidate;
    }
    if (candidate.verdict === 'real') {
      if (refs.length === 0) {
        return { verdict: 'unverified', reason_code: 'ZERO_SIM_MISSING_EVIDENCE' };
      }
      for (const ref of refs) {
        if (ref.hash && !SHA256_HEX.test(ref.hash)) {
          return { verdict: 'unreal', reason_code: 'ZERO_SIM_UNREAL' };
        }
        if (ref.kind === 'live_url' && presentedLiveValue(ref) && !liveRefValue(ref)) {
          return { verdict: 'unreal', reason_code: 'ZERO_SIM_UNREAL' };
        }
      }
      return candidate;
    }
    if (refs.length === 0) {
      return { verdict: 'unverified', reason_code: 'ZERO_SIM_MISSING_EVIDENCE' };
    }
    for (const ref of refs) {
      if (ref.hash && !SHA256_HEX.test(ref.hash)) {
        return { verdict: 'unreal', reason_code: 'ZERO_SIM_UNREAL' };
      }
      if (ref.kind === 'live_url' && presentedLiveValue(ref) && !liveRefValue(ref)) {
        return { verdict: 'unreal', reason_code: 'ZERO_SIM_UNREAL' };
      }
    }
    return { verdict: 'unverified', reason_code: 'ZERO_SIM_UNVERIFIED' };
  }
  if (refs.length === 0) {
    return { verdict: 'unverified', reason_code: 'ZERO_SIM_MISSING_EVIDENCE' };
  }
  for (const ref of refs) {
    if (ref.hash && !SHA256_HEX.test(ref.hash)) {
      return { verdict: 'unreal', reason_code: 'ZERO_SIM_UNREAL' };
    }
    if (ref.kind === 'live_url' && presentedLiveValue(ref) && !liveRefValue(ref)) {
      return { verdict: 'unreal', reason_code: 'ZERO_SIM_UNREAL' };
    }
  }
  return { verdict: 'unverified', reason_code: 'ZERO_SIM_UNVERIFIED' };
}

function finish(
  request: GateTransitionRequest,
  decision: GateDecision,
  reason_code: string,
  reason: string,
  zeroSim: ZeroSimResult,
): GateEvaluation {
  const issued_at = request.issuedAt ?? '1970-01-01T00:00:00.000Z';
  const body = {
    version: GATE_RECEIPT_VERSION,
    id: `er:gate:v1:${request.transitionId}`,
    kind: request.kind,
    transition_id: request.transitionId,
    from_state: request.fromState,
    to_state: request.toState,
    decision,
    reason_code,
    reason,
    evidence_refs: request.evidenceRefs,
    authority: request.authority,
    zero_sim: zeroSim,
    issued_at,
  };
  const receipt_hash = hashCanonical(canonicalGateJson(body));
  return {
    decision,
    reason,
    reason_code,
    receipt: { ...body, receipt_hash },
  };
}

export function evaluateTransition(request: GateTransitionRequest): GateEvaluation {
  const transitionId = (request.transitionId ?? '').trim();
  const kind = (request.kind ?? '').trim();
  const fromState = (request.fromState ?? '').trim();
  const toState = (request.toState ?? '').trim();
  const actor = request.authority?.actor ?? '';
  if (!transitionId || !kind || !fromState || !toState) {
    return finish(
      request,
      'REJECT',
      'GATE_REJECT_INVALID_TRANSITION',
      'Transition id, kind, and from→to states are required.',
      request.zeroSim ?? { verdict: 'unverified', reason_code: 'ZERO_SIM_MISSING_EVIDENCE' },
    );
  }

  if (!actor || !KNOWN_AUTHORITY_ACTORS.has(actor)) {
    return finish(
      request,
      'ESCALATE',
      'GATE_ESCALATE_AUTHORITY_UNKNOWN',
      `Authority actor "${actor || 'unknown'}" is not a known G.A.T.E. actor.`,
      request.zeroSim ?? { verdict: 'unverified', reason_code: 'ZERO_SIM_UNVERIFIED' },
    );
  }

  if (request.zeroSim && !isZeroSimVerdict(request.zeroSim.verdict)) {
    return finish(
      request,
      'ESCALATE',
      'GATE_ESCALATE_ZERO_SIM_UNKNOWN',
      'Zero-Sim verdict is not real, unverified, or unreal — G.A.T.E. will not invent one.',
      request.zeroSim,
    );
  }

  const zeroSim = assessZeroSim({
    result: request.zeroSim,
    evidenceRefs: request.evidenceRefs,
  });

  const liveRefs = request.evidenceRefs.filter((ref) => ref.kind === 'live_url');
  const verifiedLive = liveRefs.map(liveRefValue).find((url): url is string => Boolean(url));
  const claimedLiveWithoutReceipt =
    toState === 'live' && liveRefs.some((ref) => presentedLiveValue(ref)) && !verifiedLive;

  if (claimedLiveWithoutReceipt) {
    return finish(
      request,
      'REJECT',
      'GATE_REJECT_CLAIM_MISMATCH',
      'Claimed live transition without a verified https live URL (hostname required).',
      zeroSim,
    );
  }

  if (zeroSim.verdict === 'unreal') {
    return finish(
      request,
      'REJECT',
      'GATE_REJECT_UNREAL_EVIDENCE',
      'Zero-Sim marked the evidence unreal. G.A.T.E. will not invent a substitute.',
      zeroSim,
    );
  }

  if ((toState === 'live' || kind === 'studio.deploy') && !verifiedLive) {
    return finish(
      request,
      'HOLD',
      'GATE_HOLD_MISSING_EVIDENCE',
      'Live transition is held — no verified live URL receipt.',
      zeroSim,
    );
  }

  if (zeroSim.verdict === 'unverified') {
    const code =
      request.evidenceRefs.length === 0
        ? 'GATE_HOLD_MISSING_EVIDENCE'
        : 'GATE_HOLD_WEAK_EVIDENCE';
    return finish(
      request,
      'HOLD',
      code,
      code === 'GATE_HOLD_MISSING_EVIDENCE'
        ? 'Required evidence refs are missing. Plane stays proposed.'
        : 'Evidence is present but unverified. Plane stays proposed.',
      zeroSim,
    );
  }

  return finish(
    request,
    'PASS',
    'GATE_PASS',
    'Verified evidence and known authority permit this transition.',
    zeroSim,
  );
}

function isZeroSimVerdict(value: string): value is ZeroSimVerdict {
  return value === 'real' || value === 'unverified' || value === 'unreal';
}

export function evaluateStudioDeployTransition(
  input: StudioDeployGateInput,
): GateEvaluation {
  const presented = input.liveUrl?.trim() ?? '';
  const verified = studioVerifiedLiveUrl(input.liveUrl);
  const evidenceRefs: GateEvidenceRef[] = [];
  if (presented) {
    evidenceRefs.push({ kind: 'live_url', id: presented, uri: presented });
  }
  if (input.runId?.trim()) {
    evidenceRefs.push({ kind: 'run_id', id: input.runId.trim() });
  }
  if (input.jobId?.trim()) {
    evidenceRefs.push({ kind: 'job_id', id: input.jobId.trim() });
  }
  if (input.runStatus?.trim()) {
    evidenceRefs.push({ kind: 'run_status', id: input.runStatus.trim() });
  }
  if (input.kind?.trim()) {
    evidenceRefs.push({ kind: 'result_kind', id: input.kind.trim() });
  }
  if (input.backendReason?.trim()) {
    evidenceRefs.push({ kind: 'backend_reason', id: input.backendReason.trim() });
  }

  const zeroSim: ZeroSimResult | undefined = verified
    ? { verdict: 'real', reason_code: 'ZERO_SIM_REAL' }
    : presented
      ? { verdict: 'unreal', reason_code: 'ZERO_SIM_UNREAL' }
      : undefined;

  return evaluateTransition({
    transitionId: input.transitionId,
    kind: 'studio.deploy',
    fromState: 'proposed',
    toState: presented ? 'live' : 'proposed',
    evidenceRefs,
    authority: input.authority,
    zeroSim,
    issuedAt: input.issuedAt,
  });
}

/** runId when the workflow started; otherwise a citable attempt id (no invented receipt). */
export function studioDeployAttemptTransitionId(input: {
  runId?: string | null;
  videoId?: string | null;
}): string {
  const runId = input.runId?.trim();
  if (runId) return runId;
  const videoId = input.videoId?.trim();
  return videoId ? `attempt:${videoId}` : 'attempt:unknown';
}

/** Visible Studio chip: decision + short reason + receipt id/hash. */
export function studioGateReceiptView(
  evaluation: GateEvaluation,
  input?: { backendReason?: string | null },
): StudioGateReceiptView {
  const backend = input?.backendReason?.trim() ?? '';
  const reason =
    backend && !evaluation.reason.includes(backend)
      ? `${evaluation.reason} ${backend}`
      : evaluation.reason;
  return {
    decision: evaluation.decision,
    reason,
    reason_code: evaluation.reason_code,
    receiptId: evaluation.receipt.id,
    receiptHash: evaluation.receipt.receipt_hash,
    version: evaluation.receipt.version,
  };
}
