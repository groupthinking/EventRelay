import type { AgentAction } from './action-lifecycle';

export interface LocalArtifactReceipt {
  version: 'relay.local-receipt.v1';
  taskId: string;
  scope: 'local_artifact_only';
  state: 'complete';
  artifactVerified: true;
  artifactHash: string;
  contractHash: string;
  historyHead: string;
  originalActionsExecuted: false;
  originalTaskComplete: false;
  cost: {
    amount: null;
    currency: null;
    status: 'unknown';
    note: string;
  };
}

export interface ActionReviewJournal {
  persist(actions: AgentAction[], trustedIdentity: string | null): Promise<LocalArtifactReceipt>;
}

export function resolveActionReviewJournal(
  env?: NodeJS.ProcessEnv,
): ActionReviewJournal | null;
