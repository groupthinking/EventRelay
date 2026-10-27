/** Server-owned opt-in for persistent local review artifacts, never execution. */
import 'server-only';
import { createHash } from 'node:crypto';
import { createLocalReviewBridge } from './relay-local-review.mjs';

/**
 * Only operator environment config may select the interpreter/state directory.
 * A nonempty invalid mode fails closed rather than silently disabling a guard.
 */
export function resolveActionReviewJournal(env = process.env) {
  const mode = env.RELAY_REVIEW_JOURNAL_MODE;
  if (!mode) return null;
  if (mode !== 'local-review-only') throw new Error('Invalid local review journal mode');
  if (env.VERCEL || env.AWS_LAMBDA_FUNCTION_NAME || env.K_SERVICE) {
    throw new Error('Local review journal requires a persistent non-serverless host');
  }
  const bridge = createLocalReviewBridge({
    stateDirectory: env.RELAY_REVIEW_STATE_DIRECTORY,
    scriptsDirectory: env.RELAY_REVIEW_SCRIPTS_DIRECTORY,
    pythonExecutable: env.RELAY_REVIEW_PYTHON_EXECUTABLE,
  });
  return Object.freeze({
    async persist(actions, trustedIdentity) {
      if (typeof trustedIdentity !== 'string' || !trustedIdentity.trim()) {
        throw new Error('Trusted identity required for durable review plans');
      }
      // Do not store identity/transcript or trust a caller-supplied jobId as a
      // cross-user idempotency key. Exact plans are independently actor-scoped.
      const actorHash = createHash('sha256').update(trustedIdentity).digest('hex');
      const key = createHash('sha256').update(JSON.stringify({ actorHash, actions })).digest('hex');
      const result = await bridge.persistReview(actions, `review-v1-${key}`);
      if (!result.localReceipt.complete || result.originalActionsExecuted !== false ||
          result.originalTaskComplete !== false) {
        throw new Error('The local review artifact did not verify');
      }
      return {
        version: result.localReceipt.version,
        taskId: result.taskId,
        scope: 'local_artifact_only',
        state: result.localReceipt.state,
        artifactVerified: true,
        artifactHash: result.localReceipt.evidence.sha256,
        contractHash: result.localReceipt.contract_hash,
        historyHead: result.localReceipt.history_head,
        originalActionsExecuted: false,
        originalTaskComplete: false,
        cost: result.localReceipt.cost,
      };
    },
  });
}
