export type SparkleInterviewAnswers = {
  useCase: string;
  trigger: string;
  tools: string[];
  constraints: string;
  successSignal: string;
};

const SPARKLE_RE = /\bsparkle\s*pills?\b/i;

function compact(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function compactList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => (typeof entry === 'string' ? entry.trim() : ''))
    .filter((entry) => entry.length > 0)
    .slice(0, 8);
}

function parseAnswers(value: unknown): SparkleInterviewAnswers | null {
  if (!value || typeof value !== 'object') return null;
  const source = value as Record<string, unknown>;
  const useCase = compact(source.useCase);
  const trigger = compact(source.trigger);
  const tools = compactList(source.tools);
  const constraints = compact(source.constraints);
  const successSignal = compact(source.successSignal);
  if (!useCase || !trigger || tools.length === 0 || !constraints || !successSignal) {
    return null;
  }
  return { useCase, trigger, tools, constraints, successSignal };
}

export function isSparklePillsRequest(query: string): boolean {
  return SPARKLE_RE.test(query);
}

export function sparklePillsInterviewQuestions(): string[] {
  return [
    'What exact chore or workflow should sparkle pills automate?',
    'What should trigger each run (time, event, or manual action)?',
    'Which tools and systems must it update (for example Calendar, Slack, email)?',
    'What rules or constraints must never be violated?',
    'How will you measure success each week?',
  ];
}

export function resolveSparklePillsResponse(input: {
  query: string;
  sparkleInterview?: unknown;
}):
  | {
      answer: string;
      requiresInterview: boolean;
      interviewQuestions: string[];
    }
  | {
      answer: string;
      requiresInterview: false;
      provider: 'sparkle-pills-planner';
      interview: SparkleInterviewAnswers;
    }
  | null {
  if (!isSparklePillsRequest(input.query)) return null;

  const interview = parseAnswers(input.sparkleInterview);
  if (!interview) {
    return {
      answer:
        'Before I design the system, I need a short use-case interview so the workflow stays concrete and executable.',
      requiresInterview: true,
      interviewQuestions: sparklePillsInterviewQuestions(),
    };
  }

  return {
    answer: [
      'Sparkle Pills System Plan',
      '',
      `1. Objective: ${interview.useCase}`,
      `2. Trigger: ${interview.trigger}`,
      `3. Integrations: ${interview.tools.join(', ')}`,
      `4. Guardrails: ${interview.constraints}`,
      `5. Success metric: ${interview.successSignal}`,
      '6. Execution loop: intake -> validate context -> run actions -> confirm outputs -> log weekly feedback.',
      '7. First rollout: ship one low-risk automation path, then expand after two stable weekly cycles.',
    ].join('\n'),
    requiresInterview: false,
    provider: 'sparkle-pills-planner',
    interview,
  };
}
