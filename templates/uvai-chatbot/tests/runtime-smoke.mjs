import { spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { createServer } from 'node:net';
import { writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const listener = createServer();
await new Promise(resolve => listener.listen(0, '127.0.0.1', resolve));
const port = listener.address().port;
await new Promise(resolve => listener.close(resolve));
const server = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '-p', String(port), '-H', '127.0.0.1'], {
  env: { ...process.env, AUTH_SECRET: randomBytes(32).toString('hex'), AUTH_TRUST_HOST: 'true' }, stdio: ['ignore', 'ignore', 'pipe']
});
let serverErrors = '';
server.stderr.on('data', bytes => { serverErrors = (serverErrors + bytes.toString()).slice(-4000); });
const checks = [];
try {
  const base = `http://127.0.0.1:${port}`;
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { if ((await fetch(`${base}/ping`, { signal: AbortSignal.timeout(1000) })).status === 200) { ready = true; break; } } catch {}
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  assert.ok(ready, 'Local production server did not become ready');
  for (const [path, expectedStatus, headers] of [['/login', 200], ['/register', 200], ['/api/auth/guest', 404], ['/api/video-guide/download?id=00000000-0000-0000-0000-000000000000', 401], ['/api/chat', 401], ['/api/chat', 401, { Authorization: 'Bearer %' }], ['/api/chat', 401, { Authorization: 'Bearer %E0%A4%A' }], ['/', 307]]) {
    const response = await fetch(`${base}${path}`, { redirect: 'manual', headers, signal: AbortSignal.timeout(5000) });
    assert.equal(response.status, expectedStatus, `${path} status`);
    if (path === '/') assert.equal(new URL(response.headers.get('location'), base).pathname, '/login');
    if (path === '/login') assert.match(await response.text(), /Welcome back/);
    checks.push({ path, expectedStatus, actualStatus: response.status, malformedAuthorization: Boolean(headers), passed: true });
  }
  writeFileSync('evidence/runtime-smoke.json', JSON.stringify({ verifiedAt: new Date().toISOString(), environment: 'local production build', credentials: 'ephemeral auth test secret; no database or AI provider', checks, limitations: ['No authenticated customer journey', 'No browser or provider-quality verification', 'No database migrations or cross-tenant verification'] }, null, 2) + '\n');
  console.log(JSON.stringify({ passed: checks.length, failed: 0 }));
} finally {
  server.kill('SIGTERM');
  await new Promise(resolve => { if (server.exitCode !== null) resolve(); else { server.once('exit', resolve); setTimeout(() => { server.kill('SIGKILL'); resolve(); }, 3000).unref(); } });
}
