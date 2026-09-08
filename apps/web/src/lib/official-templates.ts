/**
 * Official starters for Export, and a hold-gate for Deploy.
 *
 * Templates are the vendor CLI/repo, not invented architecture.
 * Signed-in Deploy stays held only while runnable vendor checks (Vercel
 * Deployment Checks, Shopify CLI, GitHub Actions) are still open.
 * Anonymous viewers and non-runnable pack tools (SeaDance, Cluely, …)
 * get honest skip/unknown — they do not hold Deploy.
 */

import type { ChecklistItem, LinkedSop } from '@/lib/linked-sop';

export type StudioViewer = 'anonymous' | 'signed-in';
export type StackCheckStatus = 'pending' | 'done' | 'skip' | 'unknown';

/** Stacks UVAI can actually verify in-product. Pack-named tools are unknown. */
const RUNNABLE_STACKS = new Set(['vercel', 'shopify', 'github']);

export interface OfficialTemplate {
  id: 'vercel-next' | 'shopify-cli';
  stack: string;
  name: string;
  clone: string;
  repo: string;
  docsUrl: string;
}

const NEXT: OfficialTemplate = {
  id: 'vercel-next',
  stack: 'vercel',
  name: 'create-next-app',
  clone: 'npx create-next-app@latest',
  repo: 'https://github.com/vercel/next.js/tree/canary/packages/create-next-app',
  docsUrl: 'https://nextjs.org/docs/app/getting-started/installation',
};

const SHOPIFY: OfficialTemplate = {
  id: 'shopify-cli',
  stack: 'shopify',
  name: 'Shopify CLI app',
  clone: 'npm init @shopify/app@latest',
  repo: 'https://github.com/Shopify/cli',
  docsUrl: 'https://shopify.dev/docs/apps/build/cli-for-apps',
};

export function detectedStacks(sop: LinkedSop | null | undefined): Set<string> {
  const stacks = new Set<string>();
  for (const item of sop?.checklist || []) {
    if (item.source === 'stack' && item.stack) stacks.add(item.stack);
  }
  return stacks;
}

export function stackCheckItems(sop: LinkedSop | null | undefined): ChecklistItem[] {
  return (sop?.checklist || []).filter((item) => item.source === 'stack');
}

export function isRunnableStackCheck(item: ChecklistItem): boolean {
  return item.source === 'stack' && Boolean(item.stack && RUNNABLE_STACKS.has(item.stack));
}

export function stackCheckStatus(
  item: ChecklistItem,
  completedIds: Iterable<string>,
  viewer: StudioViewer = 'anonymous',
): StackCheckStatus {
  const done = new Set(completedIds);
  if (done.has(item.id)) return 'done';
  if (!isRunnableStackCheck(item)) return 'unknown';
  if (viewer === 'anonymous') return 'skip';
  return 'pending';
}

export function stackCheckStatusLabel(status: StackCheckStatus): string {
  switch (status) {
    case 'done':
      return 'Done';
    case 'pending':
      return 'Pending';
    case 'skip':
      return 'Skip — not runnable while signed out';
    case 'unknown':
      return 'Unknown — UVAI cannot run this check';
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}

export function pickOfficialTemplate(sop: LinkedSop | null | undefined): OfficialTemplate | null {
  const stacks = detectedStacks(sop);
  if (stacks.has('vercel')) return NEXT;
  if (stacks.has('shopify')) return SHOPIFY;
  return null;
}

export function deployHoldReason(
  sop: LinkedSop | null | undefined,
  completedIds: Iterable<string>,
  viewer: StudioViewer = 'anonymous',
): string | null {
  const pending = stackCheckItems(sop).filter(
    (item) => stackCheckStatus(item, completedIds, viewer) === 'pending',
  );
  if (pending.length === 0) return null;
  return `Production is held until ${pending.length} stack check(s) pass. Next: ${pending[0].title}`;
}

function nextAppFiles(projectName: string): Record<string, string> {
  return {
    'package.json': `${JSON.stringify({
      name: projectName,
      private: true,
      scripts: {
        dev: 'next dev',
        build: 'next build',
        start: 'next start',
      },
      dependencies: {
        next: '^15.5.0',
        react: '^19.1.0',
        'react-dom': '^19.1.0',
      },
      devDependencies: {
        '@types/node': '^22',
        '@types/react': '^19',
        '@types/react-dom': '^19',
        typescript: '^5',
      },
    }, null, 2)}\n`,
    'tsconfig.json': `${JSON.stringify({
      compilerOptions: {
        target: 'ES2017',
        lib: ['dom', 'dom.iterable', 'esnext'],
        allowJs: true,
        skipLibCheck: true,
        strict: true,
        noEmit: true,
        esModuleInterop: true,
        module: 'esnext',
        moduleResolution: 'bundler',
        resolveJsonModule: true,
        isolatedModules: true,
        jsx: 'preserve',
        incremental: true,
        plugins: [{ name: 'next' }],
        paths: { '@/*': ['./*'] },
      },
      include: ['next-env.d.ts', '**/*.ts', '**/*.tsx', '.next/types/**/*.ts'],
      exclude: ['node_modules'],
    }, null, 2)}\n`,
    'next.config.ts': `import type { NextConfig } from 'next';\n\nconst nextConfig: NextConfig = {};\n\nexport default nextConfig;\n`,
    'app/layout.tsx': `export default function RootLayout({\n  children,\n}: Readonly<{ children: React.ReactNode }>) {\n  return (\n    <html lang="en">\n      <body>{children}</body>\n    </html>\n  );\n}\n`,
    'app/page.tsx': `export default function Page() {\n  return (\n    <main>\n      <h1>${projectName}</h1>\n      <p>Official Next.js App Router starter. Prefer <code>npx create-next-app@latest</code> when scaffolding a new repo.</p>\n    </main>\n  );\n}\n`,
  };
}

function shopifyGuide(projectName: string, template: OfficialTemplate): string {
  return `# ${projectName} — Shopify CLI

Use the official CLI. Do not invent a storefront plugin.

\`\`\`bash
${template.clone}
\`\`\`

Docs: ${template.docsUrl}
CLI source: ${template.repo}
`;
}

export function officialTemplateFiles(
  projectName: string,
  sop: LinkedSop | null | undefined,
): Record<string, string> {
  const template = pickOfficialTemplate(sop);
  if (!template) return {};
  if (template.id === 'vercel-next') {
    return {
      ...nextAppFiles(projectName),
      'TEMPLATE.md': `# Official template\n\n${template.clone}\n\n${template.repo}\n\n${template.docsUrl}\n`,
    };
  }
  return { 'SHOPIFY.md': shopifyGuide(projectName, template) };
}
