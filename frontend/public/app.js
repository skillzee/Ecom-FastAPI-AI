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
let checkoutDraft = null;
let checkoutSubmission = null;
let orderBusy = false;
let chatBusy = false;
let chatHistory = [];

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
  checkoutDraft = null;
  checkoutSubmission = null;
  $('#checkout-form').reset();
  $('#orders-content').replaceChildren();
  $('#checkout-review').replaceChildren();
  for (const id of ['checkout-dialog', 'orders-dialog']) if ($(`#${id}`).open) $(`#${id}`).close();
  updateAccount();
  renderCart();
}

async function request(path, { method = 'GET', body, authenticated = false, timeout = 20000 } = {}) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(authenticated && token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeout),
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
    const error = new Error(typeof detail === 'string' ? detail : 'Something went wrong. Please try again.');
    error.status = response.status;
    throw error;
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
  const sessionToken = token;
  const updated = await request('/cart', { authenticated: true });
  if (sessionToken !== token || !user) return;
  cart = updated;
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
  $('#checkout-button').disabled = busy || orderBusy || cart.items.some((item) => !item.product?.in_stock);
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
  $('#checkout-button').disabled = true;
  try { await refreshCart(); } catch (error) { renderCart(); showError('#cart-error', errorText(error)); }
});

function reviewCheckout() {
  const review = $('#checkout-review');
  review.replaceChildren();
  for (const item of checkoutDraft.items) {
    const row = element('div', 'review-row');
    row.append(element('span', '', `${item.quantity} × ${item.name}`), element('strong', '', money(item.unit_price_paise * item.quantity)));
    review.append(row);
  }
  const total = element('div', 'review-row review-total');
  total.append(element('span', '', 'Items total'), element('strong', '', money(checkoutDraft.expected_total_paise)));
  review.append(total, element('p', 'muted', 'Shipping and taxes have not been calculated. This is an unpaid order, not a final payment quote.'));
}

$('#checkout-button').addEventListener('click', async () => {
  if (busy || orderBusy || !user) return;
  showError('#cart-error', '');
  $('#checkout-button').disabled = true;
  try {
    if (!checkoutSubmission) {
      await refreshCart();
      if (!cart.items.length) throw new Error('Your bag is empty.');
      if (cart.items.some((item) => !item.product?.in_stock)) throw new Error('Remove unavailable items before checkout.');
      checkoutDraft = {
        expected_total_paise: cart.total_paise,
        items: cart.items.map((item) => ({ product_id: item.product_id, name: item.product.name, quantity: item.quantity, unit_price_paise: item.product.price_paise })),
      };
      $('#shipping-fields').disabled = false;
      $('#shipping-name').value ||= user.full_name;
      showError('#checkout-error', '');
    }
    reviewCheckout();
    $('#place-order').textContent = checkoutSubmission ? 'Retry safely' : 'Create unpaid order';
    $('#cart-dialog').close();
    $('#checkout-dialog').showModal();
  } catch (error) { showError('#cart-error', errorText(error)); }
  finally { renderCart(); }
});

$('#checkout-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (orderBusy || !checkoutDraft || !user) return;
  if (!checkoutSubmission) {
    checkoutSubmission = {
      checkout_key: crypto.randomUUID(),
      expected_total_paise: checkoutDraft.expected_total_paise,
      items: checkoutDraft.items.map(({ name, ...item }) => item),
      shipping: {
        full_name: $('#shipping-name').value.trim(), address: $('#shipping-address').value.trim(),
        city: $('#shipping-city').value.trim(), postal_code: $('#shipping-postal').value.trim(), country: $('#shipping-country').value.trim(),
      },
    };
  }
  const sessionToken = token;
  orderBusy = true;
  $('#shipping-fields').disabled = true;
  $('#place-order').disabled = true;
  $('#place-order').textContent = 'Creating your order…';
  showError('#checkout-error', '');
  try {
    const order = await request('/orders', { method: 'POST', body: checkoutSubmission, authenticated: true });
    if (token !== sessionToken || !user) return;
    checkoutSubmission = null;
    checkoutDraft = null;
    $('#checkout-form').reset();
    $('#checkout-dialog').close();
    cart = { items: [], total_paise: 0 };
    updateAccount();
    renderCart();
    notify(`Order #${order.id} saved. Payment is pending; no charge was made.`);
    await openOrders(order);
    try { await refreshCart(); } catch (error) { notify(errorText(error)); }
  } catch (error) {
    if (error.status && error.status < 500) {
      checkoutSubmission = null;
      $('#shipping-fields').disabled = false;
    }
    showError('#checkout-error', `${errorText(error)}${checkoutSubmission ? ' The result is uncertain. Retry safely with the same details, or check My orders.' : ''}`);
    if (error.status === 409) {
      checkoutDraft = null;
      $('#place-order').hidden = true;
      showError('#checkout-error', `${errorText(error)} Close checkout and reopen your bag to review it.`);
    }
  } finally {
    orderBusy = false;
    $('#place-order').disabled = false;
    $('#place-order').textContent = checkoutSubmission ? 'Retry safely' : 'Create unpaid order';
  }
});

