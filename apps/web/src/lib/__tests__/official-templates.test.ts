import { describe, expect, it } from 'vitest';
import { compileLinkedSop } from '@/lib/linked-sop';
import {
  deployHoldReason,
  officialTemplateFiles,
  pickOfficialTemplate,
  stackCheckItems,
  stackCheckStatus,
  stackCheckStatusLabel,
} from '@/lib/official-templates';

/** Live pBsT6v-ciO8 pack.stack.tools — none are runnable in UVAI. */
const DOGFOOD_PACK_TOOLS = [
  { name: 'SeaDance 2.5' },
  { name: 'Claude Fable 5' },
  { name: 'Character.ai' },
  { name: 'Cluely Desktop' },
] as const;

describe('official templates', () => {
  it('picks the create-next-app starter when Vercel/Next is in pack.stack.tools', () => {
    const sop = compileLinkedSop({
      transcript: 'Deploy this Next.js app on Vercel.',
      segments: [{ start: 4, duration: 3, text: 'Deploy this Next.js app on Vercel.' }],
      packTools: [{ name: 'Next.js' }, { name: 'Vercel' }],
    });
    const picked = pickOfficialTemplate(sop);
    expect(picked?.id).toBe('vercel-next');
    expect(picked?.clone).toContain('create-next-app');
    expect(picked?.repo).toContain('github.com/vercel/next.js');
    const files = officialTemplateFiles('my-app', sop);
    expect(files['src/index.ts']).toBeUndefined();
    expect(files['app/page.tsx']).toContain('export default function Page');
    expect(files['package.json']).toContain('"next"');
  });

  it('picks Shopify CLI init only when Shopify CLI is in pack.stack.tools', () => {
    const sop = compileLinkedSop({
      transcript: 'Use the Shopify CLI, not the plugin.',
      segments: [{ start: 10, duration: 2, text: 'Use the Shopify CLI, not the plugin.' }],
      packTools: [{ name: 'Shopify CLI' }],
    });
    const picked = pickOfficialTemplate(sop);
    expect(picked?.id).toBe('shopify-cli');
    expect(picked?.clone).toContain('@shopify/app');
    const files = officialTemplateFiles('bagel-shop', sop);
    expect(files['src/index.ts']).toBeUndefined();
    expect(files['SHOPIFY.md']).toContain('shopify.dev');
  });

  it('does not invent a starter when no official stack is named', () => {
    const sop = compileLinkedSop({
      transcript: 'The host talks about bagels and local news.',
      segments: [{ start: 0, duration: 2, text: 'The host talks about bagels and local news.' }],
    });
    expect(pickOfficialTemplate(sop)).toBeNull();
    expect(officialTemplateFiles('talk', sop)['src/index.ts']).toBeUndefined();
  });
});

describe('deployHoldReason', () => {
  it('holds signed-in production only while runnable stack checks are unchecked', () => {
    const sop = compileLinkedSop({
      transcript: 'Ship on Vercel after GitHub checks.',
      segments: [{ start: 1, duration: 2, text: 'Ship on Vercel after GitHub checks.' }],
      packTools: [{ name: 'Vercel' }, { name: 'GitHub' }],
    });
    const stack = stackCheckItems(sop);
    expect(stack.length).toBeGreaterThan(0);
    expect(deployHoldReason(sop, [], 'signed-in')).toMatch(/held/i);
    expect(deployHoldReason(sop, stack.map((item) => item.id), 'signed-in')).toBeNull();
  });

  it('does not hold anonymous Deploy for runnable vendor checks', () => {
    const sop = compileLinkedSop({
      transcript: 'Ship on Vercel after GitHub checks.',
      segments: [{ start: 1, duration: 2, text: 'Ship on Vercel after GitHub checks.' }],
      packTools: [{ name: 'Vercel' }, { name: 'GitHub' }],
    });
    expect(deployHoldReason(sop, [])).toBeNull();
    expect(deployHoldReason(sop, [], 'anonymous')).toBeNull();
    const first = stackCheckItems(sop)[0];
    expect(first).toBeDefined();
    expect(stackCheckStatus(first, [], 'anonymous')).toBe('skip');
    expect(stackCheckStatusLabel('skip')).toMatch(/not runnable while signed out/i);
  });

  it('does not hold anonymous Deploy on pBsT6v-ciO8 seadance/cluely checks', () => {
    const sop = compileLinkedSop({
      transcript: 'SeaDance 2.5, Claude Fable 5, Character.ai, and Cluely Desktop.',
      segments: [
        {
          start: 0,
          duration: 4,
          text: 'SeaDance 2.5, Claude Fable 5, Character.ai, and Cluely Desktop.',
        },
      ],
      packTools: [...DOGFOOD_PACK_TOOLS],
    });
    const stack = stackCheckItems(sop);
    expect(stack).toHaveLength(4);
    expect(stack.map((item) => item.title).join(' ')).toMatch(/SeaDance|Cluely/i);
    expect(deployHoldReason(sop, [])).toBeNull();
    expect(deployHoldReason(sop, [], 'signed-in')).toBeNull();
    for (const item of stack) {
      expect(stackCheckStatus(item, [], 'anonymous')).toBe('unknown');
      expect(stackCheckStatus(item, [], 'signed-in')).toBe('unknown');
    }
    expect(stackCheckStatusLabel('unknown')).toMatch(/cannot run this check/i);
  });

  it('does not let unknown tool checks hold a signed-in Vercel pack', () => {
    const sop = compileLinkedSop({
      transcript: 'Vercel plus Cluely Desktop.',
      segments: [{ start: 1, duration: 2, text: 'Vercel plus Cluely Desktop.' }],
      packTools: [{ name: 'Vercel' }, { name: 'Cluely Desktop' }],
    });
    const stack = stackCheckItems(sop);
    const cluely = stack.find((item) => /cluely/i.test(item.title));
    const vercel = stack.filter((item) => item.stack === 'vercel');
    expect(cluely).toBeDefined();
    expect(vercel.length).toBeGreaterThan(0);
    expect(stackCheckStatus(cluely!, [], 'signed-in')).toBe('unknown');
    expect(deployHoldReason(sop, vercel.map((item) => item.id), 'signed-in')).toBeNull();
  });

  it('does not hold when the video named no deploy stack', () => {
    const sop = compileLinkedSop({
      transcript: 'The host talks about bagels.',
      segments: [{ start: 0, duration: 2, text: 'The host talks about bagels.' }],
    });
    expect(deployHoldReason(sop, [])).toBeNull();
  });
});
