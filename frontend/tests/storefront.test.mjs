import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';

const html = await readFile(new URL('../public/index.html', import.meta.url), 'utf8');
const script = await readFile(new URL('../public/app.js', import.meta.url), 'utf8');

async function settled() {
  // Drain asynchronous handlers and fetch mocks; no external requests are made.
  for (let i = 0; i < 8; i++) await new Promise((resolve) => setImmediate(resolve));
}

async function storefront(t) {
  const dom = new JSDOM(html, { url: 'http://localhost:5173', runScripts: 'outside-only' });
  t.after(() => dom.window.close());
  const { window } = dom;
  const { document } = window;
  window.AbortSignal = AbortSignal;
  for (const dialog of document.querySelectorAll('dialog')) {
    dialog.showModal = () => { dialog.open = true; };
    dialog.close = () => { dialog.open = false; dialog.dispatchEvent(new window.Event('close')); };
  }
  const products = [
    { id: 1, name: 'Notebook <script>', price_paise: 12550, in_stock: true },
    { id: 2, name: 'Pen', price_paise: 105, in_stock: true },
    { id: 3, name: 'Vase', price_paise: 90000, in_stock: false },
  ];
  let items = [];
  let expires = false;
  const calls = [];
  window.fetch = async (url, options = {}) => {
    calls.push({ url, ...options });
    const method = options.method || 'GET';
    const body = options.body ? JSON.parse(options.body) : {};
    let status = 200;
    let data;
    if (expires && options.headers?.Authorization) {
      status = 401; data = { detail: 'Could not validate credentials' };
    } else if (url === '/api/products') data = products;
    else if (url === '/api/auth/register') { status = 201; data = { id: 1, email: body.email, full_name: body.full_name }; }
    else if (url === '/api/auth/login') {
      if (body.password === 'wrong-password') { status = 401; data = { detail: 'Incorrect email or password' }; }
      else data = { access_token: 'test-token', token_type: 'bearer', expires_in: 1800 };
    } else if (url === '/api/users/me') data = { id: 1, full_name: 'Sample Shopper', email: 'shopper@example.com' };
    else if (url === '/api/cart') data = { items, total_paise: items.reduce((sum, item) => sum + item.subtotal_paise, 0) };
    else if (url === '/api/cart/items' && method === 'POST') {
      const product = products.find((entry) => entry.id === body.product_id);
      const existing = items.find((entry) => entry.product_id === product.id);
      if (existing) { existing.quantity += body.quantity; existing.subtotal_paise = existing.quantity * product.price_paise; data = existing; }
      else { data = { id: product.id, product_id: product.id, quantity: body.quantity, product, subtotal_paise: product.price_paise * body.quantity }; items.push(data); }
    } else if (url.startsWith('/api/cart/items/')) {
      const id = Number(url.split('/').at(-1));
      const item = items.find((entry) => entry.id === id);
      if (method === 'DELETE') { items = items.filter((entry) => entry.id !== id); status = 204; data = null; }
      else { item.quantity = body.quantity; item.subtotal_paise = item.quantity * item.product.price_paise; data = item; }
    } else throw new Error(`Unexpected request: ${method} ${url}`);
    const snapshot = structuredClone(data);
    return { status, ok: status < 400, json: async () => snapshot };
  };
  window.eval(script);
  await settled();
  const select = (selector) => document.querySelector(selector);
  const input = (selector, value) => {
    select(selector).value = value;
    select(selector).dispatchEvent(new window.Event('input', { bubbles: true }));
  };
  const login = async (password = 'test-password-123') => {
    select('#account-button').click();
    input('#email', 'shopper@example.com');
    input('#password', password);
    select('#auth-form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    await settled();
  };
  return { window, document, select, input, login, calls, expire: () => { expires = true; } };
}

test('catalog search, stock filtering, sorting, and safe product rendering', async (t) => {
  const ui = await storefront(t);
  assert.equal(ui.document.querySelectorAll('.product-card').length, 3);
  assert.equal(ui.select('.product-heading h3').textContent, 'Notebook <script>');
  assert.equal(ui.document.querySelectorAll('.product-card script').length, 0);
  assert.equal(ui.document.querySelectorAll('.add-button')[2].disabled, true);
  ui.input('#search', 'pen');
  assert.equal(ui.document.querySelectorAll('.product-card').length, 1);
  ui.input('#search', 'missing');
  assert.match(ui.select('#catalog-status').textContent, /No matches/);
  ui.input('#search', '');
  ui.select('#stock-filter').checked = true;
  ui.select('#stock-filter').dispatchEvent(new ui.window.Event('input'));
  assert.equal(ui.document.querySelectorAll('.product-card').length, 2);
  ui.input('#sort', 'price-low');
  assert.equal(ui.select('.product-heading h3').textContent, 'Pen');
});

test('sign-in errors stay visible and unauthenticated add opens account form', async (t) => {
  const ui = await storefront(t);
  ui.select('.add-button').click();
  assert.equal(ui.select('#auth-dialog').open, true);
  assert.equal(ui.calls.some((call) => call.url === '/api/cart/items'), false);
  await ui.login('wrong-password');
  assert.equal(ui.select('#auth-error').hidden, false);
  assert.equal(ui.select('#auth-error').textContent, 'Incorrect email or password');
  assert.equal(ui.select('#auth-submit').disabled, false);
  assert.equal(ui.select('#auth-dialog').open, true);
});

test('login, add, update, remove, and logout flow', async (t) => {
  const ui = await storefront(t);
  await ui.login();
  assert.equal(ui.select('#auth-dialog').open, false);
  assert.match(ui.select('#account-button').textContent, /Sample/);
  assert.equal(ui.window.sessionStorage.getItem('everyday-token'), 'test-token');
  ui.select('.add-button').click();
  await settled();
  assert.equal(ui.select('#cart-count').textContent, '1');
  ui.select('#cart-button').click();
  await settled();
  assert.equal(ui.select('#cart-dialog').open, true);
  assert.match(ui.select('#cart-total').textContent, /125\.50/);
  ui.select('[aria-label^="Increase quantity"]').click();
  await settled();
  assert.equal(ui.select('#cart-count').textContent, '2');
  assert.match(ui.select('#cart-total').textContent, /251\.00/);
  assert.ok(ui.calls.some((call) => call.method === 'PATCH' && JSON.parse(call.body).quantity === 2));
  ui.select('.remove-button').click();
  await settled();
  assert.equal(ui.select('#cart-count').textContent, '0');
  assert.equal(ui.select('#cart-summary').hidden, true);
  assert.match(ui.select('#cart-content').textContent, /Room for a new favorite/);
  ui.select('[data-close="cart-dialog"]').click();
  ui.select('#account-button').click();
  ui.select('#sign-out').click();
  assert.equal(ui.window.sessionStorage.getItem('everyday-token'), null);
  assert.match(ui.select('#account-button').textContent, /Sign in/);
});

test('registration signs in and an expired session clears account data', async (t) => {
  const ui = await storefront(t);
  ui.select('#account-button').click();
  ui.select('#register-tab').click();
  ui.input('#full-name', 'Sample Shopper');
  ui.input('#email', 'shopper@example.com');
  ui.input('#password', 'test-password-123');
  ui.select('#auth-form').dispatchEvent(new ui.window.Event('submit', { bubbles: true, cancelable: true }));
  await settled();
  assert.ok(ui.calls.some((call) => call.url === '/api/auth/register' && JSON.parse(call.body).full_name === 'Sample Shopper'));
  assert.equal(ui.select('#auth-dialog').open, false);
  ui.expire();
  ui.select('#cart-button').click();
  await settled();
  assert.equal(ui.window.sessionStorage.getItem('everyday-token'), null);
  assert.match(ui.select('#account-button').textContent, /Sign in/);
  assert.match(ui.select('#cart-error').textContent, /sign in again/);
});
