import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const publicDir = fileURLToPath(new URL('./public/', import.meta.url));
const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
]);

export function createServer(apiTarget = 'http://127.0.0.1:8000') {
  const target = new URL(apiTarget);
  if (!['http:', 'https:'].includes(target.protocol)) throw new Error('API_TARGET must use HTTP or HTTPS');
  return http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'same-origin');
    if (url.pathname.startsWith('/api/')) {
      res.setHeader('Cache-Control', 'no-store');
      try {
        const chunks = [];
        let size = 0;
        for await (const chunk of req) {
          size += chunk.length;
          if (size > 65536) {
            res.writeHead(413, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ detail: 'Request is too large' }));
            return;
          }
          chunks.push(chunk);
        }
        const headers = {};
        for (const name of ['authorization', 'content-type']) {
          if (req.headers[name]) headers[name] = req.headers[name];
        }
        const endpoint = new URL(target);
        endpoint.pathname = url.pathname.slice(4);
        endpoint.search = url.search;
        const upstream = await fetch(endpoint, {
          method: req.method,
          headers,
          body: ['GET', 'HEAD'].includes(req.method) ? undefined : Buffer.concat(chunks),
          signal: AbortSignal.timeout(url.pathname === '/api/chat' ? 50000 : 15000),
          redirect: 'manual',
        });
        const responseBody = Buffer.from(await upstream.arrayBuffer());
        res.writeHead(upstream.status, {
          'Content-Type': upstream.headers.get('content-type') || 'application/json',
        });
        res.end(responseBody);
      } catch {
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ detail: 'The store is unavailable. Please check that the backend is running and try again.' }));
      }
      return;
    }
    const file = files.get(url.pathname);
    if (!file || !['GET', 'HEAD'].includes(req.method)) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }
    try {
      const contents = await readFile(resolve(publicDir, file[0]));
      res.writeHead(200, {
        'Content-Type': file[1],
        'Cache-Control': 'no-cache',
        'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
      });
      res.end(req.method === 'HEAD' ? undefined : contents);
    } catch {
      res.writeHead(500);
      res.end('Unable to load the storefront');
    }
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 5173);
  createServer(process.env.API_TARGET).listen(port, '127.0.0.1', () => {
    console.log(`Storefront: http://127.0.0.1:${port}`);
  });
}
