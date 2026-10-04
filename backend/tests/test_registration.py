import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.security import password_hash
from app.core.config import get_auth_settings
from app.database import get_session
from app.main import app
from app.models.user import User


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(
            os.environ, {"JWT_SECRET_KEY": "registration-test-secret-" + "x" * 48}
        )
        self.env_patch.start()
        get_auth_settings.cache_clear()
        # Every test gets its own database; the project's ecommerce.db is untouched.
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
            "full_name": "  Sample Shopper  ",
            "password": "example-password-123",
        }

    def tearDown(self):
        self.client.__exit__(None, None, None)
        app.dependency_overrides.pop(get_session, None)
        self.startup_patch.stop()
        self.env_patch.stop()
        get_auth_settings.cache_clear()
        self.engine.dispose()

    def test_registration_persists_hash_and_returns_only_public_fields(self):
        response = self.client.post("/auth/register", json=self.payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {"id": 1, "email": "shopper@example.com", "full_name": "Sample Shopper"},
        )
        with Session(self.engine) as session:
            user = session.exec(select(User)).one()
            self.assertNotEqual(user.hashed_password, self.payload["password"])
            self.assertTrue(
                password_hash.verify(self.payload["password"], user.hashed_password)
            )

    def test_duplicate_email_is_case_insensitive(self):
        self.assertEqual(self.client.post("/auth/register", json=self.payload).status_code, 201)
        duplicate = {**self.payload, "email": "SHOPPER@EXAMPLE.COM"}
        response = self.client.post("/auth/register", json=duplicate)
        self.assertEqual(response.status_code, 409)
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(User)).all()), 1)

    def test_invalid_registration_does_not_create_a_user(self):
        invalid_fields = [
            {"email": "invalid-email"},
            {"password": "short"},
            {"password": " " * 8},
            {"full_name": "   "},
            {"full_name": "x" * 101},
            {"role": "admin"},
            {"hashed_password": "supplied-by-client"},
        ]
        for fields in invalid_fields:
            with self.subTest(fields=list(fields)):
                response = self.client.post(
                    "/auth/register", json={**self.payload, **fields}
                )
                self.assertEqual(response.status_code, 422)
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(User)).all(), [])

    def test_database_enforces_email_uniqueness(self):
        self.client.post("/auth/register", json=self.payload)
        with Session(self.engine) as session:
            session.add(
                User(
                    email=self.payload["email"],
                    full_name="Duplicate",
                    hashed_password="test-only-hash",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

    def test_existing_endpoints_still_work(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/products").json(), [])


if __name__ == "__main__":
    unittest.main()
