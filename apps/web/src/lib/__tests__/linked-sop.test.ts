import { describe, expect, it } from 'vitest';
import {
  compileLinkedSop,
  renderDeployMarkdown,
  type LinkedSop,
} from '@/lib/linked-sop';

const GROK_TRANSCRIPT = `
Grockbot is here. Start with a chief of staff bot.
Week one we build the team. Week two we execute without adding agents.
Use Shopify for store work. Beehiiv sends the newsletter.
Give the team Notion and Gmail. Do not stuff four businesses in one Grokbot account.
`.trim();

describe('compileLinkedSop', () => {
  it('labels tools from speech, removes Shopify CLI, attaches hyperlinks to processes, and labels unstated intent steps', () => {
    const sop = compileLinkedSop({
      segments: [
        { start: 142, duration: 8, text: 'Start with a chief of staff bot.' },
        { start: 548, duration: 6, text: 'Use Shopify for the store.' },
        { start: 560, duration: 5, text: 'Beehiiv sends the newsletter through Notion.' },
      ],
      events: [
        { timestamp: 142, label: 'Start with a chief of staff', description: 'Audit the business first.' },
        { timestamp: 548, label: 'Set up Shopify store', description: 'Configure online store.' },
      ],
      actions: [{ title: 'Pick one project', description: 'One Grokbot account.', category: 'setup' }],
      topics: ['Grokbot', 'Shopify'],
    });

    const names = sop.entities.map((e) => e.name);
    // Shopify CLI must NOT be present, general Shopify platform is present
    expect(names).not.toContain('Shopify CLI');
    expect(names).toEqual(expect.arrayContaining(['Shopify', 'Beehiiv', 'Notion']));
    expect(sop.entities.find((e) => e.name === 'Shopify')?.docsUrl).toMatch(/shopify\.dev/);
    expect(sop.entities.every((e) => !e.officialUrl || /^https:\/\//.test(e.officialUrl))).toBe(true);
    expect(sop.entities.some((e) => /audexum|madeup/i.test(e.officialUrl))).toBe(false);

    // Named process assertions
    const namedSteps = sop.steps.filter((s) => s.processType === 'named');
    expect(namedSteps.length).toBeGreaterThan(0);
    expect(namedSteps[0]?.title).toMatch(/chief of staff/i);
    expect(namedSteps[0]?.timestamp).toBe(142);
    expect(namedSteps[0]?.processLabel).toBe('Named in video');

    // Hyperlinks to labeled tools on each named process
    const shopifyStep = namedSteps.find((s) => s.title.includes('Shopify'));
    expect(shopifyStep).toBeDefined();
    expect(shopifyStep?.tools?.some((t) => t.name === 'Shopify' && t.officialUrl.includes('shopify.dev'))).toBe(true);

    // Unstated processes required to achieve the intent goal are synthesized and labeled
    const impliedSteps = sop.steps.filter((s) => s.processType === 'implied');
    expect(impliedSteps.length).toBeGreaterThan(0);
    expect(impliedSteps.every((s) => s.processLabel === 'Required by intent (unstated)')).toBe(true);
    expect(
      impliedSteps.some(
        (s) =>
          s.title.includes('environment variables') ||
          s.title.includes('dependencies') ||
          s.title.includes('verification'),
      ),
    ).toBe(true);
  });

  it('appends the Vercel deployment-check list only when Vercel is in the speech', () => {
    const withVercel = compileLinkedSop({
      transcript: 'Deploy the Next.js app on Vercel after GitHub checks pass.',
      segments: [{ start: 10, duration: 4, text: 'Deploy the Next.js app on Vercel after GitHub checks pass.' }],
    });
    expect(withVercel.entities.map((e) => e.name)).toEqual(expect.arrayContaining(['Vercel', 'Next.js', 'GitHub']));
    expect(withVercel.checklist.some((item) => item.source === 'stack' && item.stack === 'vercel')).toBe(true);
    expect(withVercel.checklist.some((item) => item.href?.includes('deployment-checks'))).toBe(true);

    const without = compileLinkedSop({
      transcript: GROK_TRANSCRIPT,
      segments: [{ start: 0, duration: 5, text: GROK_TRANSCRIPT }],
    });
    expect(without.checklist.some((item) => item.stack === 'vercel')).toBe(false);
  });

  it('does not invent a URL for an unknown product name', () => {
    const sop = compileLinkedSop({
      transcript: 'We used Zorpify to orchestrate the pipeline.',
      segments: [{ start: 3, duration: 2, text: 'We used Zorpify to orchestrate the pipeline.' }],
      topics: ['Zorpify'],
    });
    expect(sop.entities.find((e) => /zorpify/i.test(e.name))).toBeUndefined();
  });

  it('uses speech SOP hints, then analysis actions when there are no timed events', () => {
    const hinted = compileLinkedSop({
      transcript: 'Set up the chief of staff then run week one.',
      actions: [{ title: 'Create the chief of staff', description: 'Let it audit.', category: 'setup' }],
    });
    expect(hinted.steps.map((s) => s.title)).toEqual([
      'Start with a chief of staff agent',
      'Week 1 — build the initial team',
    ]);

    const fromActions = compileLinkedSop({
      transcript: 'Ship the preview after the captions land.',
      actions: [
        { title: 'Create the preview', description: 'From this run.', category: 'setup' },
        { title: 'Attach the checklist', description: 'Official docs only.', category: 'deploy' },
      ],
    });
    expect(fromActions.steps.map((s) => s.title)).toEqual([
      'Create the preview',
      'Attach the checklist',
    ]);
  });

  it('matches catalog aliases in process steps and guards against React English-verb false positives', () => {
    const falsePositive = compileLinkedSop({
      transcript: 'Watch how users react to the new pricing page.',
      segments: [{ start: 5, duration: 3, text: 'Watch how users react to the new pricing page.' }],
    });
    expect(falsePositive.entities.find((e) => e.name === 'React')).toBeUndefined();

    const aliasSop = compileLinkedSop({
      transcript: 'We use NextJS with React components and TypeScript.',
      segments: [{ start: 10, duration: 4, text: 'We use NextJS with React components and TypeScript.' }],
      events: [
        { timestamp: 40, label: 'Deploy NextJS', description: 'Push React UI and TypeScript build.' },
      ],
    });
    expect(aliasSop.entities.map((e) => e.name)).toEqual(
      expect.arrayContaining(['Next.js', 'React', 'TypeScript']),
    );
    const deployStep = aliasSop.steps.find((s) => s.title === 'Deploy NextJS');
    expect(deployStep?.entityNames).toEqual(expect.arrayContaining(['Next.js', 'React', 'TypeScript']));
    expect(deployStep?.tools?.map((t) => t.name)).toEqual(
      expect.arrayContaining(['Next.js', 'React', 'TypeScript']),
    );
    // Non-credentialed frameworks should not trigger credential provisioning
    expect(aliasSop.steps.some((s) => s.title.includes('environment variables and credentials'))).toBe(false);
  });

  it('generates stack-specific implied processes, separates checklist sources, and avoids over-broad deduplication', () => {
    const sop = compileLinkedSop({
      transcript: 'Install Chrome extension, then wire Supabase, Stripe, and Vercel with OpenAI.',
      segments: [
        { start: 5, duration: 4, text: 'Install Chrome extension first.' },
        { start: 15, duration: 5, text: 'Wire Supabase, Stripe, and Vercel with OpenAI.' },
      ],
      events: [
        { timestamp: 5, label: 'Install Chrome extension', description: 'Helper browser tool.' },
      ],
    });

    const impliedTitles = sop.steps.filter((s) => s.processType === 'implied').map((s) => s.title);
    expect(impliedTitles).toEqual(
      expect.arrayContaining([
        'Configure environment variables and credentials',
        'Initialize workspace and install tool dependencies',
        'Apply schema migrations and verify database access/security rules',
        'Configure webhook endpoints and verify webhook signing secrets',
        'Set production environment variables and configure preview/production branch rules',
        'Run preflight verification and integration checks',
      ]),
    );

    expect(sop.checklist.some((c) => c.source === 'video-sop' && c.title === 'Install Chrome extension')).toBe(true);
    expect(
      sop.checklist.some(
        (c) => c.source === 'intent-required' && c.title === 'Configure webhook endpoints and verify webhook signing secrets',
      ),
    ).toBe(true);
  });
});

describe('renderDeployMarkdown', () => {
  it('writes official checklist links, tool hyperlinks for named processes, and labeled unstated processes', () => {
    const sop: LinkedSop = {
      intentGoal: 'Deploy modern Next.js application to production',
      entities: [{
        name: 'Vercel',
        kind: 'platform',
        officialUrl: 'https://vercel.com',
        docsUrl: 'https://vercel.com/docs/deployments',
        timestamps: [12],
      }],
      steps: [
        {
          id: 'sop_1',
          order: 1,
          title: 'Ship the preview',
          description: 'From the video SOP.',
          timestamp: 12,
          entityNames: ['Vercel'],
          tools: [{
            name: 'Vercel',
            kind: 'platform',
            officialUrl: 'https://vercel.com',
            docsUrl: 'https://vercel.com/docs/deployments',
          }],
          processType: 'named',
          processLabel: 'Named in video',
        },
        {
          id: 'sop_2',
          order: 2,
          title: 'Configure environment variables and credentials',
          description: 'Provision API keys for production.',
          entityNames: ['Vercel'],
          tools: [{
            name: 'Vercel',
            kind: 'platform',
            officialUrl: 'https://vercel.com',
            docsUrl: 'https://vercel.com/docs/deployments',
          }],
          processType: 'implied',
          processLabel: 'Required by intent (unstated)',
        },
      ],
      checklist: [{
        id: 'chk_vercel_1',
        source: 'stack',
        stack: 'vercel',
        title: 'Hold production until Deployment Checks pass',
        href: 'https://vercel.com/docs/deployment-checks',
      }],
    };
    const md = renderDeployMarkdown(sop);
    expect(md).toContain('https://vercel.com/docs/deployment-checks');
    expect(md).toContain('Ship the preview');
    expect(md).toMatch(/\[12s\]|0:12/);
    // Verifies hyperlinks to labeled tools are rendered for the process
    expect(md).toContain('[Vercel](https://vercel.com)');
    expect(md).toContain('([docs](https://vercel.com/docs/deployments))');
    // Verifies unstated processes required for the intent are rendered under their own section
    expect(md).toContain('## Required Processes (Implied by Intent, Unstated in Video)');
    expect(md).toContain('Configure environment variables and credentials *(Required by intent)*');
  });
});
