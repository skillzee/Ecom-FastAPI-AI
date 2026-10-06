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
- Empty, loading, unavailable-product, connection-error, and expired-session states.
- Responsive layout, accessible dialog controls, and keyboard navigation.

Access tokens are kept in this tab's `sessionStorage` (or memory when storage is
disabled). Closing the tab clears the session; logging out clears the local
token without revoking it on the backend. The backend saves the cart by user.
Account registration automatically signs the user in. The catalog has no image
field, so cards use decorative initials rather than invented product photos.
Checkout, orders, and payment are not implemented. Product administration remains
in the backend and requires authorization work before public deployment.

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
errors, cart changes, logout, and expired sessions. These DOM tests do not replace
visual checks in desktop and mobile browsers.
