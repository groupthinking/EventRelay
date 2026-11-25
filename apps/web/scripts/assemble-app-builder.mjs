#!/usr/bin/env node
/**
 * Local assemble step: write App Builder sandbox files, run
 * npm install + npm run build + npm run typecheck, write assembly.receipt.json.
 *
 * HTTP /api/video/assemble never runs these gates (labeled untested there).
 *
 * Usage:
 *   node apps/web/scripts/assemble-app-builder.mjs --from-sandbox sandbox.json --out /tmp/uvai-assemble-qj
 *
 * sandbox.json may be the full { status, data } envelope or the sandbox data object.
 */
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

const RECEIPT_NAME = 'assembly.receipt.json';

function fail(message) {
  console.error(message);
  process.exit(1);
}

function argValue(flag) {
  const index = process.argv.indexOf(flag);
  if (index === -1) return null;
  return process.argv[index + 1] ?? null;
}

function sha256Text(text) {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

function loadSandbox(path) {
  const parsed = JSON.parse(readFileSync(path, 'utf8'));
  if (parsed && typeof parsed === 'object' && parsed.data && parsed.data.files) {
    return parsed.data;
  }
  if (parsed && typeof parsed === 'object' && parsed.files) {
    return parsed;
  }
  fail('sandbox JSON must be a sandbox object or { status, data } envelope with data.files');
}

function writeFiles(dir, files) {
  for (const [rel, content] of Object.entries(files)) {
    if (typeof content !== 'string') continue;
    const full = join(dir, rel);
    mkdirSync(dirname(full), { recursive: true });
    writeFileSync(full, content, { encoding: 'utf8', mode: rel === 'startup.sh' ? 0o755 : 0o644 });
  }
}

function run(cwd, command, args) {
  const started = Date.now();
  const result = spawnSync(command, args, {
    cwd,
    encoding: 'utf8',
    timeout: 180_000,
    env: { ...process.env, npm_config_fund: 'false', npm_config_audit: 'false' },
  });
  return {
    exitCode: result.status ?? 1,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? (result.error ? result.error.message : ''),
    durationMs: Date.now() - started,
  };
}

function excerpt(text, max = 240) {
  const trimmed = String(text).replace(/\s+/g, ' ').trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max).trimEnd()}…`;
}

const sandboxPath = argValue('--from-sandbox');
const outDir = argValue('--out');
if (!sandboxPath || !outDir) {
  fail('Usage: node assemble-app-builder.mjs --from-sandbox <sandbox.json> --out <dir>');
}

const sandbox = loadSandbox(resolve(sandboxPath));
if (!sandbox.videoId || !sandbox.sourceHash || !sandbox.files) {
  fail('sandbox JSON is missing videoId, sourceHash, or files');
}

const workspaceDir = resolve(outDir);
mkdirSync(workspaceDir, { recursive: true });
writeFiles(workspaceDir, sandbox.files);

const files = Object.keys(sandbox.files)
  .toSorted((a, b) => a.localeCompare(b))
  .map((path) => ({
    path,
    sha256: sha256Text(sandbox.files[path]),
    bytes: Buffer.byteLength(sandbox.files[path], 'utf8'),
  }));
const filesDigest = sha256Text(files.map((file) => `${file.path}:${file.sha256}:${file.bytes}`).join('\n'));

const install = run(workspaceDir, 'npm', ['install', '--ignore-scripts', '--no-fund', '--no-audit']);
const build =
  install.exitCode === 0
    ? run(workspaceDir, 'npm', ['run', 'build'])
    : { exitCode: null, stdout: '', stderr: 'Skipped because npm install failed.', durationMs: 0 };
const typecheck =
  install.exitCode === 0
    ? run(workspaceDir, 'npm', ['run', 'typecheck'])
    : { exitCode: null, stdout: '', stderr: 'Skipped because npm install failed.', durationMs: 0 };

function gate(name, command, result) {
  if (result.exitCode === null) {
    return {
      name,
      command,
      status: 'skipped',
      exitCode: null,
      durationMs: null,
      note: excerpt(result.stderr),
    };
  }
  return {
    name,
    command,
    status: result.exitCode === 0 ? 'pass' : 'fail',
    exitCode: result.exitCode,
    durationMs: result.durationMs,
    note: result.exitCode === 0 ? 'Recorded from assemble-app-builder.mjs' : excerpt(result.stderr || result.stdout),
  };
}

const receipt = {
  contract: 'app-builder-assembly',
  cut: 'pack→App Builder assemble',
  videoId: sandbox.videoId,
  sourceUrl: sandbox.sourceUrl,
  sourceHash: sandbox.sourceHash,
  packId: sandbox.packId ?? `vp:v0:${sandbox.videoId}`,
  files,
  filesDigest,
  identityDigest: sandbox.assembly?.identityDigest ?? null,
  dependencies: sandbox.assembly?.dependencies ?? [],
  configRequirements: sandbox.assembly?.configRequirements ?? [],
  unresolved: sandbox.assembly?.unresolved ?? [],
  claims: sandbox.assembly?.claims ?? {
    recreates_demonstrated_app: false,
    live_deploy_url: false,
    gate_studio_deploy: false,
    credentials_embedded: false,
  },
  gates: [
    gate('install', 'npm install --ignore-scripts --no-fund --no-audit', install),
    gate('build', 'npm run build', build),
    gate('typecheck', 'npm run typecheck', typecheck),
    {
      name: 'browser_smoke',
      command: 'node scripts/browser-smoke.mjs',
      status: 'untested',
      exitCode: null,
      durationMs: null,
      note: 'Default assemble does not start 0.0.0.0:8080 or run browser-smoke.',
    },
  ],
  workspaceDir,
  assembledAt: new Date().toISOString(),
};

if (existsSync(join(workspaceDir, 'node_modules/typescript/package.json'))) {
  const ts = JSON.parse(readFileSync(join(workspaceDir, 'node_modules/typescript/package.json'), 'utf8'));
  const vite = JSON.parse(readFileSync(join(workspaceDir, 'node_modules/vite/package.json'), 'utf8'));
  receipt.dependencies = [
    { name: 'typescript', pinned: '5.7.3', resolved: ts.version ?? null },
    { name: 'vite', pinned: '6.4.3', resolved: vite.version ?? null },
  ];
}

writeFileSync(join(workspaceDir, RECEIPT_NAME), `${JSON.stringify(receipt, null, 2)}\n`);
console.log(JSON.stringify({ ok: receipt.gates.every((g) => g.name === 'browser_smoke' || g.status === 'pass'), receiptPath: join(workspaceDir, RECEIPT_NAME), videoId: receipt.videoId, sourceHash: receipt.sourceHash, filesDigest: receipt.filesDigest, gates: receipt.gates.map((g) => ({ name: g.name, status: g.status, exitCode: g.exitCode })) }, null, 2));

if (install.exitCode !== 0 || build.exitCode !== 0 || typecheck.exitCode !== 0) {
  process.exit(1);
}
