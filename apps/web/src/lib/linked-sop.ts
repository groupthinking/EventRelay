/**
 * Linked SOP compiler.
 *
 * After verified captions land, label the tools the video named, attach only
 * official docs, and turn speech order into a checklist. Unknown names do not
 * get invented URLs. Stack checklists (Vercel Deployment Checks, GitHub Actions)
 * are appended only when that stack is actually in the transcript.
 *
 * Each named process in the video includes hyperlinks to all labeled tools
 * referenced or required at that milestone. Processes required to achieve the
 * intent goal of the video that were not specifically named in speech (such as
 * environment/secret provisioning, dependency installation, and preflight test
 * gates) are synthesized, classified as 'implied', and labeled as
 * 'Required by intent (unstated)'.
 */

import { formatSeconds } from '@/lib/timestamp';

export type EntityKind = 'tool' | 'product' | 'process' | 'platform';
export type ProcessType = 'named' | 'implied';

export interface ProcessToolLink {
  name: string;
  kind: EntityKind;
  officialUrl: string;
  docsUrl?: string;
}

export interface LinkedEntity {
  name: string;
  kind: EntityKind;
  officialUrl: string;
  docsUrl?: string;
  timestamps: number[];
  quote?: string;
}

export interface SopStep {
  id: string;
  order: number;
  title: string;
  description: string;
  timestamp?: number;
  quote?: string;
  entityNames: string[];
  /** Hyperlinks to official vendor documentation/sites for tools labeled in this process */
  tools?: ProcessToolLink[];
  /** Classification: 'named' (explicitly in video) vs 'implied' (required by intent, unstated) */
  processType?: ProcessType;
  /** UI badge / label describing origin: 'Named in video' | 'Required by intent (unstated)' */
  processLabel?: string;
}

export interface ChecklistItem {
  id: string;
  source: 'video-sop' | 'stack';
  stack?: string;
  title: string;
  href?: string;
  timestamp?: number;
}

export interface LinkedSop {
  intentGoal?: string;
  entities: LinkedEntity[];
  steps: SopStep[];
  checklist: ChecklistItem[];
}

export interface CatalogEntry {
  name: string;
  aliases: string[];
  kind: EntityKind;
  officialUrl: string;
  docsUrl?: string;
  stack?: string;
}

export interface LinkedSopInput {
  title?: string;
  summary?: string;
  transcript?: string;
  segments?: Array<{ start: number; duration?: number; text: string }>;
  events?: Array<{ timestamp?: number; label?: string; title?: string; description?: string }>;
  actions?: Array<{ title?: string; description?: string; category?: string }>;
  topics?: string[];
}

interface StackCheck {
  stack: string;
  title: string;
  href: string;
}

