# Everyday storefront

A responsive storefront for the existing FastAPI backend. Uses HTML, CSS,
browser JavaScript, and Node's built-in HTTP server; no dependency installation
or build step is needed. Node 22 or newer is required.

## Run locally

Start FastAPI in a separate terminal from `backend` using the backend README.
Then, from `frontend`:

```powershell
npm.cmd run dev
```

Open **http://127.0.0.1:5173**. The frontend server forwards `/api/*` to
`http://127.0.0.1:8000`, avoiding browser CORS configuration. Optional settings:

```powershell
$env:API_TARGET = "http://127.0.0.1:8000"
$env:PORT = "5173"
npm.cmd start
```

The server binds to loopback for local development. Hosting requires a process
manager/reverse proxy, HTTPS, and a reachable FastAPI backend.

## Features

- Registration, login, account details, and local sign-out.
- Real catalog data with name search, price/name sorting, and stock filtering.
- Add to bag, view totals in INR, change quantities (1–100), and remove items.
- Checkout with shipping details, a reviewed item total, and saved order history.
- Floating **Ask Everyday** chatbot with conversation context, suggested prompts,
  loading/error states, and a clear-conversation control.
- Empty, loading, unavailable-product, connection-error, and expired-session states.
- Responsive layout, accessible dialog controls, and keyboard navigation.

Access tokens are kept in this tab's `sessionStorage` (or memory when storage is
disabled). Closing the tab clears the session; logging out clears the local
token without revoking it on the backend. The backend saves the cart by user.
Account registration automatically signs the user in. The catalog has no image
field, so cards use decorative initials rather than invented product photos.
Checkout creates an order with status `pending_payment` and clears the cart.
No charge is made. Online payments, shipping/tax calculation, fulfillment, and
inventory reservation are not implemented. Order snapshots keep the reviewed
names and prices even if the catalog later changes. Open **Your account → My
orders** to view saved orders. Changed prices, quantities, or unavailable items
must be reviewed in the bag before submitting again.

The chatbot calls the backend's `/chat` endpoint and can help with catalog
questions; it cannot modify the bag, place orders, or access account details.
Chat messages and the latest 12 context messages are sent to the configured AI
provider. Conversation history stays in page memory and is cleared on reload.
Set `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` in the root `.env`,
then restart FastAPI. No provider credentials are sent to the browser. A chatbot
service error is shown in the chat panel and leaves the message ready to retry.

Product administration remains in the backend and requires authorization work
before public deployment.

## Checks

Install the development-only DOM test dependency before running tests on a
fresh checkout. The storefront itself still runs without installing packages.

```powershell
npm.cmd ci
npm.cmd run check
npm.cmd test
```

The proxy and UI tests use a temporary mock API; they do not change the store
database. UI tests cover catalog controls, safe rendering, registration, login
errors, cart changes, checkout/retries, order history, chatbot conversations and
errors, logout, and expired sessions. These DOM tests do not replace
visual checks in desktop and mobile browsers.
