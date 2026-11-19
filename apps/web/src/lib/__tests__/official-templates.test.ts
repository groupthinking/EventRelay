import { describe, expect, it } from 'vitest';
import { compileLinkedSop } from '@/lib/linked-sop';
import {
  deployHoldReason,
  OFFICIAL_TEMPLATES,
  officialTemplateFiles,
  pickOfficialTemplate,
  stackCheckItems,
  stackCheckStatus,
  stackCheckStatusLabel,
  studioStackCheckView,
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

  it('exports the complete OFFICIAL_TEMPLATES catalog with verified GitHub repos and docs URLs', () => {
    expect(OFFICIAL_TEMPLATES.map((t) => t.id)).toEqual([
      'vercel-next',
      'shopify-cli',
      'webflow-devlink',
      'google-gemini-live',
      'openai-responses',
      'nvidia-genai',
      'groq-appgen',
    ]);
    for (const template of OFFICIAL_TEMPLATES) {
      expect(template.stack.length).toBeGreaterThan(0);
      expect(template.name.length).toBeGreaterThan(0);
      expect(template.clone.length).toBeGreaterThan(0);
      expect(template.repo).toMatch(/^https:\/\/github\.com\//);
      expect(template.docsUrl).toMatch(/^https:\/\//);
    }
  });

  it.each([
    {
      label: 'Webflow',
      toolName: 'Webflow DevLink',
      expectedId: 'webflow-devlink',
      expectedStack: 'webflow',
      expectedRepo: 'https://github.com/webflow/devlink-examples',
      expectedDocs: 'https://developers.webflow.com',
    },
    {
      label: 'Gemini',
      toolName: 'Gemini',
      expectedId: 'google-gemini-live',
      expectedStack: 'gemini',
      expectedRepo: 'https://github.com/google-gemini/live-api-web-console',
      expectedDocs: 'https://ai.google.dev/gemini-api/docs/live',
    },
    {
      label: 'Google AI Studio',
      toolName: 'Google AI Studio',
      expectedId: 'google-gemini-live',
      expectedStack: 'gemini',
      expectedRepo: 'https://github.com/google-gemini/live-api-web-console',
      expectedDocs: 'https://ai.google.dev/gemini-api/docs/live',
    },
    {
      label: 'OpenAI / ChatGPT',
      toolName: 'ChatGPT',
      expectedId: 'openai-responses',
      expectedStack: 'openai',
      expectedRepo: 'https://github.com/openai/openai-responses-starter-app',
      expectedDocs: 'https://platform.openai.com/docs',
    },
    {
      label: 'NVIDIA',
      toolName: 'NVIDIA NIM',
      expectedId: 'nvidia-genai',
      expectedStack: 'nvidia',
      expectedRepo: 'https://github.com/NVIDIA/GenerativeAIExamples',
      expectedDocs: 'https://docs.nvidia.com/nim',
    },
    {
      label: 'Groq',
      toolName: 'GroqCloud',
      expectedId: 'groq-appgen',
      expectedStack: 'groq',
      expectedRepo: 'https://github.com/groq/groq-appgen',
      expectedDocs: 'https://console.groq.com/docs',
    },
  ])(
    'picks $expectedId and emits TEMPLATE.md when $label ($toolName) is in pack.stack.tools',
    ({ toolName, expectedId, expectedStack, expectedRepo, expectedDocs }) => {
      const sop = compileLinkedSop({
        transcript: `Build the workflow with ${toolName}.`,
        segments: [{ start: 2, duration: 3, text: `Build the workflow with ${toolName}.` }],
        packTools: [{ name: toolName }],
      });
      const picked = pickOfficialTemplate(sop);
      expect(picked?.id).toBe(expectedId);
      expect(picked?.stack).toBe(expectedStack);
      expect(picked?.repo).toBe(expectedRepo);
      expect(picked?.docsUrl).toBe(expectedDocs);

      const files = officialTemplateFiles('starter-demo', sop);
      expect(files['src/index.ts']).toBeUndefined();
      expect(files['SHOPIFY.md']).toBeUndefined();
      expect(files['TEMPLATE.md']).toContain('starter-demo');
      expect(files['TEMPLATE.md']).toContain(picked!.clone);
      expect(files['TEMPLATE.md']).toContain(expectedRepo);
      expect(files['TEMPLATE.md']).toContain(expectedDocs);
    },
  );

  it('preserves priority order so Vercel and Shopify take precedence over non-runnable starter stacks', () => {
    const vercelAndGemini = compileLinkedSop({
      transcript: 'Deploy Gemini Live on Vercel.',
      segments: [{ start: 1, duration: 2, text: 'Deploy Gemini Live on Vercel.' }],
      packTools: [{ name: 'Gemini' }, { name: 'Vercel' }],
    });
    expect(pickOfficialTemplate(vercelAndGemini)?.id).toBe('vercel-next');

    const shopifyAndOpenAI = compileLinkedSop({
      transcript: 'Run Shopify CLI with OpenAI.',
      segments: [{ start: 1, duration: 2, text: 'Run Shopify CLI with OpenAI.' }],
      packTools: [{ name: 'OpenAI' }, { name: 'Shopify CLI' }],
    });
    expect(pickOfficialTemplate(shopifyAndOpenAI)?.id).toBe('shopify-cli');
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
    expect(studioStackCheckView(first, [], 'anonymous').holdsShip).toBe(false);
    expect(studioStackCheckView(first, [], 'signed-in').holdsShip).toBe(true);
    expect(studioStackCheckView(first, [first.id], 'signed-in').holdsShip).toBe(false);
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
    const rows = stack.map((item) => studioStackCheckView(item, [], 'anonymous'));
    expect(rows.every((row) => row.status === 'unknown')).toBe(true);
    expect(rows.every((row) => row.holdsShip === false)).toBe(true);
    expect(rows[0]?.statusLabel).toMatch(/cannot run this check/i);
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

  it('keeps deployHoldReason null for non-runnable starter stacks (webflow, gemini, openai, nvidia, groq)', () => {
    const sop = compileLinkedSop({
      transcript: 'Combine Webflow, Gemini, OpenAI, NVIDIA NIM, and Groq.',
      segments: [
        {
          start: 0,
          duration: 5,
          text: 'Combine Webflow, Gemini, OpenAI, NVIDIA NIM, and Groq.',
        },
      ],
      packTools: [
        { name: 'Webflow' },
        { name: 'Gemini' },
        { name: 'OpenAI' },
        { name: 'NVIDIA' },
        { name: 'Groq' },
      ],
    });
    const stack = stackCheckItems(sop);
    expect(stack).toHaveLength(5);
    expect(deployHoldReason(sop, [], 'anonymous')).toBeNull();
    expect(deployHoldReason(sop, [], 'signed-in')).toBeNull();
    for (const item of stack) {
      expect(stackCheckStatus(item, [], 'anonymous')).toBe('unknown');
      expect(stackCheckStatus(item, [], 'signed-in')).toBe('unknown');
      expect(studioStackCheckView(item, [], 'signed-in').holdsShip).toBe(false);
    }
  });
});