/** Official vendor docs only. Aliases are matched in the transcript, longest first. */
export const OFFICIAL_CATALOG: CatalogEntry[] = [
  {
    name: 'Shopify',
    aliases: ['shopify'],
    kind: 'platform',
    officialUrl: 'https://shopify.dev',
    docsUrl: 'https://shopify.dev/docs',
    stack: 'shopify',
  },
  {
    name: 'Vercel',
    aliases: ['vercel'],
    kind: 'platform',
    officialUrl: 'https://vercel.com',
    docsUrl: 'https://vercel.com/docs/deployments',
    stack: 'vercel',
  },
  {
    name: 'Next.js',
    aliases: ['next.js', 'nextjs'],
    kind: 'product',
    officialUrl: 'https://nextjs.org',
    docsUrl: 'https://nextjs.org/docs',
    stack: 'vercel',
  },
  {
    name: 'GitHub',
    aliases: ['github', 'github actions'],
    kind: 'platform',
    officialUrl: 'https://github.com',
    docsUrl: 'https://docs.github.com',
    stack: 'github',
  },
  {
    name: 'Beehiiv',
    aliases: ['beehiiv', 'beehive'],
    kind: 'product',
    officialUrl: 'https://www.beehiiv.com',
    docsUrl: 'https://developers.beehiiv.com',
  },
  {
    name: 'Notion',
    aliases: ['notion'],
    kind: 'product',
    officialUrl: 'https://www.notion.com',
    docsUrl: 'https://developers.notion.com',
  },
  {
    name: 'Gmail',
    aliases: ['gmail'],
    kind: 'product',
    officialUrl: 'https://developers.google.com/gmail',
    docsUrl: 'https://developers.google.com/gmail/api',
  },
  {
    name: 'Slack',
    aliases: ['slack'],
    kind: 'product',
    officialUrl: 'https://api.slack.com',
    docsUrl: 'https://api.slack.com/docs',
  },
  {
    name: 'Make',
    aliases: ['make.com'],
    kind: 'tool',
    officialUrl: 'https://www.make.com',
    docsUrl: 'https://www.make.com/en/help',
  },
  {
    name: 'Google AI Studio',
    aliases: ['google ai studio', 'ai studio'],
    kind: 'product',
    officialUrl: 'https://aistudio.google.com',
    docsUrl: 'https://ai.google.dev',
  },
  {
    name: 'Gemini',
    aliases: ['gemini'],
    kind: 'product',
    officialUrl: 'https://ai.google.dev',
    docsUrl: 'https://ai.google.dev/gemini-api/docs',
  },
  {
    name: 'Grok',
    aliases: ['grokbot', 'grockbot', 'grok bot', 'grok'],
    kind: 'product',
    officialUrl: 'https://grok.com',
    docsUrl: 'https://docs.x.ai',
  },
  {
    name: 'Hugging Face',
    aliases: ['hugging face', 'huggingface'],
    kind: 'platform',
    officialUrl: 'https://huggingface.co',
    docsUrl: 'https://huggingface.co/docs',
  },
  {
    name: 'Stripe',
    aliases: ['stripe'],
    kind: 'product',
    officialUrl: 'https://stripe.com',
    docsUrl: 'https://docs.stripe.com',
  },
  {
    name: 'Supabase',
    aliases: ['supabase'],
    kind: 'platform',
    officialUrl: 'https://supabase.com',
    docsUrl: 'https://supabase.com/docs',
  },
  {
    name: 'Cloudflare',
    aliases: ['cloudflare'],
    kind: 'platform',
    officialUrl: 'https://developers.cloudflare.com',
    docsUrl: 'https://developers.cloudflare.com',
  },
  {
    name: 'FastAPI',
    aliases: ['fastapi'],
    kind: 'tool',
    officialUrl: 'https://fastapi.tiangolo.com',
    docsUrl: 'https://fastapi.tiangolo.com',
  },
  {
    name: 'React',
    aliases: ['react'],
    kind: 'tool',
    officialUrl: 'https://react.dev',
    docsUrl: 'https://react.dev',
  },
];

const STACK_CHECKS: StackCheck[] = [
  {
    stack: 'vercel',
    title: 'Link the GitHub repo with Vercel for GitHub',
    href: 'https://vercel.com/docs/git/vercel-for-github',
  },
  {
    stack: 'vercel',
    title: 'Hold production until Deployment Checks pass',
    href: 'https://vercel.com/docs/deployment-checks',
  },
  {
    stack: 'vercel',
    title: 'Keep GitHub Action job names unique and stable',
    href: 'https://vercel.com/docs/deployment-checks',
  },
  {
    stack: 'vercel',
    title: 'Promote only after checks pass (or Force Promote deliberately)',
    href: 'https://vercel.com/docs/deployments/promoting-a-deployment',
  },
  {
    stack: 'shopify',
    title: 'Verify app scopes and API access in Shopify Partner Dashboard',
    href: 'https://shopify.dev/docs/apps/launch',
  },
  {
    stack: 'github',
    title: 'Use GitHub Actions statuses that Vercel can import as checks',
    href: 'https://docs.github.com/en/actions',
  },
];

const SOP_HINTS: Array<{ pattern: RegExp; title: string; description: string }> = [
  {
    pattern: /chief of staff/i,
    title: 'Start with a chief of staff agent',
    description: 'Let it audit the business and name the first teammates.',
  },
  {
    pattern: /week (one|1)\b/i,
    title: 'Week 1 — build the initial team',
    description: 'Stand up the smallest team that can run the mission.',
  },
  {
    pattern: /week (two|2)\b/i,
    title: 'Week 2 — execute without adding agents',
    description: 'Run the work. No new agents, no tinkering.',
  },
  {
    pattern: /week (three|3)\b/i,
    title: 'Week 3 — hire and fire against real gaps',
    description: 'Add or remove agents only after a week of execution.',
  },
  {
    pattern: /week (four|4)\b/i,
    title: 'Week 4 — automate routines',
    description: 'Add cron/routines after the team already works.',
  },
  {
    pattern: /one project per|one grokbot account|one grok bot account/i,
    title: 'One project per account',
    description: 'Keep context and tokens on a single mission.',
  },
];

