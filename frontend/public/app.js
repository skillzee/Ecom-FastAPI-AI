const $ = (selector) => document.querySelector(selector);
const money = (paise) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(paise / 100);
let token = '';
try { token = sessionStorage.getItem('everyday-token') || ''; } catch { /* Storage may be disabled. */ }
let user = null;
let products = [];
let cart = { items: [], total_paise: 0 };
let authMode = 'login';
let busy = false;
let authBusy = false;
let toastTimer;
let catalogLoaded = false;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function notify(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 5000);
}

function setToken(value) {
  token = value;
  try {
    if (value) sessionStorage.setItem('everyday-token', value);
    else sessionStorage.removeItem('everyday-token');
  } catch { /* Keep the session in memory if storage is unavailable. */ }
}

function signOut() {
  setToken('');
  user = null;
  cart = { items: [], total_paise: 0 };
  updateAccount();
  renderCart();
}

async function request(path, { method = 'GET', body, authenticated = false } = {}) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(authenticated && token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(20000),
  });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    if (response.status === 401 && authenticated) {
      signOut();
      notify('Your session has expired. Please sign in again.');
      throw new Error('Please sign in again to access your bag.');
    }
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((error) => `${error.loc?.at(-1) || 'Input'}: ${error.msg}`).join(' ')
      : data?.detail;
    throw new Error(typeof detail === 'string' ? detail : 'Something went wrong. Please try again.');
  }
  return data;
}

function errorText(error) {
  if (['TimeoutError', 'AbortError'].includes(error.name)) return 'This is taking longer than expected. Please try again.';
  if (error instanceof TypeError) return 'Unable to connect to the store. Please try again.';
  return error.message;
}

function showError(selector, message) {
  $(selector).textContent = message;
  $(selector).hidden = !message;
}

function updateAccount() {
  $('#account-button').textContent = user ? `Hi, ${user.full_name.split(' ')[0]}` : 'Sign in ↗';
  $('#account-name').textContent = user?.full_name || '';
  $('#account-email').textContent = user?.email || '';
  const quantity = cart.items.reduce((sum, item) => sum + item.quantity, 0);
  $('#cart-count').textContent = quantity;
  $('#bag-quantity').textContent = ` (${quantity})`;
}

function openAuth() {
  if ($('#cart-dialog').open) $('#cart-dialog').close();
  showError('#auth-error', '');
  $('#password').value = '';
  if (!$('#auth-dialog').open) $('#auth-dialog').showModal();
}

function setAuthMode(mode, preserveError = false) {
  authMode = mode;
  const register = mode === 'register';
  $('#name-label').hidden = !register;
  $('#full-name').required = register;
  $('#password').minLength = register ? 8 : 1;
  $('#password').autocomplete = register ? 'new-password' : 'current-password';
  $('#auth-title').textContent = register ? 'Make yourself at home.' : 'Welcome back.';
  $('#auth-description').textContent = register ? 'Create an account and start your collection.' : 'Sign in to keep your favorites together.';
  $('#auth-submit').textContent = register ? 'Create account ↗' : 'Sign in ↗';
  $('#login-tab').setAttribute('aria-pressed', String(!register));
  $('#register-tab').setAttribute('aria-pressed', String(register));
  if (!preserveError) showError('#auth-error', '');
}

function renderProducts() {
  const search = $('#search').value.trim().toLocaleLowerCase();
  const filtered = products.filter((product) => product.name.toLocaleLowerCase().includes(search) && (!$('#stock-filter').checked || product.in_stock));
  const sort = $('#sort').value;
  if (sort === 'price-low') filtered.sort((a, b) => a.price_paise - b.price_paise);
  if (sort === 'price-high') filtered.sort((a, b) => b.price_paise - a.price_paise);
  if (sort === 'name') filtered.sort((a, b) => a.name.localeCompare(b.name));
  $('#product-count').textContent = `${filtered.length} ${filtered.length === 1 ? 'find' : 'finds'}`;
  $('#product-grid').replaceChildren();
  if (catalogLoaded) {
    $('#catalog-status').hidden = filtered.length > 0;
    $('#catalog-status').textContent = products.length ? 'No matches. Try another search or switch off the stock filter.' : 'The collection is on its way. Products will appear here when they are added to the catalog.';
  }
  for (const product of filtered) {
    const card = element('article', 'product-card');
    const visual = element('div', `product-visual tone-${product.id % 4}`);
    visual.setAttribute('aria-hidden', 'true');
    visual.append(element('span', 'product-monogram', product.name.trim().slice(0, 1).toUpperCase()));
    visual.append(element('span', 'product-label', 'EVERYDAY COLLECTION'));
    const details = element('div', 'product-details');
    const status = element('span', `product-stock ${product.in_stock ? '' : 'unavailable'}`, product.in_stock ? 'Available' : 'Out of stock');
    const heading = element('div', 'product-heading');
    heading.append(element('h3', '', product.name), element('span', 'product-price', money(product.price_paise)));
    const button = element('button', 'add-button', product.in_stock ? 'Add to bag +' : 'Out of stock');
    button.disabled = !product.in_stock || busy;
    button.setAttribute('aria-label', `Add ${product.name} to bag`);
    button.addEventListener('click', () => addProduct(product, button));
    details.append(status, heading, button);
    card.append(visual, details);
    $('#product-grid').append(card);
  }
}

