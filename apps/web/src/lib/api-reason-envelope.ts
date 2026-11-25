/**
 * Shared JSON envelope for API and hosted-spec failures.
 * Top-level responses use ok + reason_code (AXIOM-scored); avoid bare gateway strings alone.
 */
export type ReasonEnvelope = {
  ok: boolean;
  reason_code: string;
  detail?: string;
};

export function reasonEnvelope(
  ok: boolean,
  reason_code: string,
  detail?: string,
): ReasonEnvelope {
  if (detail !== undefined && detail !== '') {
    return { ok, reason_code, detail };
  }
  return { ok, reason_code };
}

export function reasonEnvelopeJson(
  envelope: ReasonEnvelope,
  extra?: Record<string, unknown>,
): Record<string, unknown> {
  return extra ? { ...extra, ...envelope } : { ...envelope };
}
