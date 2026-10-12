import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.database import create_db_and_tables, get_session
from app.main import app
from app.models.product import Product
from app.services.sample_catalog import SAMPLE_PRODUCTS


class SampleCatalogTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        self.addCleanup(self.engine.dispose)
        engine_patch = patch("app.database.engine", self.engine)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)

    def test_startup_makes_sample_catalog_available_through_api(self):
        def override_session():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        self.addCleanup(lambda: app.dependency_overrides.pop(get_session, None))
        with patch("app.core.config.JWT_SECRET_KEY", "sample-test-secret-" + "x" * 48):
            with TestClient(app) as client:
                response = client.get("/products")
                self.assertEqual(response.status_code, 200)
                products = response.json()
        self.assertEqual(len(products), len(SAMPLE_PRODUCTS))
        self.assertIn("A Light in the Attic", {item["name"] for item in products})
        self.assertTrue(any(not item["in_stock"] for item in products))

    def test_repeated_startup_preserves_ids_and_edited_prices_and_stock(self):
        create_db_and_tables()
        with Session(self.engine) as session:
            products = session.exec(select(Product)).all()
            original_ids = {item.name: item.id for item in products}
            products[0].price_paise = 12345
            products[0].in_stock = False
            edited_id = products[0].id
            session.add(products[0])
            session.commit()
        create_db_and_tables()
        with Session(self.engine) as session:
            products = session.exec(select(Product)).all()
            self.assertEqual({item.name: item.id for item in products}, original_ids)
            edited = session.get(Product, edited_id)
            self.assertEqual(edited.price_paise, 12345)
            self.assertFalse(edited.in_stock)

    def test_existing_catalog_is_kept_and_matching_names_are_not_duplicated(self):
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            session.add_all([
                Product(name="Existing Product", price_paise=10000),
                Product(name="  WIRELESS MOUSE  ", price_paise=50000),
            ])
            session.commit()
        create_db_and_tables()
        with Session(self.engine) as session:
            products = session.exec(select(Product)).all()
            self.assertEqual(len(products), len(SAMPLE_PRODUCTS) + 1)
            self.assertIn("Existing Product", {item.name for item in products})
            mouse = next(item for item in products if item.name == SAMPLE_PRODUCTS[6]["name"])
            self.assertEqual(mouse.price_paise, 50000)

    def test_legacy_demo_product_keeps_id_and_price_when_renamed(self):
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            legacy = Product(name="Classic Notebook", price_paise=32100, in_stock=False)
            session.add(legacy)
            session.commit()
            legacy_id = legacy.id
        create_db_and_tables()
        with Session(self.engine) as session:
            book = session.get(Product, legacy_id)
            self.assertEqual(book.name, "A Light in the Attic")
            self.assertEqual(book.price_paise, 32100)
            self.assertFalse(book.in_stock)
