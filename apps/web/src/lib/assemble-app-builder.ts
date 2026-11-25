import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { promisify } from 'node:util';
import {
  APP_BUILDER_PINNED_DEPS,
  emitAppBuilderSandbox,
  type AppBuilderSandbox,
  type AppBuilderSandboxInput,
  type AppBuilderSandboxIngredients,
} from '@/lib/emit-app-builder-sandbox';

const execFileAsync = promisify(execFile);

export const ASSEMBLY_CONTRACT = 'app-builder-assembly' as const;
export const ASSEMBLY_CUT = 'pack→App Builder assemble' as const;
export const ASSEMBLY_RECEIPT_FILENAME = 'assembly.receipt.json' as const;

export const ASSEMBLY_GATE_NAMES = ['install', 'build', 'typecheck', 'browser_smoke'] as const;
export type AssemblyGateName = (typeof ASSEMBLY_GATE_NAMES)[number];

export const ASSEMBLY_GATE_STATUSES = ['pass', 'fail', 'untested', 'skipped'] as const;
export type AssemblyGateStatus = (typeof ASSEMBLY_GATE_STATUSES)[number];

export const UNRESOLVED_KINDS = [
  'missing_credential',
  'untested_behavior',
  'unsupported_capability',
  'viewer_limit',
] as const;
export type UnresolvedKind = (typeof UNRESOLVED_KINDS)[number];

const SOURCE_HASH = /^[a-f0-9]{64}$/;

const NAMED_UNSUPPORTED = [
  { id: 'n8n', label: 'n8n', pattern: /\bn8n\b/i },
  { id: 'make', label: 'Make.com', pattern: /\bMake(?:\.com)?\b/ },
  { id: 'retell', label: 'Retell AI', pattern: /\bretell\b/i },
  { id: 'voiceflow', label: 'Voiceflow', pattern: /\bvoiceflow\b/i },
  { id: 'shopify', label: 'Shopify', pattern: /\bshopify\b/i },
  { id: 'telegram', label: 'Telegram', pattern: /\btelegram\b/i },
  { id: 'apify', label: 'Apify', pattern: /\bapify\b/i },
  { id: 'stripe', label: 'Stripe', pattern: /\bstripe\b/i },
  { id: 'twilio', label: 'Twilio', pattern: /\btwilio\b/i },
] as const;

export type AssemblyFileEntry = {
  path: string;
  sha256: string;
  bytes: number;
};

export type AssemblyDependency = {
  name: string;
  pinned: string;
  resolved: string | null;
};

export type AssemblyConfigRequirement = {
  key: string;
  required: boolean;
  present: boolean;
  note: string;
};

export type UnresolvedRequirement = {
  id: string;
  kind: UnresolvedKind;
  title: string;
  detail: string;
};

export type AssemblyGateResult = {
  name: AssemblyGateName;
  command: string;
  status: AssemblyGateStatus;
  exitCode: number | null;
  durationMs: number | null;
  note: string;
};

export type AssemblyClaims = {
  recreates_demonstrated_app: false;
  live_deploy_url: false;
  gate_studio_deploy: false;
  credentials_embedded: false;
};

export type AssemblyManifest = {
  contract: typeof ASSEMBLY_CONTRACT;
  cut: typeof ASSEMBLY_CUT;
  videoId: string;
  sourceUrl: string;
  sourceHash: string;
  packId: string;
  files: AssemblyFileEntry[];
  filesDigest: string;
  identityDigest: string;
  dependencies: AssemblyDependency[];
  configRequirements: AssemblyConfigRequirement[];
  unresolved: UnresolvedRequirement[];
  claims: AssemblyClaims;
};

export type AssemblyReceipt = AssemblyManifest & {
  gates: AssemblyGateResult[];
  workspaceDir: string | null;
  assembledAt: string | null;
};

export type AssembleOptions = {
  workspaceDir?: string;
  runGates?: boolean;
};

const CLAIMS: AssemblyClaims = {
  recreates_demonstrated_app: false,
  live_deploy_url: false,
  gate_studio_deploy: false,
  credentials_embedded: false,
};

