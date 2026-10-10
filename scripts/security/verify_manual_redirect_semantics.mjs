// Node 24+; one isolated loopback request, zero public-network requests.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
let targetHits = 0;
const server = createServer((request, response) => {
  if (request.url === '/target') { targetHits++; response.end('unexpected'); return; }
  response.writeHead(302, { Location: '/target' });
  response.end();
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
try {
  const address = server.address();
  const response = await fetch('http://127.0.0.1:' + address.port + '/start', { redirect: 'manual' });
  assert.equal(response.status, 302);
  assert.equal(response.redirected, false);
  assert.equal(targetHits, 0);
  await response.body?.cancel();
  console.log(JSON.stringify({ passed: true, mode: 'manual', status: 302, targetHits, loopbackRequests: 1, publicNetworkRequests: 0, scope: 'native Fetch semantics only, not SSRF containment' }));
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
