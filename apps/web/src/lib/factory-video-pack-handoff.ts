import type { AppBuilderSandbox } from '@/lib/emit-app-builder-sandbox';
import {
  MISSION_CANVAS_FILENAME,
  validateJsonCanvas,
  type JsonCanvasFileNode,
  type JsonCanvasTextNode,
} from '@/lib/emit-json-canvas';
import { canonicalGateJson, hashCanonical } from '@/lib/gate-transition';

export const FACTORY_HANDOFF_RECEIPT_VERSION =
  'eventrelay.factory-video-pack-handoff-receipt.v1' as const;

export type FactoryHandoffDecision = 'DRY_RUN' | 'DUPLICATE' | 'HOLD';

export type FixtureFactoryHandoffInput = {
  sandbox: AppBuilderSandbox;
  existingFingerprints?: readonly string[];
  approvedPlanRevision?: string | null;
  requiresVisualProof?: boolean;
  issuedAt?: string;
};

export type FactoryCandidateTask = {
  fingerprint: string;
  title: string;
  description: string;
  source_node_id: string;
  evidence_refs: Array<{ kind: string; id: string; hash?: string }>;
  status: 'candidate' | 'blocked';
  block_reason: 'missing_visual_proof' | null;
};

export type FactoryHandoffReceipt = {
  version: typeof FACTORY_HANDOFF_RECEIPT_VERSION;
  mode: 'fixture-only';
  decision: FactoryHandoffDecision;
  reason_code:
    | 'FIXTURE_DRY_RUN'
    | 'DUPLICATE_CANDIDATE'
    | 'MISSING_VISUAL_PROOF';
  issued_at: string;
  inputs: {
    pack_id: string;
    video_id: string;
    source_hash: string;
    workspace_digest: string;
    mission_canvas_digest: string;
    plan_revision: string;
  };
  authorization: {
    status: 'NOT_GRANTED' | 'VALID_FOR_REVISION' | 'INVALIDATED';
    approved_revision: string | null;
    authority_effect: 'none';
    untrusted_inputs_cannot_grant_authority: true;
  };
  candidate: FactoryCandidateTask;
  deduplication: {
    matched_existing_fingerprint: boolean;
  };
  dry_run: {
    dispatch_state: 'not-executed';
    external_effects: 0;
    artifact_kind: 'issue';
    artifact_locator: string;
    artifact_observed: false;
  };
  receipt_hash: string;
};

const SHA256_HEX = /^[a-f0-9]{64}$/;

function digest(value: unknown): string {
  return hashCanonical(canonicalGateJson(value));
}

function firstSopNode(nodes: readonly unknown[]): JsonCanvasTextNode {
  const candidate = nodes.find(
    (node): node is JsonCanvasTextNode =>
      typeof node === 'object' &&
      node !== null &&
      (node as { type?: unknown }).type === 'text' &&
      typeof (node as { id?: unknown }).id === 'string' &&
      (node as { id: string }).id.startsWith('sop-step-'),
  );
  if (!candidate) {
    throw new Error('Factory handoff held: mission.canvas has no SOP candidate node.');
  }
  return candidate;
}

function taskText(node: JsonCanvasTextNode): { title: string; description: string } {
  const [heading = '', ...body] = node.text.split(/\n\n+/);
  const title = heading.replace(/^\d+\.\s*/, '').replace(/\s+\(\d+(?:\.\d+)?s\)$/, '').trim();
  if (!title) {
    throw new Error('Factory handoff held: SOP candidate title is empty.');
  }
  return { title, description: body.join('\n\n').trim() };
}

/**
 * Convert a sanitized Video Pack workspace into exactly one inert Factory
 * candidate and an append-only-style receipt. This function never calls a
 * tool, persists an artifact, or treats workspace content as authorization.
 */
