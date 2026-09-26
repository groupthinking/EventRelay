#!/usr/bin/env node
// Run the application over HTTP. Do not replace DNS, auth, the gate, or storage.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createHash, createHmac, randomBytes, randomUUID } from 'node:crypto';
import { lookup } from 'node:dns/promises';
import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createServer } from 'node:net';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import { encode } from 'next-auth/jwt';

const app = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(import.meta.url);
const next = require.resolve('next/dist/bin/next');
const args = process.argv.slice(2);
const output = resolve(process.env.STUDIO_PREFLIGHT_REPORT ?? resolve(app, 'test-results/studio-preflight-real.json'));
const sourceUrl = process.env.STUDIO_PREFLIGHT_SOURCE_URL ?? 'https://www.youtube.com/watch?v=auJzb1D-fag';
const previewOrigin = new URL(sourceUrl).origin;
const secret = randomBytes(48).toString('base64url');
const subject = `studio-preflight:${randomUUID()}`;
const report = { startedAt: new Date().toISOString(), sourceUrl, subject, checks: [], requests: [] };
const receiptKeys = new Set();
const sha256 = (value) => createHash('sha256').update(value).digest('hex');
const pendingKey = `er:gate:v2:pending:${sha256(subject)}`;
let credentials;

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])]));
  }
  return value;
}

async function provisionRedis() {
  // An explicit flag opts into a free, isolated database with a 72-hour expiry.
  // https://github.com/upstash/redis-js#readme
  const response = await fetch('https://upstash.com/start-redis', {
    method: 'POST', headers: { 'User-Agent': 'EventRelay-Studio-Preflight' },
    signal: AbortSignal.timeout(45_000), redirect: 'error',
  });
  assert.equal(response.status, 200, 'Temporary Redis provisioning failed');
  const text = await response.text();
  const field = (name) => {
    const match = text.match(new RegExp(`${name}[^:\\n]*:\\s*(.+)`));
    assert.ok(match, `Temporary Redis response is missing ${name}`);
    return match[1].trim().replace(/^[`*\s]+|[`*\s]+$/g, '');
  };
  const endpoint = field('Endpoint');
  const url = new URL(endpoint.startsWith('https://') ? endpoint : `https://${endpoint}`);
  assert.ok(url.hostname.endsWith('.upstash.io'), 'Unexpected temporary Redis provider');
  return { url: url.origin, token: field('Token') };
}

async function redis(command) {
  const response = await fetch(credentials.url, {
    method: 'POST', headers: { authorization: `Bearer ${credentials.token}`, 'content-type': 'application/json' },
    body: JSON.stringify(command), redirect: 'error', signal: AbortSignal.timeout(10_000),
  });
  assert.equal(response.status, 200, `Redis ${command[0]} HTTP status`);
  const payload = await response.json();
  assert.ok(!('error' in payload) && 'result' in payload, `Redis ${command[0]} failed`);
  return payload.result;
}

async function port() {
  const listener = createServer();
  listener.listen(0, '127.0.0.1');
  await once(listener, 'listening');
  const selected = listener.address().port;
  await new Promise((done) => listener.close(done));
  return selected;
}

