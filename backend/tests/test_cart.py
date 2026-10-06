import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import create_access_token
from app.database import get_session
from app.main import app
from app.models.product import Product
from app.models.user import User


class CartTests(unittest.TestCase):
    def setUp(self):
        self.secret_patch = patch(
            "app.core.config.JWT_SECRET_KEY", "cart-test-secret-" + "x" * 48
        )
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
        with Session(self.engine) as session:
            session.add_all([
                User(id=1, email="one@example.com", full_name="One", hashed_password="unused"),
                User(id=2, email="two@example.com", full_name="Two", hashed_password="unused"),
                Product(id=1, name="Notebook", price_paise=12550, in_stock=True),
                Product(id=2, name="Pen", price_paise=105, in_stock=True),
                Product(id=3, name="Sold out", price_paise=500, in_stock=False),
            ])
            session.commit()
        self.headers = {"Authorization": f"Bearer {create_access_token(1)}"}
        self.other_headers = {"Authorization": f"Bearer {create_access_token(2)}"}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        app.dependency_overrides.pop(get_session, None)
        self.startup_patch.stop()
        self.secret_patch.stop()
        self.engine.dispose()

    def add(self, product_id=1, quantity=2, headers=None):
        return self.client.post(
            "/cart/items",
            json={"product_id": product_id, "quantity": quantity},
            headers=self.headers if headers is None else headers,
        )

    def cart(self, headers=None):
        return self.client.get(
            "/cart", headers=self.headers if headers is None else headers
        )

    def test_empty_cart(self):
        response = self.cart()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": [], "total_paise": 0})

    def test_cart_details_totals_and_quantity_replacement(self):
        response = self.add()
        self.assertEqual(response.status_code, 200)
        item_id = response.json()["id"]
        self.add(2, 3)
        cart = self.cart().json()
        self.assertEqual(cart["total_paise"], 25415)
        self.assertEqual(cart["items"][0], {
            "id": item_id, "product_id": 1, "quantity": 2,
            "product": {"id": 1, "name": "Notebook", "price_paise": 12550, "in_stock": True},
            "subtotal_paise": 25100,
        })
        updated = self.client.patch(
            f"/cart/items/{item_id}", json={"quantity": 4}, headers=self.headers
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["quantity"], 4)
        self.assertEqual(self.cart().json()["total_paise"], 50515)

    def test_delete_item_and_missing_item(self):
        item_id = self.add().json()["id"]
        response = self.client.delete(f"/cart/items/{item_id}", headers=self.headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.cart().json(), {"items": [], "total_paise": 0})
        self.assertEqual(
            self.client.delete(f"/cart/items/{item_id}", headers=self.headers).status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(f"/cart/items/{item_id}", json={"quantity": 1}, headers=self.headers).status_code,
            404,
        )

    def test_cart_isolation(self):
        item_id = self.add().json()["id"]
        self.assertEqual(self.cart(self.other_headers).json()["items"], [])
        for method, kwargs in [
            (self.client.patch, {"json": {"quantity": 5}}),
            (self.client.delete, {}),
        ]:
            response = method(f"/cart/items/{item_id}", headers=self.other_headers, **kwargs)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"detail": "Cart item not found"})
        self.add(quantity=7, headers=self.other_headers)
        self.assertEqual(self.cart().json()["items"][0]["quantity"], 2)
        self.assertEqual(self.cart(self.other_headers).json()["items"][0]["quantity"], 7)

    def test_all_cart_endpoints_require_authentication(self):
        for headers in [{}, {"Authorization": "Bearer invalid-token"}]:
            for method, path, kwargs in [
                (self.client.get, "/cart", {}),
                (self.client.post, "/cart/items", {"json": {"product_id": 1, "quantity": 1}}),
                (self.client.patch, "/cart/items/1", {"json": {"quantity": 1}}),
                (self.client.delete, "/cart/items/1", {}),
            ]:
                with self.subTest(path=path, method=method.__name__, headers=headers):
                    self.assertEqual(method(path, headers=headers, **kwargs).status_code, 401)

    def test_invalid_update_preserves_quantity(self):
        item_id = self.add().json()["id"]
        for payload in [{"quantity": 0}, {"quantity": -1}, {"quantity": 101}, {}, {"quantity": 1, "user_id": 2}]:
            with self.subTest(payload=payload):
                response = self.client.patch(f"/cart/items/{item_id}", json=payload, headers=self.headers)
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.cart().json()["items"][0]["quantity"], 2)
        self.assertEqual(self.client.patch(
            f"/cart/items/{item_id}", json={"quantity": 100}, headers=self.headers
        ).status_code, 200)

    def test_add_merges_items_and_rejects_quantity_overflow(self):
        item_id = self.add(quantity=99).json()["id"]
        response = self.add(quantity=1)
        self.assertEqual(response.json(), {"id": item_id, "product_id": 1, "quantity": 100})
        self.assertEqual(self.add(quantity=1).status_code, 409)
        self.assertEqual(len(self.cart().json()["items"]), 1)
        self.assertEqual(self.cart().json()["items"][0]["quantity"], 100)

    def test_missing_and_out_of_stock_products(self):
        self.assertEqual(self.add(product_id=999).status_code, 404)
        self.assertEqual(self.add(product_id=3).status_code, 409)
        item_id = self.add().json()["id"]
        with Session(self.engine) as session:
            product = session.get(Product, 1)
            product.in_stock = False
            session.add(product)
            session.commit()
        response = self.client.patch(f"/cart/items/{item_id}", json={"quantity": 3}, headers=self.headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.cart().json()["items"][0]["quantity"], 2)
        self.assertEqual(self.client.delete(f"/cart/items/{item_id}", headers=self.headers).status_code, 204)

    def test_deleted_product_remains_removable_and_totals_use_current_prices(self):
        item_id = self.add().json()["id"]
        with Session(self.engine) as session:
            product = session.get(Product, 1)
            product.price_paise = 20000
            session.add(product)
            session.commit()
        self.assertEqual(self.cart().json()["total_paise"], 40000)
        self.add(product_id=2, quantity=1)
        self.assertEqual(self.client.delete("/products/1").status_code, 204)
        cart = self.cart().json()
        self.assertIsNone(cart["items"][0]["product"])
        self.assertIsNone(cart["items"][0]["subtotal_paise"])
        self.assertEqual(cart["total_paise"], 105)
        self.assertEqual(self.client.patch(
            f"/cart/items/{item_id}", json={"quantity": 3}, headers=self.headers
        ).status_code, 404)
        self.assertEqual(self.client.delete(f"/cart/items/{item_id}", headers=self.headers).status_code, 204)


if __name__ == "__main__":
    unittest.main()
