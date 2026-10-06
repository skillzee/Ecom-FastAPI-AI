import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { once } from 'node:events';
import { createServer } from '../server.mjs';

async function start(server) {
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return `http://127.0.0.1:${server.address().port}`;
}

test('serves the storefront and proxies authenticated cart requests', async (t) => {
  const received = [];
  const backend = http.createServer(async (req, res) => {
    let body = '';
    for await (const chunk of req) body += chunk;
    received.push({ path: req.url, method: req.method, authorization: req.headers.authorization, body });
    if (req.method === 'DELETE') { res.writeHead(204); res.end(); return; }
    res.writeHead(req.url === '/auth/login' ? 401 : 200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(req.url === '/auth/login' ? { detail: 'Incorrect email or password' } : { items: [], total_paise: 0 }));
  });
  const target = await start(backend);
  const frontend = createServer(target);
  const base = await start(frontend);
  t.after(() => { frontend.closeAllConnections(); frontend.close(); backend.closeAllConnections(); backend.close(); });
  const page = await fetch(base);
  assert.equal(page.status, 200);
  assert.match(await page.text(), /Shopping bag/);
  assert.match(page.headers.get('content-security-policy'), /script-src 'self'/);
  for (const file of ['/app.js', '/styles.css']) assert.equal((await fetch(base + file)).status, 200);
  const cart = await fetch(base + '/api/cart', { headers: { Authorization: 'Bearer test-token' } });
  assert.deepEqual(await cart.json(), { items: [], total_paise: 0 });
  assert.equal(cart.headers.get('cache-control'), 'no-store');
  assert.equal(received[0].authorization, 'Bearer test-token');
  await fetch(base + '/api/cart/items/1', { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-token' }, body: '{"quantity":3}' });
  assert.deepEqual(received[1], { path: '/cart/items/1', method: 'PATCH', authorization: 'Bearer test-token', body: '{"quantity":3}' });
  const removed = await fetch(base + '/api/cart/items/1', { method: 'DELETE' });
  assert.equal(removed.status, 204);
  assert.equal(await removed.text(), '');
  const login = await fetch(base + '/api/auth/login', { method: 'POST', body: '{}' });
  assert.equal(login.status, 401);
  assert.deepEqual(await login.json(), { detail: 'Incorrect email or password' });
  assert.equal((await fetch(base + '/server.mjs')).status, 404);
  assert.equal((await fetch(base + '/.env')).status, 404);
  assert.equal((await fetch(base + '/api/cart', { method: 'POST', body: 'x'.repeat(65537) })).status, 413);
});

test('returns a useful error when the backend cannot be reached', async (t) => {
  const unused = http.createServer();
  const target = await start(unused);
  await new Promise((resolve) => unused.close(resolve));
  const frontend = createServer(target);
  const base = await start(frontend);
  t.after(() => { frontend.closeAllConnections(); frontend.close(); });
  const response = await fetch(base + '/api/products');
  assert.equal(response.status, 502);
  assert.match((await response.json()).detail, /backend is running/);
});