async function withServer(mode, run) {
  const selected = await port();
  const origin = `http://127.0.0.1:${selected}`;
  // Only the dedicated integration credentials enter the server. Never inherit
  // production auth/provider secrets, NODE_OPTIONS preloads, or auth bypasses.
  const env = Object.fromEntries(['PATH', 'HOME', 'TMPDIR', 'SystemRoot'].filter((key) => process.env[key]).map((key) => [key, process.env[key]]));
  Object.assign(env, {
    NODE_ENV: mode, NEXTAUTH_SECRET: secret, NEXTAUTH_URL: origin,
    NEXT_TELEMETRY_DISABLED: '1', UPSTASH_REDIS_REST_URL: credentials.url,
    UPSTASH_REDIS_REST_TOKEN: credentials.token, V0_BUILD_URL: previewOrigin,
  });
  const child = spawn(process.execPath, [next, mode === 'production' ? 'start' : 'dev', '--hostname', '127.0.0.1', '--port', String(selected)], {
    cwd: app, env, stdio: ['ignore', 'pipe', 'pipe'],
  });
  let logs = '';
  for (const stream of [child.stdout, child.stderr]) stream.on('data', (data) => { logs = (logs + data).slice(-40_000); });
  let launchError;
  child.on('error', (error) => { launchError = error; });
  const session = await encode({ secret, token: { sub: subject }, maxAge: 600 });
  const cookieName = mode === 'production' ? '__Secure-next-auth.session-token' : 'next-auth.session-token';
  const cookie = `${cookieName}=${session}`;
  let rateLimitReset = 0;
  async function post(body, options = {}) {
    // Respect the real production limiter instead of disabling or spoofing it.
    if (rateLimitReset > Date.now()) await delay(rateLimitReset - Date.now());
    const headers = { origin: options.origin ?? origin, 'content-type': options.contentType ?? 'application/json' };
    if (options.auth !== false) headers.cookie = options.cookie ?? cookie;
    const response = await fetch(`${origin}/api/workflows/studio-deploy`, {
      method: 'POST', headers, body: options.raw ?? JSON.stringify(body),
      redirect: 'error', signal: AbortSignal.timeout(60_000),
    });
    if (response.headers.get('x-ratelimit-remaining') === '0') {
      const reset = Number(response.headers.get('x-ratelimit-reset')) * 1000;
      assert.ok(Number.isFinite(reset) && reset > 0, 'Rate limit reset is required');
      rateLimitReset = reset + 250;
    }
    const payload = await response.json();
    report.requests.push({ mode, status: response.status, body: payload });
    assert.ok(!('runId' in payload) && !('jobId' in payload), 'Preflight must not return a newly started job');
    return { response, payload };
  }
  try {
    const deadline = Date.now() + 90_000;
    let ready = false;
    while (Date.now() < deadline && !launchError && child.exitCode === null) {
      try {
        const response = await fetch(`${origin}/api/auth/providers`, { signal: AbortSignal.timeout(3000) });
        if (response.ok) { ready = true; break; }
      } catch { /* Wait for the actual server to bind and compile. */ }
      await delay(250);
    }
    assert.ok(ready, `${mode} Next server did not become ready: ${launchError?.message ?? child.exitCode}`);
    await run({ post, cookie, cookieName });
  } finally {
    if (child.exitCode === null) {
      child.kill('SIGTERM');
      const stopped = once(child, 'exit');
      await Promise.race([stopped, delay(5000)]);
      if (child.exitCode === null) { child.kill('SIGKILL'); await stopped; }
    }
    // Provider credentials and session keys must never reach evidence artifacts.
    const redacted = [secret, credentials.token, session].reduce((text, value) => text.replaceAll(value, '[REDACTED]'), logs);
    await writeFile(resolve(dirname(output), `studio-preflight-${mode}.log`), redacted);
  }
}

async function check(name, run) {
  const started = Date.now();
  try {
    await run();
    report.checks.push({ name, status: 'passed', durationMs: Date.now() - started });
    console.log(`PASS ${name}`);
  } catch (error) {
    report.checks.push({ name, status: 'failed', error: error.message });
    console.error(`FAIL ${name}: ${error.message}`);
  }
}

async function rejected(post, body, status, expected, options) {
  const before = await redis(['ZCARD', pendingKey]);
  const { response, payload } = await post(body, options);
  assert.equal(response.status, status);
  for (const [key, value] of Object.entries(expected)) assert.equal(payload[key], value);
  assert.ok(!('gate' in payload), 'Rejected request must not reach G.A.T.E.');
  assert.equal(await redis(['ZCARD', pendingKey]), before, 'Rejected request must not retain a receipt');
}

async function retainedHold(post, body, options) {
  const before = await redis(['ZCARD', pendingKey]);
  const { response, payload } = await post(body, options);
  assert.equal(response.status, 409);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(payload.ok, false);
  assert.equal(payload.gate.decision, 'HOLD');
  assert.equal(payload.gate.reason_code, 'GATE_HOLD_MISSING_EVIDENCE');
  const { receipt } = payload.gate;
  assert.equal(receipt.version, 'eventrelay.gate-receipt.v2');
  assert.equal(receipt.retained, true, 'A runtime-unavailable HOLD is not a successful integration');
  assert.deepEqual(receipt.authority, { actor: 'signed-in', claim: subject });
  assert.equal(receipt.artifact_hash, null, 'Browser-supplied artifact claims do not authorize deployment');
  assert.equal(receipt.run_id, null);
  const { receipt_hash, signature, ...signedBody } = receipt;
  const digest = sha256(JSON.stringify(canonical(signedBody)));
  assert.equal(receipt_hash, digest);
  assert.equal(signature, createHmac('sha256', secret).update(`origin.gate-receipt.v2\n${digest}`).digest('hex'));
  const key = `er:gate:v2:receipt:${receipt.request_hash}`;
  receiptKeys.add(key);
  const stored = await redis(['GET', key]);
  assert.ok(typeof stored === 'string', 'Receipt must be independently readable from Redis');
  assert.deepEqual(JSON.parse(stored), payload.gate);
  const ttl = await redis(['TTL', key]);
  assert.ok(ttl > 0 && ttl <= 86_400, 'Non-PASS retention must be bounded');
  assert.equal(await redis(['ZCARD', pendingKey]), before + 1);
  report.checks.push({ name: 'persisted receipt evidence', status: 'passed', receiptId: receipt.id, receiptHash: receipt_hash, ttl });
}

