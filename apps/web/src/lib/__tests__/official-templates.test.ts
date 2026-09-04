import { describe, expect, it } from 'vitest';
import { compileLinkedSop } from '@/lib/linked-sop';
import {
  deployHoldReason,
  officialTemplateFiles,
  pickOfficialTemplate,
  stackCheckItems,
} from '@/lib/official-templates';

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
  it('holds production while stack checks are unchecked', () => {
    const sop = compileLinkedSop({
      transcript: 'Ship on Vercel after GitHub checks.',
      segments: [{ start: 1, duration: 2, text: 'Ship on Vercel after GitHub checks.' }],
      packTools: [{ name: 'Vercel' }, { name: 'GitHub' }],
    });
    const stack = stackCheckItems(sop);
    expect(stack.length).toBeGreaterThan(0);
    expect(deployHoldReason(sop, [])).toMatch(/held/i);
    expect(deployHoldReason(sop, stack.map((item) => item.id))).toBeNull();
  });

  it('does not hold when the video named no deploy stack', () => {
    const sop = compileLinkedSop({
      transcript: 'The host talks about bagels.',
      segments: [{ start: 0, duration: 2, text: 'The host talks about bagels.' }],
    });
    expect(deployHoldReason(sop, [])).toBeNull();
  });
});
