#!/usr/bin/env node
// Real Redis + SRH, the HTTP transport recommended by Upstash for integration
// testing: https://upstash.com/docs/redis/sdks/ts/developing
import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { access, mkdtemp, readFile, rm } from 'node:fs/promises';
import http from 'node:http';
import https from 'node:https';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';

const app = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// Immutable provider images; no shared database, host volume, or Docker socket
// is exposed to either container. Only SRH's HTTP port is published on loopback.
const redisImage = 'redis:8.10.2-alpine@sha256:3811787313eba226a2ef38658c6ccb91cd5e110edc89c37767de373120a0e5a0';
const srhImage = 'hiett/serverless-redis-http:0.0.10@sha256:65128347949bca511e448fd7238780d624573d74c22b79155a7563db19e9b678';
const name = `studio-preflight-${randomUUID()}`;
const token = randomBytes(48).toString('base64url');
const containers = [];
let directory;
let networkCreated = false;
let transport;

function command(binary, args, env = process.env) {
  const result = spawnSync(binary, args, { encoding: 'utf8', env, timeout: 180_000 });
  assert.equal(result.status, 0, `${binary} failed: ${(result.error?.message ?? result.stderr ?? '').replaceAll(token, '[REDACTED]')}`);
  return result.stdout.trim();
}

try {
  await access(resolve(app, '.next/BUILD_ID'));
  command('docker', ['info', '--format', '{{.ServerVersion}}']);
  directory = await mkdtemp(join(tmpdir(), 'studio-preflight-'));
  const keyPath = join(directory, 'localhost.key');
  const certPath = join(directory, 'localhost.crt');
  command('openssl', [
    'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-sha256', '-days', '1',
    '-keyout', keyPath, '-out', certPath, '-subj', '/CN=localhost',
    '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1',
    '-addext', 'basicConstraints=critical,CA:TRUE',
  ]);
  command('docker', ['network', 'create', name]);
  networkCreated = true;
  const redisName = `${name}-redis`;
  command('docker', ['run', '--rm', '--detach', '--name', redisName, '--network', name, '--network-alias', 'redis', redisImage]);
  containers.push(redisName);
  const srhName = `${name}-http`;
  command('docker', [
    'run', '--rm', '--detach', '--name', srhName, '--network', name,
    '--publish', '127.0.0.1::80', '--env', 'SRH_MODE=env', '--env', 'SRH_TOKEN',
    '--env', 'SRH_CONNECTION_STRING=redis://redis:6379', srhImage,
  ], { ...process.env, SRH_TOKEN: token });
  containers.push(srhName);
  const published = command('docker', ['port', srhName, '80/tcp']);
  assert.match(published, /^127\.0\.0\.1:\d+$/);
  const srhPort = Number(published.split(':')[1]);
  const deadline = Date.now() + 30_000;
  let ready = false;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://${published}`, {
        method: 'POST', headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
        body: JSON.stringify(['PING']), signal: AbortSignal.timeout(1000),
      });
      if (response.ok && (await response.json()).result === 'PONG') { ready = true; break; }
    } catch { /* Wait for real service startup, never substitute an answer. */ }
    await delay(250);
  }
  assert.ok(ready, 'The real Redis/SRH service did not become ready');
  assert.equal(command('docker', ['exec', redisName, 'redis-cli', 'PING']), 'PONG');

  // Preserve the production store's HTTPS requirement. TLS terminates here;
  // request and response bytes pass unchanged to the real SRH/Redis service.
  transport = https.createServer({ key: await readFile(keyPath), cert: await readFile(certPath) }, (request, response) => {
    const upstream = http.request({
      hostname: '127.0.0.1', port: srhPort, method: request.method, path: request.url,
      headers: { ...request.headers, host: published },
    }, (reply) => {
      response.writeHead(reply.statusCode, reply.headers);
      reply.pipe(response);
    });
    upstream.on('error', () => {
      if (!response.headersSent) response.writeHead(502);
      response.end();
    });
    request.pipe(upstream);
  });
  transport.listen(0, '127.0.0.1');
  await once(transport, 'listening');
  const url = `https://localhost:${transport.address().port}`;
  const childEnv = { ...process.env };
  delete childEnv.NODE_OPTIONS;
  delete childEnv.NODE_TLS_REJECT_UNAUTHORIZED;
  console.log(`Real Redis ready: ${redisImage}; HTTP transport: ${srhImage}; TLS verification enabled`);
  const child = spawn(process.execPath, [resolve(app, 'scripts/verify-studio-preflight.mjs')], {
    cwd: app, stdio: 'inherit',
    env: {
      ...childEnv, STUDIO_PREFLIGHT_REDIS_REST_URL: url,
      STUDIO_PREFLIGHT_REDIS_REST_TOKEN: token,
      // Add only this ephemeral CA to the verifier and Next processes. TLS
      // certificate and hostname verification remain enabled.
      NODE_EXTRA_CA_CERTS: certPath,
    },
  });
  const [code] = await once(child, 'exit');
  assert.equal(code, 0, 'Real Studio preflight verification failed');
} catch (error) {
  console.error(error.message.replaceAll(token, '[REDACTED]'));
  process.exitCode = 1;
} finally {
  if (transport) {
    transport.closeAllConnections();
    await new Promise((done) => transport.close(done));
  }
  for (const container of containers.reverse()) {
    try { command('docker', ['rm', '--force', container]); }
    catch (error) { console.error(error.message); process.exitCode = 1; }
  }
  if (networkCreated) {
    try { command('docker', ['network', 'rm', name]); }
    catch (error) { console.error(error.message); process.exitCode = 1; }
  }
  if (directory) await rm(directory, { recursive: true, force: true });
}