async function loadProducts() {
  catalogLoaded = false;
  $('#catalog-status').hidden = false;
  $('#catalog-status').textContent = 'Loading the collection…';
  try {
    products = await request('/products');
    catalogLoaded = true;
    renderProducts();
  } catch (error) {
    $('#catalog-status').replaceChildren(element('p', '', errorText(error)));
    const retry = element('button', 'secondary-button', 'Try again');
    retry.addEventListener('click', loadProducts);
    $('#catalog-status').append(retry);
  }
}

async function refreshCart() {
  cart = await request('/cart', { authenticated: true });
  updateAccount();
  renderCart();
}

async function addProduct(product, button) {
  if (!user) { openAuth(); return; }
  if (busy) return;
  busy = true;
  button.textContent = 'Adding…';
  document.querySelectorAll('.add-button').forEach((item) => { item.disabled = true; });
  try {
    await request('/cart/items', { method: 'POST', body: { product_id: product.id, quantity: 1 }, authenticated: true });
    notify(`${product.name} added to your bag.`);
    try { await refreshCart(); } catch (error) { notify(`Item added. ${errorText(error)} Open your bag to refresh it.`); }
  } catch (error) {
    notify(errorText(error));
  } finally {
    busy = false;
    renderProducts();
    renderCart();
  }
}

function renderCart() {
  const content = $('#cart-content');
  content.replaceChildren();
  $('#cart-summary').hidden = !user || !cart.items.length;
  if (!user || !cart.items.length) {
    const empty = element('div', 'bag-empty');
    empty.append(element('span', 'empty-symbol', '＋'), element('h3', '', user ? 'Room for a new favorite.' : 'Your finds belong together.'), element('p', 'muted', user ? 'Explore the collection and add something to your bag.' : 'Sign in to view your saved bag.'));
    const button = element('button', 'primary-button', user ? 'Explore the collection ↗' : 'Sign in ↗');
    button.addEventListener('click', () => {
      $('#cart-dialog').close();
      if (user) $('#collection').scrollIntoView({ behavior: 'smooth' });
      else openAuth();
    });
    empty.append(button);
    content.append(empty);
    return;
  }
  for (const item of cart.items) {
    const row = element('article', 'cart-item');
    const name = item.product?.name || 'Product no longer available';
    const visual = element('div', `cart-visual tone-${item.product_id % 4}`, item.product ? name.trim().slice(0, 1).toUpperCase() : '—');
    visual.setAttribute('aria-hidden', 'true');
    const details = element('div', 'cart-item-details');
    details.append(element('h3', '', name), element('p', 'muted', item.product ? money(item.product.price_paise) : 'Excluded from subtotal'));
    if (item.product && !item.product.in_stock) details.append(element('p', 'stock-warning', 'Currently out of stock'));
    const controls = element('div', 'quantity-controls');
    const decrease = element('button', '', '−');
    const increase = element('button', '', '+');
    decrease.setAttribute('aria-label', `Decrease quantity of ${name}`);
    increase.setAttribute('aria-label', `Increase quantity of ${name}`);
    decrease.disabled = busy || item.quantity <= 1 || !item.product?.in_stock;
    increase.disabled = busy || item.quantity >= 100 || !item.product?.in_stock;
    decrease.addEventListener('click', () => mutateCart(item.id, item.quantity - 1));
    increase.addEventListener('click', () => mutateCart(item.id, item.quantity + 1));
    const quantity = element('span', '', item.quantity);
    quantity.setAttribute('aria-label', `Quantity: ${item.quantity}`);
    controls.append(decrease, quantity, increase);
    const remove = element('button', 'remove-button', 'Remove');
    remove.disabled = busy;
    remove.setAttribute('aria-label', `Remove ${name} from bag`);
    remove.addEventListener('click', () => mutateCart(item.id));
    const actions = element('div', 'cart-item-actions');
    actions.append(controls, remove);
    details.append(actions);
    row.append(visual, details, element('strong', 'line-total', item.subtotal_paise === null ? '—' : money(item.subtotal_paise)));
    content.append(row);
  }
  $('#cart-total').textContent = money(cart.total_paise);
}

