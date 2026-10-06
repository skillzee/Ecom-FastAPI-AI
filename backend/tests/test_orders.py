from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.security import create_access_token
from app.database import get_session
from app.main import app
from app.models.cart import CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import CheckoutRequest
from app.services.orders import CheckoutConflictError, checkout


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.secret_patch = patch("app.core.config.JWT_SECRET_KEY", "order-test-secret-" + "x" * 48)
        self.secret_patch.start()
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        def override_session():
            with Session(self.engine) as session:
                yield session

        self.startup_patch = patch("app.main.create_db_and_tables", side_effect=lambda: SQLModel.metadata.create_all(self.engine))
        self.startup_patch.start()
        app.dependency_overrides[get_session] = override_session
        self.client = TestClient(app)
        self.client.__enter__()
        self.seed(self.engine)
        self.headers = {"Authorization": f"Bearer {create_access_token(1)}"}
        self.other_headers = {"Authorization": f"Bearer {create_access_token(2)}"}
        self.payload = {
            "checkout_key": str(uuid4()),
            "shipping": {"full_name": "Shopper", "address": "10 Sample Street", "city": "Pune", "postal_code": "411001", "country": "India"},
            "items": [{"product_id": 1, "quantity": 2, "unit_price_paise": 12550}],
            "expected_total_paise": 25100,
        }

    @staticmethod
    def seed(engine):
        with Session(engine) as session:
            session.add_all([
                User(id=1, email="one@example.com", full_name="One", hashed_password="unused"),
                User(id=2, email="two@example.com", full_name="Two", hashed_password="unused"),
                Product(id=1, name="Notebook", price_paise=12550, in_stock=True),
                CartItem(id=1, user_id=1, product_id=1, quantity=2),
                CartItem(id=2, user_id=2, product_id=1, quantity=7),
            ])
            session.commit()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        app.dependency_overrides.pop(get_session, None)
        self.startup_patch.stop()
        self.secret_patch.stop()
        self.engine.dispose()

    def place(self, payload=None, headers=None):
        return self.client.post("/orders", json=payload or self.payload, headers=headers or self.headers)

    def test_checkout_saves_snapshot_and_clears_only_own_cart(self):
        response = self.place()
        self.assertEqual(response.status_code, 201, response.text)
        order = response.json()
        self.assertEqual(order["total_paise"], 25100)
        self.assertEqual(order["status"], "pending_payment")
        self.assertEqual(order["shipping"], self.payload["shipping"])
        self.assertEqual(order["items"], [{"product_id": 1, "name": "Notebook", "quantity": 2, "unit_price_paise": 12550, "subtotal_paise": 25100}])
        self.assertTrue(order["created_at"].endswith("+00:00"))
        self.assertEqual(self.client.get("/cart", headers=self.headers).json()["items"], [])
        self.assertEqual(self.client.get("/cart", headers=self.other_headers).json()["items"][0]["quantity"], 7)
        with Session(self.engine) as session:
            product = session.get(Product, 1)
            product.name = "Changed"
            product.price_paise = 99999
            session.add(product)
            session.commit()
            session.delete(product)
            session.commit()
        self.assertEqual(self.client.get(f"/orders/{order['id']}", headers=self.headers).json(), order)

    def test_same_key_returns_same_order_even_after_cart_is_cleared(self):
        first = self.place()
        retry = self.place()
        self.assertEqual(retry.status_code, 201)
        self.assertEqual(first.json(), retry.json())
        with Session(self.engine) as session:
            self.assertEqual(len(session.exec(select(Order)).all()), 1)
        changed = {**self.payload, "shipping": {**self.payload["shipping"], "city": "Mumbai"}}
        self.assertEqual(self.place(changed).status_code, 409)
        self.assertEqual(self.place({**self.payload, "checkout_key": str(uuid4())}).status_code, 409)

    def test_order_history_is_private(self):
        order = self.place().json()
        self.assertEqual(self.client.get("/orders", headers=self.headers).json(), [order])
        self.assertEqual(self.client.get("/orders", headers=self.other_headers).json(), [])
        for order_id in [order["id"], 999]:
            response = self.client.get(f"/orders/{order_id}", headers=self.other_headers)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"detail": "Order not found"})

    def test_order_endpoints_require_authentication(self):
        for method, path, kwargs in [
            (self.client.post, "/orders", {"json": self.payload}),
            (self.client.get, "/orders", {}),
            (self.client.get, "/orders/1", {}),
        ]:
            self.assertEqual(method(path, **kwargs).status_code, 401)

    def test_changed_cart_and_prices_leave_cart_unchanged(self):
        for changes in [{"price_paise": 20000}, {"in_stock": False}]:
            with self.subTest(changes=changes):
                with Session(self.engine) as session:
                    product = session.get(Product, 1)
                    for field, value in changes.items(): setattr(product, field, value)
                    session.add(product)
                    session.commit()
                self.assertEqual(self.place().status_code, 409)
                with Session(self.engine) as session:
                    self.assertEqual(session.get(CartItem, 1).quantity, 2)
                    self.assertEqual(session.exec(select(Order)).all(), [])
                    product = session.get(Product, 1)
                    product.price_paise = 12550
                    product.in_stock = True
                    session.add(product)
                    session.commit()
        with Session(self.engine) as session:
            item = session.get(CartItem, 1)
            item.quantity = 3
            session.add(item)
            session.commit()
        self.assertEqual(self.place().status_code, 409)

    def test_missing_product_blocks_checkout(self):
        with Session(self.engine) as session:
            session.delete(session.get(Product, 1))
            session.commit()
        self.assertEqual(self.place().status_code, 409)
        self.assertEqual(len(self.client.get("/cart", headers=self.headers).json()["items"]), 1)

    def test_invalid_payload_and_client_supplied_status_are_rejected(self):
        for changes in [
            {"status": "paid"}, {"user_id": 2}, {"expected_total_paise": 1},
            {"checkout_key": "invalid"}, {"items": []},
            {"shipping": {**self.payload["shipping"], "full_name": "   "}},
            {"items": self.payload["items"] * 2, "expected_total_paise": 50200},
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(self.place({**self.payload, **changes}).status_code, 422)
        self.assertEqual(self.client.get("/orders", headers=self.headers).json(), [])

    def test_database_failure_rolls_back_order_and_cart_changes(self):
        with patch("app.services.orders.Session.commit", side_effect=RuntimeError("Simulated database failure")):
            with self.assertRaisesRegex(RuntimeError, "Simulated database failure"):
                self.place()
        with Session(self.engine) as session:
            self.assertEqual(session.exec(select(Order)).all(), [])
            self.assertEqual(session.exec(select(OrderItem)).all(), [])
            self.assertEqual(session.get(CartItem, 1).quantity, 2)

    def test_concurrent_checkouts_do_not_duplicate_orders(self):
        with TemporaryDirectory() as directory:
            engine = create_engine(f"sqlite:///{Path(directory) / 'orders.db'}", connect_args={"check_same_thread": False})
            try:
                SQLModel.metadata.create_all(engine)
                self.seed(engine)

                def run(key):
                    with Session(engine) as session:
                        try:
                            result = checkout(session, 1, CheckoutRequest(**{**self.payload, "checkout_key": key}))
                            return result.id
                        except CheckoutConflictError:
                            return None

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(run, [self.payload["checkout_key"], self.payload["checkout_key"]]))
                self.assertEqual(results[0], results[1])
                with Session(engine) as session:
                    self.assertEqual(len(session.exec(select(Order)).all()), 1)
                # Refill the cart and race different checkout keys.
                with Session(engine) as session:
                    session.add(CartItem(user_id=1, product_id=1, quantity=2))
                    session.commit()
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(run, [str(uuid4()), str(uuid4())]))
                self.assertEqual(sum(result is not None for result in results), 1)
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