function renderOrders(orders) {
  const content = $('#orders-content');
  content.replaceChildren();
  if (!orders.length) { content.append(element('p', 'empty-state', 'Your orders will appear here after checkout.')); return; }
  for (const order of orders) {
    const card = element('article', 'order-card');
    const heading = element('div', 'review-row');
    heading.append(element('h3', '', `Order #${order.id}`), element('strong', '', money(order.total_paise)));
    card.append(heading, element('p', 'order-status', order.status === 'pending_payment' ? 'Awaiting payment · No charge made' : order.status), element('p', 'muted', new Date(order.created_at).toLocaleString('en-IN')));
    for (const item of order.items) {
      const row = element('div', 'review-row');
      row.append(element('span', '', `${item.quantity} × ${item.name}`), element('span', '', money(item.subtotal_paise)));
      card.append(row);
    }
    card.append(element('p', 'order-address', `Ship to ${order.shipping.full_name}: ${order.shipping.address}, ${order.shipping.city}, ${order.shipping.postal_code}, ${order.shipping.country}`));
    content.append(card);
  }
}

async function openOrders(confirmedOrder = null) {
  if (!user) { openAuth(); return; }
  if ($('#account-dialog').open) $('#account-dialog').close();
  if (!$('#orders-dialog').open) $('#orders-dialog').showModal();
  showError('#orders-error', '');
  if (confirmedOrder) renderOrders([confirmedOrder]);
  else $('#orders-content').textContent = 'Loading your orders…';
  $('#orders-refresh').disabled = true;
  const sessionToken = token;
  try {
    const orders = await request('/orders', { authenticated: true });
    if (token === sessionToken && user) renderOrders(orders);
  } catch (error) {
    if (!confirmedOrder) $('#orders-content').replaceChildren();
    showError('#orders-error', errorText(error));
  } finally { $('#orders-refresh').disabled = false; }
}
$('#orders-button').addEventListener('click', () => openOrders());
$('#orders-refresh').addEventListener('click', () => openOrders());
$('#checkout-dialog').addEventListener('close', () => { $('#place-order').hidden = false; });

function appendChat(role, content) {
  $('#chat-messages').append(element('p', `chat-bubble ${role}`, content));
  $('#chat-messages').scrollTop = $('#chat-messages').scrollHeight;
}

async function sendChat(message) {
  if (chatBusy || !message.trim()) return;
  chatBusy = true;
  const history = chatHistory.slice(-12);
  $('#chat-send').disabled = true;
  $('#chat-clear').disabled = true;
  document.querySelectorAll('[data-prompt]').forEach((button) => { button.disabled = true; });
  showError('#chat-error', '');
  appendChat('user', message);
  const thinking = element('p', 'chat-bubble assistant thinking', 'Looking through the collection…');
  $('#chat-messages').append(thinking);
  $('#chat-messages').setAttribute('aria-busy', 'true');
  try {
    const response = await request('/chat', { method: 'POST', body: { message, history }, timeout: 60000 });
    thinking.remove();
    appendChat('assistant', response.reply);
    chatHistory.push({ role: 'user', content: message }, { role: 'assistant', content: response.reply.slice(0, 2000) });
    chatHistory = chatHistory.slice(-12);
    if ($('#chat-input').value.trim() === message) $('#chat-input').value = '';
  } catch (error) {
    thinking.remove();
    showError('#chat-error', errorText(error));
    $('#chat-input').value = message;
  } finally {
    chatBusy = false;
    $('#chat-messages').setAttribute('aria-busy', 'false');
    $('#chat-send').disabled = false;
    $('#chat-clear').disabled = false;
    document.querySelectorAll('[data-prompt]').forEach((button) => { button.disabled = false; });
    if ($('#chat-dialog').open) $('#chat-input').focus();
  }
}
$('#chat-launcher').addEventListener('click', () => { $('#chat-dialog').showModal(); $('#chat-input').focus(); });
$('#chat-form').addEventListener('submit', (event) => { event.preventDefault(); sendChat($('#chat-input').value.trim()); });
$('#chat-input').addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); sendChat($('#chat-input').value.trim()); }
});
document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => { $('#chat-input').value = button.dataset.prompt; sendChat(button.dataset.prompt); }));
$('#chat-clear').addEventListener('click', () => {
  chatHistory = [];
  $('#chat-messages').replaceChildren(element('p', 'chat-bubble assistant', 'A fresh start. What would you like to find?'));
  $('#chat-input').value = '';
  showError('#chat-error', '');
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