function escapeRe(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function haystack(input: LinkedSopInput): string {
  const parts = [
    input.transcript || '',
    ...(input.segments || []).map((s) => s.text),
    ...(input.topics || []),
    ...(input.events || []).map((e) => `${e.label || e.title || ''} ${e.description || ''}`),
    ...(input.actions || []).map((a) => `${a.title || ''} ${a.description || ''}`),
  ];
  return parts.join('\n');
}

function findHits(
  text: string,
  segments: LinkedSopInput['segments'],
  pattern: RegExp,
): { timestamps: number[]; quote?: string } {
  const flags = pattern.flags.includes('g') ? pattern.flags : `${pattern.flags}g`;
  const global = new RegExp(pattern.source, flags);
  if (!global.test(text) && !(segments || []).some((s) => pattern.test(s.text))) {
    return { timestamps: [] };
  }
  const timestamps: number[] = [];
  let quote: string | undefined;
  for (const segment of segments || []) {
    if (!pattern.test(segment.text)) continue;
    if (Number.isFinite(segment.start)) timestamps.push(Math.max(0, Math.floor(segment.start)));
    if (!quote) quote = segment.text.trim();
  }
  return { timestamps: [...new Set(timestamps)].slice(0, 6), quote };
}

function entityNamesIn(text: string, entities: LinkedEntity[]): string[] {
  return entities
    .filter((entity) => {
      const pattern = new RegExp(`(^|[^a-z0-9])${escapeRe(entity.name)}([^a-z0-9]|$)`, 'i');
      return pattern.test(text);
    })
    .map((entity) => entity.name);
}

function similarTitle(left: string, right: string): boolean {
  const norm = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const a = norm(left);
  const b = norm(right);
  if (!a || !b) return false;
  if (a === b || a.includes(b) || b.includes(a)) return true;
  const wordsA = a.split(' ').filter((w) => w.length >= 4);
  const wordsB = new Set(b.split(' ').filter((w) => w.length >= 4));
  const overlap = wordsA.filter((w) => wordsB.has(w));
  return overlap.length >= 2 || (overlap.length >= 1 && (wordsA.length <= 2 || wordsB.size <= 2));
}

function toolsForProcess(
  text: string,
  timestamp: number | undefined,
  entities: LinkedEntity[],
  segments?: LinkedSopInput['segments'],
): ProcessToolLink[] {
  const result: ProcessToolLink[] = [];
  const added = new Set<string>();

  const addEntity = (entity: LinkedEntity) => {
    if (added.has(entity.name)) return;
    added.add(entity.name);
    result.push({
      name: entity.name,
      kind: entity.kind,
      officialUrl: entity.officialUrl,
      docsUrl: entity.docsUrl,
    });
  };

  // 1. Direct name match in step title or description
  for (const entity of entities) {
    const pattern = new RegExp(`(^|[^a-z0-9])${escapeRe(entity.name)}([^a-z0-9]|$)`, 'i');
    if (pattern.test(text)) {
      addEntity(entity);
    }
  }

  // 2. Proximity match by timestamp (within +/- 20s)
  if (timestamp != null) {
    for (const entity of entities) {
      if (entity.timestamps.some((t) => Math.abs(t - timestamp) <= 20)) {
        addEntity(entity);
      }
    }
  }

  // 3. Segment text matching near the timestamp
  if (timestamp != null && segments) {
    const nearbySegments = segments.filter((s) => Math.abs(s.start - timestamp) <= 8);
    for (const seg of nearbySegments) {
      for (const entity of entities) {
        const pattern = new RegExp(`(^|[^a-z0-9])${escapeRe(entity.name)}([^a-z0-9]|$)`, 'i');
        if (pattern.test(seg.text)) {
          addEntity(entity);
        }
      }
    }
  }

  return result;
}

function resolveIntentGoal(input: LinkedSopInput, namedSteps: SopStep[]): string {
  if (input.summary?.trim()) {
    const firstSentence = input.summary.trim().split(/[.!?]\s/)[0];
    if (firstSentence) return firstSentence.trim().replace(/\.$/, '');
  }
  if (input.title?.trim()) {
    return input.title.trim();
  }
  if (input.topics && input.topics.length > 0) {
    return `Implement solution using ${input.topics.slice(0, 3).join(', ')}`;
  }
  if (namedSteps.length > 0) {
    return `Execute workflow: ${namedSteps[0].title}`;
  }
  return 'Achieve workflow objective and deploy solution';
}

function synthesizeImpliedProcesses(
  input: LinkedSopInput,
  entities: LinkedEntity[],
  namedSteps: SopStep[],
): SopStep[] {
  const implied: SopStep[] = [];
  const isNamedAlready = (term: string) =>
    namedSteps.some((step) => similarTitle(step.title, term) || similarTitle(step.description, term));

  // Labeled tools and platforms
  const toolEntities = entities.filter(
    (e) => e.kind === 'tool' || e.kind === 'product' || e.kind === 'platform',
  );

  // 1. Environment & API Credential Configuration
  if (toolEntities.length > 0) {
    const credTitle = 'Configure environment variables and credentials';
    if (!isNamedAlready('environment') && !isNamedAlready('credentials') && !isNamedAlready('api keys') && !isNamedAlready('secrets')) {
      const toolLinks: ProcessToolLink[] = toolEntities.map((e) => ({
        name: e.name,
        kind: e.kind,
        officialUrl: e.officialUrl,
        docsUrl: e.docsUrl,
      }));
      implied.push({
        id: 'sop_implied_env',
        order: 0,
        title: credTitle,
        description: `Provision API keys and secrets for ${toolEntities.map((t) => t.name).slice(0, 4).join(', ')}.`,
        entityNames: toolEntities.map((t) => t.name),
        tools: toolLinks,
        processType: 'implied',
        processLabel: 'Required by intent (unstated)',
      });
    }
  }

  // 2. Local Runtime & Dependency Setup
  if (toolEntities.length > 0) {
    const setupTitle = 'Initialize workspace and install tool dependencies';
    if (!isNamedAlready('install') && !isNamedAlready('dependencies') && !isNamedAlready('workspace setup')) {
      const toolLinks: ProcessToolLink[] = toolEntities.map((e) => ({
        name: e.name,
        kind: e.kind,
        officialUrl: e.officialUrl,
        docsUrl: e.docsUrl,
      }));
      implied.push({
        id: 'sop_implied_setup',
        order: 0,
        title: setupTitle,
        description: 'Install SDKs and initialize dependencies required to interact with the target toolchain.',
        entityNames: toolEntities.map((t) => t.name),
        tools: toolLinks,
        processType: 'implied',
        processLabel: 'Required by intent (unstated)',
      });
    }
  }

  // 3. Unstated actions from analysis (when timed events exist and actions supplement them)
  if ((input.events || []).length > 0) {
    for (const action of input.actions || []) {
      const title = (action.title || '').trim();
      if (!title) continue;
      if (isNamedAlready(title) || implied.some((s) => similarTitle(s.title, title))) continue;

      const matchedTools = toolsForProcess(
        `${title} ${action.description || ''}`,
        undefined,
        entities,
        input.segments,
      );

      implied.push({
        id: `sop_implied_${implied.length + 1}`,
        order: 0,
        title,
        description: (action.description || '').trim() || 'Required task to achieve the video intent goal.',
        entityNames: matchedTools.map((t) => t.name),
        tools: matchedTools,
        processType: 'implied',
        processLabel: 'Required by intent (unstated)',
      });
    }
  }

  // 4. Preflight Verification & Integration Checks (when tech tools/platforms are in play)
  if (toolEntities.length > 0) {
    const verifyTitle = 'Run preflight verification and integration checks';
    if (!isNamedAlready('verification') && !isNamedAlready('testing') && !isNamedAlready('checks') && !isNamedAlready('smoke test')) {
      implied.push({
        id: 'sop_implied_verify',
        order: 0,
        title: verifyTitle,
        description: 'Validate end-to-end integration and smoke test components before promoting to production.',
        entityNames: [],
        tools: [],
        processType: 'implied',
        processLabel: 'Required by intent (unstated)',
      });
    }
  }

  return implied;
}

export function compileLinkedSop(input: LinkedSopInput): LinkedSop {
  const text = haystack(input);
  const segments = input.segments || [];
  const catalog = [...OFFICIAL_CATALOG].sort(
    (a, b) => Math.max(...b.aliases.map((x) => x.length)) - Math.max(...a.aliases.map((x) => x.length)),
  );

  const entities: LinkedEntity[] = [];
  const used = new Set<string>();
  for (const entry of catalog) {
    if (used.has(entry.name)) continue;
    const aliasHit = entry.aliases.find((alias) => {
      const pattern = new RegExp(`(^|[^a-z0-9])${escapeRe(alias)}([^a-z0-9]|$)`, 'i');
      return pattern.test(text);
    });
    if (!aliasHit) continue;
    used.add(entry.name);
    const hits = findHits(
      text,
      segments,
      new RegExp(`(^|[^a-z0-9])${escapeRe(aliasHit)}([^a-z0-9]|$)`, 'i'),
    );
    entities.push({
      name: entry.name,
      kind: entry.kind,
      officialUrl: entry.officialUrl,
      docsUrl: entry.docsUrl,
      timestamps: hits.timestamps,
      quote: hits.quote,
    });
  }

  const namedSteps: SopStep[] = [];
  const timedEvents = [...(input.events || [])]
    .map((event) => ({
      title: (event.label || event.title || '').trim(),
      description: (event.description || '').trim(),
      timestamp: Number.isFinite(event.timestamp) ? Math.floor(Number(event.timestamp)) : undefined,
    }))
    .filter((event) => event.title)
    .sort((a, b) => (a.timestamp ?? 1e12) - (b.timestamp ?? 1e12));

  for (const event of timedEvents) {
    const hits = event.timestamp != null
      ? { timestamps: [event.timestamp], quote: segments.find((s) => Math.abs(s.start - event.timestamp!) < 8)?.text.trim() }
      : findHits(event.title, segments, new RegExp(escapeRe(event.title.split(' ').slice(0, 4).join(' ')), 'i'));

    const stepText = `${event.title} ${event.description}`;
    const stepEntities = entityNamesIn(stepText, entities);
    const stepTools = toolsForProcess(stepText, hits.timestamps[0] ?? event.timestamp, entities, segments);

    namedSteps.push({
      id: `sop_${namedSteps.length + 1}`,
      order: namedSteps.length + 1,
      title: event.title,
      description: event.description,
      timestamp: hits.timestamps[0] ?? event.timestamp,
      quote: hits.quote,
      entityNames: stepEntities,
      tools: stepTools,
      processType: 'named',
      processLabel: 'Named in video',
    });
  }

  for (const hint of SOP_HINTS) {
    const hits = findHits(text, segments, hint.pattern);
    if (hits.timestamps.length === 0 && !hint.pattern.test(text)) continue;
    if (namedSteps.some((step) => similarTitle(step.title, hint.title))) continue;

    const hintText = `${hint.title} ${hint.description}`;
    const hintEntities = entityNamesIn(hintText, entities);
    const hintTools = toolsForProcess(hintText, hits.timestamps[0], entities, segments);

    namedSteps.push({
      id: `sop_${namedSteps.length + 1}`,
      order: namedSteps.length + 1,
      title: hint.title,
      description: hint.description,
      timestamp: hits.timestamps[0],
      quote: hits.quote,
      entityNames: hintEntities,
      tools: hintTools,
      processType: 'named',
      processLabel: 'Named in video',
    });
  }

  if (namedSteps.length === 0) {
    for (const action of input.actions || []) {
      const title = (action.title || '').trim();
      if (!title) continue;
      const hits = findHits(title, segments, new RegExp(escapeRe(title.split(' ').slice(0, 5).join(' ')), 'i'));
      const actionText = `${title} ${action.description || ''}`;
      const actionEntities = entityNamesIn(actionText, entities);
      const actionTools = toolsForProcess(actionText, hits.timestamps[0], entities, segments);

      namedSteps.push({
        id: `sop_${namedSteps.length + 1}`,
        order: namedSteps.length + 1,
        title,
        description: (action.description || '').trim(),
        timestamp: hits.timestamps[0],
        quote: hits.quote,
        entityNames: actionEntities,
        tools: actionTools,
        processType: 'named',
        processLabel: 'Named in video',
      });
    }
  }

  const impliedSteps = synthesizeImpliedProcesses(input, entities, namedSteps);
  const steps: SopStep[] = [...namedSteps, ...impliedSteps].map((step, idx) => ({
    ...step,
    id: `sop_${idx + 1}`,
    order: idx + 1,
  }));

  const intentGoal = resolveIntentGoal(input, namedSteps);

  const stacks = new Set(
    entities
      .map((entity) => OFFICIAL_CATALOG.find((entry) => entry.name === entity.name)?.stack)
      .filter((stack): stack is string => Boolean(stack)),
  );

  const checklist: ChecklistItem[] = steps.map((step) => ({
    id: `chk_${step.id}`,
    source: 'video-sop',
    title: step.title,
    timestamp: step.timestamp,
  }));

  for (const check of STACK_CHECKS) {
    if (!stacks.has(check.stack)) continue;
    checklist.push({
      id: `chk_${check.stack}_${checklist.length + 1}`,
      source: 'stack',
      stack: check.stack,
      title: check.title,
      href: check.href,
    });
  }

  return { intentGoal, entities, steps, checklist };
}

export function renderDeployMarkdown(sop: LinkedSop): string {
  const lines: string[] = [
    '# Deploy checklist',
    '',
    'Compiled from the video SOP plus official stack docs. Do not invent extra steps.',
    '',
  ];

  if (sop.intentGoal) {
    lines.push(`**Intent Goal:** ${sop.intentGoal}`, '');
  }

  const namedSteps = sop.steps.filter((s) => s.processType !== 'implied');
  lines.push('## Video SOP (Named Processes)', '');
  if (namedSteps.length === 0) {
    lines.push('_No timed SOP steps in this run._', '');
  } else {
    for (const step of namedSteps) {
      const when = step.timestamp != null ? ` [${formatSeconds(step.timestamp)}]` : '';
      lines.push(`- [ ] ${step.title}${when}`);
      if (step.description) lines.push(`  ${step.description}`);
      if (step.tools && step.tools.length > 0) {
        const toolLinks = step.tools.map((t) => {
          const docs = t.docsUrl && t.docsUrl !== t.officialUrl ? ` ([docs](${t.docsUrl}))` : '';
          return `[${t.name}](${t.officialUrl})${docs}`;
        });
        lines.push(`  Tools: ${toolLinks.join(', ')}`);
      }
    }
    lines.push('');
  }

  const impliedSteps = sop.steps.filter((s) => s.processType === 'implied');
  if (impliedSteps.length > 0) {
    lines.push('## Required Processes (Implied by Intent, Unstated in Video)', '');
    for (const step of impliedSteps) {
      lines.push(`- [ ] ${step.title} *(Required by intent)*`);
      if (step.description) lines.push(`  ${step.description}`);
      if (step.tools && step.tools.length > 0) {
        const toolLinks = step.tools.map((t) => {
          const docs = t.docsUrl && t.docsUrl !== t.officialUrl ? ` ([docs](${t.docsUrl}))` : '';
          return `[${t.name}](${t.officialUrl})${docs}`;
        });
        lines.push(`  Tools: ${toolLinks.join(', ')}`);
      }
    }
    lines.push('');
  }

  const stackItems = sop.checklist.filter((item) => item.source === 'stack');
  lines.push('## Industry checks', '');
  if (stackItems.length === 0) {
    lines.push('_No Vercel/GitHub stack detected in the transcript._', '');
  } else {
    for (const item of stackItems) {
      const link = item.href ? ` ([docs](${item.href}))` : '';
      lines.push(`- [ ] ${item.title}${link}`);
    }
    lines.push('');
  }

  if (sop.entities.length > 0) {
    lines.push('## Named tools', '');
    for (const entity of sop.entities) {
      const docs = entity.docsUrl && entity.docsUrl !== entity.officialUrl
        ? ` — [docs](${entity.docsUrl})`
        : '';
      lines.push(`- [${entity.name}](${entity.officialUrl})${docs}`);
    }
    lines.push('');
  }
  return lines.join('\n');
}