const GATE_COMMAND: Record<AssemblyGateName, string> = {
  install: 'npm install --ignore-scripts --no-fund --no-audit',
  build: 'npm run build',
  typecheck: 'npm run typecheck',
  browser_smoke: 'node scripts/browser-smoke.mjs',
};

function sha256Text(text: string): string {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

function excerpt(text: string, max = 240): string {
  const trimmed = text.replace(/\s+/g, ' ').trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max).trimEnd()}…`;
}

function hashFiles(files: Record<string, string>): AssemblyFileEntry[] {
  return Object.keys(files)
    .toSorted((a, b) => a.localeCompare(b))
    .map((path) => ({
      path,
      sha256: sha256Text(files[path] ?? ''),
      bytes: Buffer.byteLength(files[path] ?? '', 'utf8'),
    }));
}

function digestFileList(files: AssemblyFileEntry[]): string {
  const rows = files.map((file) => `${file.path}:${file.sha256}:${file.bytes}`).join('\n');
  return sha256Text(rows);
}

function pinnedDependencies(resolved: Record<string, string | null> = {}): AssemblyDependency[] {
  return (Object.keys(APP_BUILDER_PINNED_DEPS) as Array<keyof typeof APP_BUILDER_PINNED_DEPS>)
    .toSorted((a, b) => a.localeCompare(b))
    .map((name) => ({
      name,
      pinned: APP_BUILDER_PINNED_DEPS[name],
      resolved: resolved[name] ?? null,
    }));
}

function sliceText(ingredients: AppBuilderSandboxIngredients): string {
  const transcript = ingredients.transcript.full_text ?? '';
  const segments = (ingredients.transcript.segments ?? []).map((segment) => segment.text).join('\n');
  const visual = ingredients.visualEvents
    .map((event) => `${event.element_type ?? ''} ${event.content}`)
    .join('\n');
  const sop = ingredients.sopSteps.map((step) => `${step.title}\n${step.description}`).join('\n');
  return `${transcript}\n${segments}\n${visual}\n${sop}`;
}

function namedUnsupported(ingredients: AppBuilderSandboxIngredients): UnresolvedRequirement[] {
  const text = sliceText(ingredients);
  return NAMED_UNSUPPORTED.flatMap((entry) => {
    if (!entry.pattern.test(text)) return [];
    return [
      {
        id: `unsupported:${entry.id}`,
        kind: 'unsupported_capability' as const,
        title: `${entry.label} is not implemented`,
        detail: `The pack names ${entry.label}. This assembly does not implement that integration, embed credentials for it, or mark it as working.`,
      },
    ];
  });
}

function unresolvedRequirements(
  ingredients: AppBuilderSandboxIngredients,
  smokeStatus: AssemblyGateStatus,
): UnresolvedRequirement[] {
  const named = namedUnsupported(ingredients);
  const rows: UnresolvedRequirement[] = [
    {
      id: 'viewer-not-recreation',
      kind: 'viewer_limit',
      title: 'Pack viewer is not the demonstrated application',
      detail:
        'Assembled UI shows transcript, visual events, and a source-grounded SOP checklist. That is not recreation, install, or deploy of the app shown in the video.',
    },
    {
      id: 'architecture-stripped',
      kind: 'unsupported_capability',
      title: 'Pack architecture and code snippets are stripped',
      detail:
        'architecture / code_snippets / invented types stay out of App Builder files. They are not implemented features.',
    },
    {
      id: 'no-live-deploy',
      kind: 'unsupported_capability',
      title: 'No live deploy URL',
      detail: 'This cut does not produce or verify a public https hostname.',
    },
    {
      id: 'gate-parked',
      kind: 'unsupported_capability',
      title: 'G.A.T.E. studio.deploy stays parked',
      detail: 'Assembly is not a studio.deploy PASS and does not evaluate live-URL evidence.',
    },
  ];

  if (ingredients.sopSteps.length > 0) {
    rows.push({
      id: 'sop-checklist-local-only',
      kind: 'untested_behavior',
      title: 'SOP checklist is local-only',
      detail:
        'Checkbox state is stored in localStorage keyed by video id + source_hash. It is not evidence the procedure was performed.',
    });
  }

  if (smokeStatus === 'untested' || smokeStatus === 'skipped') {
    rows.push({
      id: 'browser-smoke-untested',
      kind: 'untested_behavior',
      title: '8080 browser smoke is untested',
      detail:
        'scripts/browser-smoke.mjs is shipped. It is not marked pass until a live 0.0.0.0:8080 preview is probed.',
    });
  }

  if (named.length === 0) {
    rows.push({
      id: 'no-external-credentials',
      kind: 'missing_credential',
      title: 'No external credentials required for this viewer',
      detail:
        'The pack-viewer + SOP checklist needs no API keys. Missing provider credentials remain unresolved if a later cut claims those integrations.',
    });
  } else {
    rows.push({
      id: 'missing-provider-credentials',
      kind: 'missing_credential',
      title: 'Provider credentials are missing',
      detail: `Named integrations (${named.map((row) => row.title.replace(/ is not implemented$/, '')).join(', ')}) are unsupported here; their credentials are not present and are not embedded in generated source.`,
    });
    rows.push(...named);
  }

  return rows.toSorted((a, b) => a.id.localeCompare(b.id));
}

function configRequirements(): AssemblyConfigRequirement[] {
  return [
    {
      key: 'NODE_VERSION',
      required: true,
      present: typeof process.versions?.node === 'string',
      note: 'Node.js >= 22 to install pinned typescript + vite and run gates.',
    },
    {
      key: 'NPM_NETWORK',
      required: true,
      present: false,
      note: 'npm install needs registry access. Secrets stay out of generated source.',
    },
    {
      key: 'SMOKE_URL',
      required: false,
      present: false,
      note: 'Optional. Defaults to http://127.0.0.1:8080/ when browser smoke is run.',
    },
    {
      key: 'AI_GATEWAY_API_KEY',
      required: false,
      present: false,
      note: 'Not required for this viewer assembly. Do not embed keys in generated files.',
    },
  ];
}

function identityDigest(manifest: Omit<AssemblyManifest, 'identityDigest'>): string {
  return sha256Text(
    JSON.stringify({
      contract: manifest.contract,
      cut: manifest.cut,
      videoId: manifest.videoId,
      sourceUrl: manifest.sourceUrl,
      sourceHash: manifest.sourceHash,
      packId: manifest.packId,
      filesDigest: manifest.filesDigest,
      dependencies: manifest.dependencies.map((dep) => ({ name: dep.name, pinned: dep.pinned })),
      unresolvedIds: manifest.unresolved.map((row) => row.id),
      claims: manifest.claims,
    }),
  );
}

function untestedGates(): AssemblyGateResult[] {
  return ASSEMBLY_GATE_NAMES.map((name) => ({
    name,
    command: GATE_COMMAND[name],
    status: name === 'browser_smoke' ? ('untested' as const) : ('untested' as const),
    exitCode: null,
    durationMs: null,
    note:
      name === 'browser_smoke'
        ? 'Preview smoke is not run by HTTP assemble or default gates.'
        : 'HTTP assemble does not run npm. Use the local assemble script or the Vitest gates test.',
  }));
}

function assertSandboxIdentity(sandbox: AppBuilderSandbox): void {
  if (!sandbox.videoId.trim()) {
    throw new Error('Assembly failed: video_id is required.');
  }
  if (!sandbox.sourceUrl.trim().startsWith('http')) {
    throw new Error('Assembly failed: source_url is required.');
  }
  if (!SOURCE_HASH.test(sandbox.sourceHash.trim())) {
    throw new Error('Assembly failed: source_hash is required.');
  }
}

export function planAssembly(sandbox: AppBuilderSandbox): AssemblyReceipt {
  assertSandboxIdentity(sandbox);
  const files = hashFiles(sandbox.files);
  const filesDigest = digestFileList(files);
  const ingredients = sandbox.ingredients;
  const unresolved = unresolvedRequirements(ingredients, 'untested');
  const base: Omit<AssemblyManifest, 'identityDigest'> = {
    contract: ASSEMBLY_CONTRACT,
    cut: ASSEMBLY_CUT,
    videoId: sandbox.videoId,
    sourceUrl: sandbox.sourceUrl,
    sourceHash: sandbox.sourceHash,
    packId: sandbox.packId,
    files,
    filesDigest,
    dependencies: pinnedDependencies(),
    configRequirements: configRequirements(),
    unresolved,
    claims: CLAIMS,
  };
  return {
    ...base,
    identityDigest: identityDigest(base),
    gates: untestedGates(),
    workspaceDir: null,
    assembledAt: null,
  };
}

export function materializeAssembly(sandbox: AppBuilderSandbox, workspaceDir: string): void {
  for (const [rel, content] of Object.entries(sandbox.files)) {
    const full = join(workspaceDir, rel);
    mkdirSync(dirname(full), { recursive: true });
    writeFileSync(full, content, { encoding: 'utf8', mode: rel === 'startup.sh' ? 0o755 : 0o644 });
  }
}

function readResolvedVersion(workspaceDir: string, name: string): string | null {
  const pkgPath = join(workspaceDir, 'node_modules', name, 'package.json');
  if (!existsSync(pkgPath)) return null;
  try {
    const parsed: unknown = JSON.parse(readFileSync(pkgPath, 'utf8'));
    if (parsed === null || typeof parsed !== 'object') return null;
    const version = (parsed as { version?: unknown }).version;
    return typeof version === 'string' ? version : null;
  } catch (error) {
    console.error(`assemble: failed reading ${name} package.json`, error);
    return null;
  }
}

type CommandResult = {
  exitCode: number;
  stdout: string;
  stderr: string;
  durationMs: number;
};

async function runCommand(cwd: string, command: string, args: string[]): Promise<CommandResult> {
  const started = Date.now();
  try {
    const { stdout, stderr } = await execFileAsync(command, args, {
      cwd,
      timeout: 180_000,
      maxBuffer: 2 * 1024 * 1024,
      env: {
        ...process.env,
        npm_config_fund: 'false',
        npm_config_audit: 'false',
      },
    });
    return { exitCode: 0, stdout, stderr, durationMs: Date.now() - started };
  } catch (error) {
    const durationMs = Date.now() - started;
    if (error && typeof error === 'object') {
      const err = error as {
        status?: number | null;
        code?: string | number;
        stdout?: string;
        stderr?: string;
        message?: string;
      };
      const exitCode =
        typeof err.status === 'number' && err.status !== 0
          ? err.status
          : typeof err.code === 'number'
            ? err.code
            : 1;
      return {
        exitCode,
        stdout: typeof err.stdout === 'string' ? err.stdout : '',
        stderr: typeof err.stderr === 'string' ? err.stderr : (err.message ?? String(error)),
        durationMs,
      };
    }
    return {
      exitCode: 1,
      stdout: '',
      stderr: error instanceof Error ? error.message : String(error),
      durationMs,
    };
  }
}

function gateFromCommand(
  name: Exclude<AssemblyGateName, 'browser_smoke'>,
  result: CommandResult,
): AssemblyGateResult {
  const status: AssemblyGateStatus = result.exitCode === 0 ? 'pass' : 'fail';
  return {
    name,
    command: GATE_COMMAND[name],
    status,
    exitCode: result.exitCode,
    durationMs: result.durationMs,
    note:
      status === 'pass'
        ? 'Recorded from a real local/CI process — not an HTTP assemble.'
        : excerpt(result.stderr || result.stdout || 'command failed'),
  };
}

export async function runAssemblyGates(workspaceDir: string): Promise<{
  gates: AssemblyGateResult[];
  resolved: Record<string, string | null>;
}> {
  const installResult = await runCommand(workspaceDir, 'npm', [
    'install',
    '--ignore-scripts',
    '--no-fund',
    '--no-audit',
  ]);
  const resolved = {
    typescript: readResolvedVersion(workspaceDir, 'typescript'),
    vite: readResolvedVersion(workspaceDir, 'vite'),
  };
  const gates: AssemblyGateResult[] = [gateFromCommand('install', installResult)];
  if (installResult.exitCode !== 0) {
    gates.push({
      name: 'build',
      command: GATE_COMMAND.build,
      status: 'skipped',
      exitCode: null,
      durationMs: null,
      note: 'Skipped because npm install failed.',
    });
    gates.push({
      name: 'typecheck',
      command: GATE_COMMAND.typecheck,
      status: 'skipped',
      exitCode: null,
      durationMs: null,
      note: 'Skipped because npm install failed.',
    });
  } else {
    const buildResult = await runCommand(workspaceDir, 'npm', ['run', 'build']);
    gates.push(gateFromCommand('build', buildResult));
    const typecheckResult = await runCommand(workspaceDir, 'npm', ['run', 'typecheck']);
    gates.push(gateFromCommand('typecheck', typecheckResult));
  }
  gates.push({
    name: 'browser_smoke',
    command: GATE_COMMAND.browser_smoke,
    status: 'untested',
    exitCode: null,
    durationMs: null,
    note: 'Default assemble does not start 0.0.0.0:8080 or run browser-smoke.',
  });
  return { gates, resolved };
}

export function writeAssemblyReceipt(workspaceDir: string, receipt: AssemblyReceipt): string {
  const path = join(workspaceDir, ASSEMBLY_RECEIPT_FILENAME);
  writeFileSync(path, `${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  return path;
}

