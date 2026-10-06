# Backend

Activate the project virtual environment, then run from `backend`:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Configuration lives in the root `.env`. `core/config.py` loads it with
`load_dotenv()` and reads named values using `os.getenv()`.
There are no settings classes or setup scripts.

Your existing `JWT_SECRET_KEY` can stay as it is. For a fresh checkout, generate
a signing secret once, then paste the output into `.env` as `JWT_SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep the key private and stable so tokens remain valid across server restarts.
Restart the server after changing configuration. Missing or short signing
secrets stop startup with a configuration error.

## Registration and login

Use `http://127.0.0.1:8000/docs` to try these endpoints:

1. `POST /auth/register` with `email`, `full_name`, and `password`.
   Passwords must contain 8–128 characters and cannot be all whitespace.
   The server saves an Argon2 hash and returns only the user's public fields.
   Duplicate emails, including case variations, return `409`.
2. `POST /auth/login` with JSON containing `email` and `password`.
   The server verifies the password and returns an access token valid for
   30 minutes, with `token_type: "bearer"` and `expires_in: 1800`.
   An unknown email or incorrect password returns the same `401` response.
3. Click **Authorize** in `/docs`, paste only the `access_token` value, then
   call `GET /users/me`. It returns the signed-in user's public fields.

Clients send the token as `Authorization: Bearer <access_token>`.
The reusable `CurrentUser` dependency checks the signature, required claims,
expiration, and existence of the user in SQLite. A token stores the user ID
in `sub`; it contains no password. JWTs are signed, not encrypted.

The current feature adds access-token login and one protected endpoint.
Refresh tokens, logout/revocation, roles, and protection of product write
endpoints are future steps. Access tokens expire naturally after 30 minutes.

## Cart

All cart endpoints require a bearer access token and use the signed-in user's
ID. Clients cannot select another user's cart.

- `POST /cart/items`: add `{"product_id": 1, "quantity": 2}`. Adding the same
  product again increases its existing quantity, up to 100 per product.
- `GET /cart`: return `items` and `total_paise`. Each item includes its cart
  `id`, `product_id`, `quantity`, current `product` details, and `subtotal_paise`.
  An empty cart returns `{"items": [], "total_paise": 0}`.
- `PATCH /cart/items/{item_id}`: send `{"quantity": 3}` to replace the quantity
  with a value from 1 through 100. The ID is the cart item ID, not the product ID.
- `DELETE /cart/items/{item_id}`: remove the item and return an empty `204`.

Missing items and items belonging to another user both return `404`. Adding or
updating an out-of-stock product returns `409`; removing it is still allowed.
Prices and totals use integer paise and current catalog prices, including
out-of-stock products. Totals are estimates and do not reserve stock or prices.
If a catalog product has been deleted, its cart entry remains removable, with
`product` and `subtotal_paise` set to `null`; it is excluded from `total_paise`.
Updating that entry returns `404`.

## Modules

- `schemas/user.py` and `schemas/auth.py`: request and response contracts.
- `core/security.py`: password hashing, verification, and JWT signing/decoding.
- `services/users.py`: registration and credential checks against SQLite.
- `core/dependencies.py`: extract a bearer token and resolve the current user.
- `routers/auth.py` and `routers/users.py`: HTTP status codes and endpoints.
- `core/config.py`: environment values read using `os.getenv()` and token lifetime.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use temporary SQLite databases and a separate test signing
secret. They do not change `ecommerce.db` or make model-provider requests.

## Storefront

The local frontend is in `../frontend`. With this backend running on port 8000,
run `npm.cmd run dev` from `frontend` and open `http://127.0.0.1:5173`.
See [the frontend README](../frontend/README.md) for configuration and tests.

## Orders and checkout

Restart FastAPI after updating the backend. Startup creates the new `orders`
and `order_items` tables without modifying existing catalog or user columns.
All order endpoints require a bearer token and return only the current user's
orders. `GET /orders` returns newest first; `GET /orders/{id}` returns `404`
for missing orders and orders belonging to another user.

`POST /orders` creates an unpaid order from the current cart. Send:

```json
{
  "checkout_key": "b6480a3a-1f8c-40dd-9a5b-46a17e16f213",
  "shipping": {
    "full_name": "Sample Shopper",
    "address": "10 Sample Street",
    "city": "Pune",
    "postal_code": "411001",
    "country": "India"
  },
  "items": [{"product_id": 1, "quantity": 2, "unit_price_paise": 12550}],
  "expected_total_paise": 25100
}
```

The server computes prices from the catalog and compares the exact reviewed
items with the cart. Empty carts, changed prices/quantities, and unavailable
products return `409` without clearing the cart. Up to 200 different products
are supported per checkout. SQLite's write lock serializes concurrent checkout
transactions. Order items and shipping details are snapshotted, and saving the
order and clearing the cart commit together. Failed transactions roll back both.

Reuse the same UUID and payload after an uncertain response: it returns the
existing order rather than creating another. Reusing a key with different
details returns `409`. Successful creation/replay returns `201`. The client
retains the pending submission in page memory for safe retry; after reloading,
check My orders before starting another checkout.

Orders have status `pending_payment`. No payment, delivery, shipping/tax quote,
or stock reservation happens. Current inventory is a boolean availability flag;
quantity-based stock and payment verification belong to the payment phase.

## Shopping assistant

`POST /chat` accepts `message` (1–2000 non-whitespace characters) and optional
`history` (up to 12 entries with `role: "user" | "assistant"` and `content`,
each up to 2000 characters). It returns `{"reply": "..."}`. Existing clients
that send only `message` still work. Catalog answers use the product tool.
The assistant cannot access customer carts/orders or perform checkout actions.

Configure `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` in `.env`.
Provider failures or requests taking more than 45 seconds return a readable
`503`, without exposing provider error details. The frontend proxy allows a
longer timeout for chat. Tests mock provider calls; they do not spend API credits.
