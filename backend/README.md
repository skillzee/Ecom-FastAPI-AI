# Backend

Activate the project virtual environment, then run from `backend`:

```powershell
python -m pip install -r requirements.txt
python scripts/setup_auth.py
python -m uvicorn app.main:app --reload
```

The setup script generates a random JWT signing secret in the root `.env`.
It preserves an existing nonblank secret and never prints credentials.
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

## Modules

- `schemas/user.py` and `schemas/auth.py`: request and response contracts.
- `core/security.py`: password hashing, verification, and JWT signing/decoding.
- `services/users.py`: registration and credential checks against SQLite.
- `core/dependencies.py`: extract a bearer token and resolve the current user.
- `routers/auth.py` and `routers/users.py`: HTTP status codes and endpoints.
- `core/config.py`: separate cached auth and AI configuration.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use temporary in-memory SQLite databases and a separate test signing
secret. They do not change `ecommerce.db` or make model-provider requests.