export function createFixtureFactoryHandoff(
  input: FixtureFactoryHandoffInput,
): FactoryHandoffReceipt {
  const { sandbox } = input;
  if (!SHA256_HEX.test(sandbox.sourceHash)) {
    throw new Error('Factory handoff held: source_hash is invalid.');
  }
  const missionFile = sandbox.files[MISSION_CANVAS_FILENAME];
  if (!missionFile) {
    throw new Error('Factory handoff held: mission.canvas is required.');
  }

  const canvas = validateJsonCanvas(JSON.parse(missionFile));
  const sopNode = firstSopNode(canvas.nodes ?? []);
  const { title, description } = taskText(sopNode);
  const workspaceDigest = digest(sandbox.files);
  const missionCanvasDigest = digest(canvas);
  const planRevision = digest({
    pack_id: sandbox.packId,
    source_hash: sandbox.sourceHash,
    workspace_digest: workspaceDigest,
    mission_canvas_digest: missionCanvasDigest,
  });
  const fingerprint = digest({
    plan_revision: planRevision,
    source_node_id: sopNode.id,
    title,
    description,
  });
  const hasVisualProof = (canvas.nodes ?? []).some(
    (node): node is JsonCanvasFileNode => node.type === 'file',
  );
  const missingVisualProof = Boolean(input.requiresVisualProof && !hasVisualProof);
  const duplicate = new Set(input.existingFingerprints ?? []).has(fingerprint);
  const approvedRevision = input.approvedPlanRevision ?? null;
  const authorizationStatus: FactoryHandoffReceipt['authorization']['status'] =
    approvedRevision === null
      ? 'NOT_GRANTED'
      : approvedRevision === planRevision
        ? 'VALID_FOR_REVISION'
        : 'INVALIDATED';
  const decision: FactoryHandoffDecision = missingVisualProof
    ? 'HOLD'
    : duplicate
      ? 'DUPLICATE'
      : 'DRY_RUN';
  const reasonCode: FactoryHandoffReceipt['reason_code'] = missingVisualProof
    ? 'MISSING_VISUAL_PROOF'
    : duplicate
      ? 'DUPLICATE_CANDIDATE'
      : 'FIXTURE_DRY_RUN';
  const candidate: FactoryCandidateTask = {
    fingerprint,
    title,
    description,
    source_node_id: sopNode.id,
    evidence_refs: [
      { kind: 'video_pack', id: sandbox.packId, hash: sandbox.sourceHash },
      { kind: 'workspace', id: sandbox.contract, hash: workspaceDigest },
      { kind: 'mission_canvas', id: MISSION_CANVAS_FILENAME, hash: missionCanvasDigest },
      { kind: 'canvas_node', id: sopNode.id },
    ],
    status: missingVisualProof ? 'blocked' : 'candidate',
    block_reason: missingVisualProof ? 'missing_visual_proof' : null,
  };
  const body = {
    version: FACTORY_HANDOFF_RECEIPT_VERSION,
    mode: 'fixture-only' as const,
    decision,
    reason_code: reasonCode,
    issued_at: input.issuedAt ?? new Date().toISOString(),
    inputs: {
      pack_id: sandbox.packId,
      video_id: sandbox.videoId,
      source_hash: sandbox.sourceHash,
      workspace_digest: workspaceDigest,
      mission_canvas_digest: missionCanvasDigest,
      plan_revision: planRevision,
    },
    authorization: {
      status: authorizationStatus,
      approved_revision: approvedRevision,
      authority_effect: 'none' as const,
      untrusted_inputs_cannot_grant_authority: true as const,
    },
    candidate,
    deduplication: { matched_existing_fingerprint: duplicate },
    dry_run: {
      dispatch_state: 'not-executed' as const,
      external_effects: 0 as const,
      artifact_kind: 'issue' as const,
      artifact_locator: `fixture://factory/issues/${fingerprint}`,
      artifact_observed: false as const,
    },
  };
  return { ...body, receipt_hash: digest(body) };
}
