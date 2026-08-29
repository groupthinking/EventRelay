import { describe, expect, it } from 'vitest';
import {
  compileLinkedSop,
  renderDeployMarkdown,
  type LinkedSop,
} from '@/lib/linked-sop';

const GROK_TRANSCRIPT = `
Grockbot is here. Start with a chief of staff bot.
Week one we build the team. Week two we execute without adding agents.
Use the Shopify CLI, not the built-in plugin. Beehiiv sends the newsletter.
Give the team Notion and Gmail. Do not stuff four businesses in one Grokbot account.
`.trim();

describe('compileLinkedSop', () => {
  it('labels tools from speech and links only official docs', () => {
    const sop = compileLinkedSop({
      segments: [
        { start: 142, duration: 8, text: 'Start with a chief of staff bot.' },
        { start: 548, duration: 6, text: 'Use the Shopify CLI, not the built-in plugin.' },
        { start: 560, duration: 5, text: 'Beehiiv sends the newsletter through Notion.' },
      ],
      events: [
        { timestamp: 142, label: 'Start with a chief of staff', description: 'Audit the business first.' },
        { timestamp: 548, label: 'Use Shopify CLI', description: 'Not the plugin.' },
      ],
      actions: [{ title: 'Pick one project', description: 'One Grokbot account.', category: 'setup' }],
      topics: ['Grokbot', 'Shopify'],
    });

    const names = sop.entities.map((e) => e.name);
    expect(names).toEqual(expect.arrayContaining(['Shopify CLI', 'Beehiiv', 'Notion']));
    expect(sop.entities.find((e) => e.name === 'Shopify CLI')?.docsUrl).toMatch(/shopify\.dev/);
    expect(sop.entities.every((e) => !e.officialUrl || /^https:\/\//.test(e.officialUrl))).toBe(true);
    expect(sop.entities.some((e) => /audexum|madeup/i.test(e.officialUrl))).toBe(false);

    expect(sop.steps[0]?.title).toMatch(/chief of staff/i);
    expect(sop.steps[0]?.timestamp).toBe(142);
    expect(sop.steps.some((s) => /shopify cli/i.test(s.title))).toBe(true);
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
});

describe('renderDeployMarkdown', () => {
  it('writes official checklist links, not invented steps', () => {
    const sop: LinkedSop = {
      entities: [{
        name: 'Vercel',
        kind: 'platform',
        officialUrl: 'https://vercel.com',
        docsUrl: 'https://vercel.com/docs/deployments',
        timestamps: [12],
      }],
      steps: [{
        id: 'sop_1',
        order: 1,
        title: 'Ship the preview',
        description: 'From the video SOP.',
        timestamp: 12,
        entityNames: ['Vercel'],
      }],
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
  });
});
