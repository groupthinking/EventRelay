/**
 * Linked SOP compiler.
 *
 * After verified captions land, label the tools the video named, attach only
 * official docs, and turn speech order into a checklist. Unknown names do not
 * get invented URLs. Stack checklists (Vercel Deployment Checks, Shopify CLI)
 * are appended only when that stack is actually in the transcript.
 */

import { formatSeconds } from '@/lib/timestamp';

export type EntityKind = 'tool' | 'product' | 'process' | 'platform';

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
    name: 'Shopify CLI',
    aliases: ['shopify cli'],
    kind: 'tool',
    officialUrl: 'https://shopify.dev/docs/api/shopify-cli',
    docsUrl: 'https://shopify.dev/docs/api/shopify-cli',
    stack: 'shopify',
  },
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
    title: 'Use Shopify CLI, not a storefront plugin, for store work',
    href: 'https://shopify.dev/docs/api/shopify-cli',
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
    pattern: /shopify cli/i,
    title: 'Use Shopify CLI, not the plugin',
    description: 'The video SOP is the CLI on the agent machine.',
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
  return a === b || a.includes(b) || b.includes(a);
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

  const steps: SopStep[] = [];
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
    steps.push({
      id: `sop_${steps.length + 1}`,
      order: steps.length + 1,
      title: event.title,
      description: event.description,
      timestamp: hits.timestamps[0] ?? event.timestamp,
      quote: hits.quote,
      entityNames: entityNamesIn(`${event.title} ${event.description}`, entities),
    });
  }

  for (const hint of SOP_HINTS) {
    const hits = findHits(text, segments, hint.pattern);
    if (hits.timestamps.length === 0 && !hint.pattern.test(text)) continue;
    if (steps.some((step) => similarTitle(step.title, hint.title))) continue;
    steps.push({
      id: `sop_${steps.length + 1}`,
      order: steps.length + 1,
      title: hint.title,
      description: hint.description,
      timestamp: hits.timestamps[0],
      quote: hits.quote,
      entityNames: entityNamesIn(`${hint.title} ${hint.description}`, entities),
    });
  }

  if (steps.length === 0) {
    for (const action of input.actions || []) {
      const title = (action.title || '').trim();
      if (!title) continue;
      const hits = findHits(title, segments, new RegExp(escapeRe(title.split(' ').slice(0, 5).join(' ')), 'i'));
      steps.push({
        id: `sop_${steps.length + 1}`,
        order: steps.length + 1,
        title,
        description: (action.description || '').trim(),
        timestamp: hits.timestamps[0],
        quote: hits.quote,
        entityNames: entityNamesIn(`${title} ${action.description || ''}`, entities),
      });
    }
  }

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

  return { entities, steps, checklist };
}

export function renderDeployMarkdown(sop: LinkedSop): string {
  const lines: string[] = [
    '# Deploy checklist',
    '',
    'Compiled from the video SOP plus official stack docs. Do not invent extra steps.',
    '',
    '## Video SOP',
    '',
  ];
  if (sop.steps.length === 0) {
    lines.push('_No timed SOP steps in this run._', '');
  } else {
    for (const step of sop.steps) {
      const when = step.timestamp != null ? ` [${formatSeconds(step.timestamp)}]` : '';
      lines.push(`- [ ] ${step.title}${when}`);
      if (step.description) lines.push(`  ${step.description}`);
    }
    lines.push('');
  }

  const stackItems = sop.checklist.filter((item) => item.source === 'stack');
  lines.push('## Industry checks', '');
  if (stackItems.length === 0) {
    lines.push('_No Vercel/Shopify/GitHub stack detected in the transcript._', '');
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