export async function assembleAppBuilder(
  input: AppBuilderSandboxInput,
  options: AssembleOptions = {},
): Promise<{ sandbox: AppBuilderSandbox; receipt: AssemblyReceipt }> {
  const sandbox = emitAppBuilderSandbox(input);
  return assembleFromSandbox(sandbox, options);
}

export async function assembleFromSandbox(
  sandbox: AppBuilderSandbox,
  options: AssembleOptions = {},
): Promise<{ sandbox: AppBuilderSandbox; receipt: AssemblyReceipt }> {
  let receipt = planAssembly(sandbox);
  const workspaceDir = options.workspaceDir;
  if (workspaceDir) {
    materializeAssembly(sandbox, workspaceDir);
    receipt = { ...receipt, workspaceDir };
  }
  if (options.runGates) {
    if (!workspaceDir) {
      throw new Error('Assembly gates require workspaceDir.');
    }
    const { gates, resolved } = await runAssemblyGates(workspaceDir);
    const smoke = gates.find((gate) => gate.name === 'browser_smoke')?.status ?? 'untested';
    const unresolved = unresolvedRequirements(sandbox.ingredients, smoke);
    const dependencies = pinnedDependencies(resolved);
    const base: Omit<AssemblyManifest, 'identityDigest'> = {
      contract: receipt.contract,
      cut: receipt.cut,
      videoId: receipt.videoId,
      sourceUrl: receipt.sourceUrl,
      sourceHash: receipt.sourceHash,
      packId: receipt.packId,
      files: receipt.files,
      filesDigest: receipt.filesDigest,
      dependencies,
      configRequirements: receipt.configRequirements,
      unresolved,
      claims: receipt.claims,
    };
    receipt = {
      ...base,
      identityDigest: identityDigest(base),
      gates,
      workspaceDir,
      assembledAt: new Date().toISOString(),
    };
    writeAssemblyReceipt(workspaceDir, receipt);
  }
  return { sandbox, receipt };
}

export function isAppBuilderSandbox(value: unknown): value is AppBuilderSandbox {
  if (value === null || typeof value !== 'object') return false;
  const row = value as AppBuilderSandbox;
  return (
    row.contract === 'app-builder-workspace' &&
    typeof row.videoId === 'string' &&
    typeof row.sourceUrl === 'string' &&
    typeof row.sourceHash === 'string' &&
    row.files !== null &&
    typeof row.files === 'object' &&
    row.ingredients !== null &&
    typeof row.ingredients === 'object'
  );
}
