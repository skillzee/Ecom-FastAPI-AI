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

Tests use temporary in-memory SQLite databases and a separate test signing
secret. They do not change `ecommerce.db` or make model-provider requests.