async function mutateCart(id, quantity) {
  if (busy) return;
  busy = true;
  showError('#cart-error', '');
  renderCart();
  renderProducts();
  try {
    const updated = await request(`/cart/items/${id}`, {
      method: quantity === undefined ? 'DELETE' : 'PATCH',
      body: quantity === undefined ? undefined : { quantity },
      authenticated: true,
    });
    // Reflect the successful write even if the following refresh fails.
    if (updated) {
      const item = cart.items.find((entry) => entry.id === id);
      if (item) {
        item.quantity = updated.quantity;
        item.subtotal_paise = item.product ? item.product.price_paise * updated.quantity : null;
      }
    } else cart.items = cart.items.filter((item) => item.id !== id);
    cart.total_paise = cart.items.reduce((sum, item) => sum + (item.subtotal_paise || 0), 0);
    updateAccount();
    await refreshCart();
  } catch (error) {
    showError('#cart-error', errorText(error));
  } finally {
    busy = false;
    renderCart();
    renderProducts();
  }
}

$('#auth-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (authBusy) return;
  authBusy = true;
  const mode = authMode;
  const email = $('#email').value.trim();
  const password = $('#password').value;
  $('#auth-submit').disabled = true;
  $('#login-tab').disabled = true;
  $('#register-tab').disabled = true;
  $('#auth-submit').textContent = mode === 'register' ? 'Creating account…' : 'Signing in…';
  showError('#auth-error', '');
  try {
    if (mode === 'register') {
      await request('/auth/register', { method: 'POST', body: { email, password, full_name: $('#full-name').value.trim() } });
      setAuthMode('login');
    }
    const credentials = await request('/auth/login', { method: 'POST', body: { email, password } });
    setToken(credentials.access_token);
    user = await request('/users/me', { authenticated: true });
    updateAccount();
    $('#auth-dialog').close();
    $('#auth-form').reset();
    notify(mode === 'register' ? 'Account created. Welcome to Everyday.' : `Welcome back, ${user.full_name.split(' ')[0]}.`);
    try { await refreshCart(); } catch (error) { notify(errorText(error)); }
  } catch (error) {
    if (!user) setToken('');
    showError('#auth-error', errorText(error));
  } finally {
    authBusy = false;
    $('#auth-submit').disabled = false;
    $('#login-tab').disabled = false;
    $('#register-tab').disabled = false;
    setAuthMode(authMode, true);
  }
});

$('#login-tab').addEventListener('click', () => setAuthMode('login'));
$('#register-tab').addEventListener('click', () => setAuthMode('register'));
$('#account-button').addEventListener('click', () => user ? $('#account-dialog').showModal() : openAuth());
$('#sign-out').addEventListener('click', () => { signOut(); $('#account-dialog').close(); notify('You have signed out.'); });
$('#cart-button').addEventListener('click', async () => {
  showError('#cart-error', '');
  renderCart();
  $('#cart-dialog').showModal();
  if (!user) return;
  $('#cart-content').textContent = 'Updating your bag…';
  try { await refreshCart(); } catch (error) { renderCart(); showError('#cart-error', errorText(error)); }
});
for (const selector of ['#search', '#stock-filter', '#sort']) $(selector).addEventListener('input', renderProducts);
document.querySelectorAll('[data-close]').forEach((button) => {
  button.addEventListener('click', () => document.getElementById(button.dataset.close).close());
});
document.querySelectorAll('dialog').forEach((dialog) => {
  dialog.addEventListener('click', (event) => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => { if (dialog.id === 'auth-dialog') $('#password').value = ''; });
});

async function initialize() {
  setAuthMode('login');
  await Promise.all([
    loadProducts(),
    (async () => {
      if (!token) return;
      $('#account-button').disabled = true;
      $('#cart-button').disabled = true;
      try {
        user = await request('/users/me', { authenticated: true });
        updateAccount();
        await refreshCart();
      } catch (error) { notify(errorText(error)); }
      finally { $('#account-button').disabled = false; $('#cart-button').disabled = false; }
    })(),
  ]);
}
initialize();
