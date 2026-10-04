"""Add a generated JWT signing secret without displaying existing credentials."""

from pathlib import Path
import secrets

from dotenv import dotenv_values, set_key


def main():
    env_file = Path(__file__).resolve().parents[2] / ".env"
    existing_secret = dotenv_values(env_file).get("JWT_SECRET_KEY")
    if existing_secret and existing_secret.strip():
        if len(existing_secret.encode("utf-8")) < 32:
            raise ValueError("Existing JWT_SECRET_KEY must contain at least 32 bytes")
        print("JWT_SECRET_KEY is already configured; it was left unchanged.")
        return

    set_key(env_file, "JWT_SECRET_KEY", secrets.token_urlsafe(48))
    print("Generated JWT_SECRET_KEY in the root .env; its value was not printed.")


if __name__ == "__main__":
    main()
