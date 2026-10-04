from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import jwt
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.models.user import User


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.secret = "test-only-secret-key-" + "x" * 48
        self.secret_patch = patch("app.core.config.JWT_SECRET_KEY", self.secret)
        self.secret_patch.start()
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        def override_session():
            with Session(self.engine) as session:
                yield session

        self.startup_patch = patch(
            "app.main.create_db_and_tables",
            side_effect=lambda: SQLModel.metadata.create_all(self.engine),
        )
        self.startup_patch.start()
        app.dependency_overrides[get_session] = override_session
        self.client = TestClient(app)
        self.client.__enter__()
        self.payload = {
            "email": "shopper@example.com",
            "full_name": "Sample Shopper",
            "password": "example-password-123",
        }
        self.user_id = self.client.post("/auth/register", json=self.payload).json()["id"]

    def tearDown(self):
        self.client.__exit__(None, None, None)
        app.dependency_overrides.pop(get_session, None)
        self.startup_patch.stop()
        self.secret_patch.stop()
        self.engine.dispose()

    def login(self):
        return self.client.post(
            "/auth/login",
            json={"email": "SHOPPER@EXAMPLE.COM", "password": self.payload["password"]},
        )

    def test_login_and_authenticated_profile(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        token_data = response.json()
        self.assertEqual(set(token_data), {"access_token", "token_type", "expires_in"})
        self.assertEqual(token_data["token_type"], "bearer")
        self.assertEqual(token_data["expires_in"], 1800)
        claims = jwt.decode(token_data["access_token"], self.secret, algorithms=["HS256"])
        self.assertEqual(claims["sub"], str(self.user_id))
        self.assertEqual(claims["exp"] - claims["iat"], 1800)
        profile = self.client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(
            profile.json(),
            {"id": self.user_id, "email": self.payload["email"], "full_name": self.payload["full_name"]},
        )

    def test_unknown_email_and_wrong_password_have_same_error(self):
        for email, password in [
            (self.payload["email"], "wrong-password"),
            ("unknown@example.com", self.payload["password"]),
        ]:
            with self.subTest(email=email):
                response = self.client.post(
                    "/auth/login", json={"email": email, "password": password}
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Incorrect email or password"})
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_missing_and_malformed_authorization(self):
        for header in [None, "Bearer", "Basic abc", "Bearer invalid-token"]:
            with self.subTest(header=header):
                headers = {"Authorization": header} if header is not None else {}
                response = self.client.get("/users/me", headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_invalid_tokens_are_rejected(self):
        now = datetime.now(timezone.utc)
        valid_claims = {"sub": str(self.user_id), "iat": now, "exp": now + timedelta(minutes=30)}
        cases = [
            ({**valid_claims, "iat": now - timedelta(minutes=2), "exp": now - timedelta(minutes=1)}, self.secret, "HS256"),
            (valid_claims, "different-signing-key-" + "y" * 48, "HS256"),
            (valid_claims, self.secret, "HS512"),
            ({key: value for key, value in valid_claims.items() if key != "exp"}, self.secret, "HS256"),
            ({**valid_claims, "sub": "invalid-id"}, self.secret, "HS256"),
            ({**valid_claims, "sub": "9" * 30}, self.secret, "HS256"),
            ({**valid_claims, "sub": "999"}, self.secret, "HS256"),
        ]
        for claims, key, algorithm in cases:
            with self.subTest(algorithm=algorithm, subject=claims.get("sub")):
                token = jwt.encode(claims, key, algorithm=algorithm)
                response = self.client.get(
                    "/users/me", headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(response.status_code, 401)

    def test_deleted_user_token_is_rejected(self):
        token = self.login().json()["access_token"]
        with Session(self.engine) as session:
            user = session.get(User, self.user_id)
            session.delete(user)
            session.commit()
        response = self.client.get(
            "/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_login_input_is_rejected(self):
        for credentials in [
            {"email": "invalid", "password": "password"},
            {"email": self.payload["email"], "password": ""},
            {"email": self.payload["email"]},
        ]:
            with self.subTest(fields=list(credentials)):
                self.assertEqual(
                    self.client.post("/auth/login", json=credentials).status_code, 422
                )

    def test_swagger_declares_bearer_authentication(self):
        schema = self.client.get("/openapi.json").json()
        self.assertEqual(
            schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"], "bearer"
        )
        self.assertEqual(schema["paths"]["/users/me"]["get"]["security"], [{"HTTPBearer": []}])

    def test_startup_rejects_missing_or_short_signing_secret(self):
        for secret in ["", "short", " " * 40]:
            with self.subTest(secret_length=len(secret)):
                with patch("app.core.config.JWT_SECRET_KEY", secret):
                    with self.assertRaisesRegex(ValueError, "JWT_SECRET_KEY"):
                        with TestClient(app):
                            pass


if __name__ == "__main__":
    unittest.main()