try {
  assert.ok(args.every((arg) => arg === '--provision-redis'), 'Only --provision-redis is supported');
  await mkdir(dirname(output), { recursive: true });
  await access(resolve(app, '.next/BUILD_ID')); // No dev-only substitute for a production build.
  credentials = args.includes('--provision-redis') ? await provisionRedis() : {
    url: process.env.STUDIO_PREFLIGHT_REDIS_REST_URL,
    token: process.env.STUDIO_PREFLIGHT_REDIS_REST_TOKEN,
  };
  assert.ok(credentials.url?.startsWith('https://') && credentials.token,
    'Provide dedicated STUDIO_PREFLIGHT_REDIS_REST_URL/TOKEN or explicitly use --provision-redis');
  assert.equal(await redis(['PING']), 'PONG');
  report.dns = await lookup(new URL(sourceUrl).hostname, { all: true });
  assert.ok(report.dns.length, 'The actual public source must resolve');
  const body = { url: sourceUrl };
  const artifactHash = sha256(await readFile(resolve(app, 'src/app/api/workflows/studio-deploy/route.ts')));
  await withServer('production', async ({ post, cookieName }) => {
    await check('production requires a session', () => rejected(post, body, 401, {}, { auth: false }));
    const wrongSignature = await encode({ secret: randomBytes(48).toString('base64url'), token: { sub: subject }, maxAge: 600 });
    await check('production rejects a session signed by another issuer', () => rejected(post, body, 401, {}, { cookie: `${cookieName}=${wrongSignature}` }));
    await check('production rejects cross-origin submissions despite preview configuration', () => rejected(post, body, 403, { code: 'invalid_origin' }, { origin: previewOrigin }));
    await check('production rejects a missing source URL', () => rejected(post, {}, 400, { error: 'url (http/https string) is required' }));
    for (const [name, url] of [
      ['IPv4 loopback', 'http://127.0.0.1:3000/x'],
      ['IPv6 loopback', 'http://[::1]:8000/x'],
      ['link-local metadata', 'http://169.254.169.254/latest/meta-data/'],
      ['localhost', 'http://localhost/'],
      ['metadata hostname', 'http://metadata.google.internal/'],
    ]) {
      await check(`production rejects ${name}`, () => rejected(post, { url }, 400, { error: 'url host is not allowed' }));
    }
    await check('production rejects a non-HTTP source', () => rejected(post, { url: 'file:///etc/passwd' }, 400, { error: 'url (http/https string) is required' }));
    await check('production rejects an oversized body', () => rejected(post, { ...body, transcript: 'x'.repeat(33_000) }, 413, { code: 'request_too_large' }));
    await check('production rejects invalid JSON', () => rejected(post, null, 400, { code: 'invalid_json' }, { raw: '{' }));
    await check('production requires JSON content type', () => rejected(post, body, 415, { code: 'json_required' }, { contentType: 'text/plain' }));
    await check('production resolves the public source and retains a signed HOLD', () => retainedHold(post, body));
    await check('production ignores browser authority and artifact claims', () => retainedHold(post, { ...body, authority: { actor: 'system' }, artifactHash }));
  });
  await withServer('development', async ({ post }) => {
    await check('approved development preview requires a session', () => rejected(post, body, 401, {}, { origin: previewOrigin, auth: false }));
    await check('approved development preview retains a real signed HOLD', () => retainedHold(post, body, { origin: previewOrigin }));
  });
} catch (error) {
  report.checks.push({ name: 'real runtime prerequisites', status: 'failed', error: error.message });
  console.error(`FAIL real runtime prerequisites: ${error.message}`);
} finally {
  if (credentials?.url && credentials?.token) {
    await check('remove only this run\'s temporary receipts', async () => {
      const indexed = await redis(['ZRANGE', pendingKey, 0, -1]);
      for (const key of indexed) {
        assert.match(key, /^er:gate:v2:receipt:[a-f0-9]{64}$/);
        const stored = await redis(['GET', key]);
        if (stored !== null) {
          assert.equal(JSON.parse(stored).receipt.authority.claim, subject, 'Cleanup cannot delete another subject\'s receipt');
          receiptKeys.add(key);
        }
      }
      const keys = [...receiptKeys, pendingKey];
      await redis(['DEL', ...keys]);
      assert.equal(await redis(['EXISTS', ...keys]), 0);
    });
  }
  report.finishedAt = new Date().toISOString();
  report.passed = report.checks.length > 0 && report.checks.every(({ status }) => status === 'passed');
  await mkdir(dirname(output), { recursive: true });
  await writeFile(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(`${report.checks.filter(({ status }) => status === 'passed').length}/${report.checks.length} checks passed; evidence: ${output}`);
  if (!report.passed) process.exitCode = 1;
}
