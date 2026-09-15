import 'server-only';

import type { Message, MessagesResolveAsyncData } from 'v0';
import { z } from 'zod';
import { StudioError } from './errors';

export const resolutionSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('answered-questions'),
    answers: z.array(z.object({
      questionId: z.string().min(1).max(256),
      selectedLabels: z.array(z.string().min(1).max(2000)).max(20),
      customText: z.string().trim().max(4000).optional(),
    }).strict()).min(1).max(20),
  }).strict(),
  z.object({
    type: z.literal('plan-exit-response'),
    status: z.enum(['approved', 'rejected', 'request-changes']),
    content: z.string().trim().max(8000),
  }).strict(),
  z.object({ type: z.literal('skip-integration') }).strict(),
]);
export type StudioResolution = z.infer<typeof resolutionSchema>;
type ProviderResolution = MessagesResolveAsyncData['body']['task'];

export function resolvePendingTask(message: Message, task: StudioResolution): ProviderResolution {
  const stale = () => new StudioError(409, 'interaction_changed', 'The pending action changed. Reload this chat.');
  const invalid = () => new StudioError(400, 'invalid_answers', 'Answer the current questions using the available options or your own text.');
  if (message.role !== 'assistant' || message.finishReason !== 'tool-calls') throw stale();
  const action = message.parts.findLast((part) => part.type === 'agent-action');
  if (!action || action.type !== 'agent-action' || !action.data) throw stale();
  const data = action.data;
  if (task.type === 'answered-questions') {
    if (action.name !== 'ask_user_questions' || !('questions' in data)) throw stale();
    if (task.answers.length !== data.questions.length || new Set(task.answers.map((answer) => answer.questionId)).size !== task.answers.length) throw invalid();
    return {
      type: 'answered-questions',
      answers: data.questions.map((question) => {
        const answer = task.answers.find((value) => value.questionId === question.id);
        if (!answer || (!answer.selectedLabels.length && !answer.customText)) throw invalid();
        if ((!question.multiSelect && answer.selectedLabels.length > 1) || new Set(answer.selectedLabels).size !== answer.selectedLabels.length) throw invalid();
        if (answer.selectedLabels.some((label) => !question.options.some((option) => option.label === label))) throw invalid();
        return { ...answer, questionText: question.question };
      }),
    };
  }
  if (task.type === 'plan-exit-response') {
    if (action.name !== 'exit_plan_mode' || !('plan' in data)) throw stale();
    if (task.status === 'request-changes' && !task.content) throw invalid();
    return task;
  }
  if (action.name !== 'get_or_request_integration' || !('requestedIntegrations' in data)) throw stale();
  // No connection is attested by the browser; skipping is the only supported receipt here.
  return { type: 'confirmed-steps', connectedIntegrationNames: [], connectedNpmRegistryIds: [], connectedMcpPresetNames: [] };
}
