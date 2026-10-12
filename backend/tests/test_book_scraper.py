import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.models.product import Product
from app.services import book_scraper as scraper

HTML = '''<article class="product_pod"><h3><a title="A Light in the Attic"
href="catalogue/a-light-in-the-attic_1000/index.html">A Light...</a></h3>
<p class="price_color">£51.77</p><p class="availability"> In stock </p></article>'''


class BookScraperTests(unittest.TestCase):
    def setUp(self):
        scraper._cache = None
        scraper._expires = 0
        self.addCleanup(lambda: setattr(scraper, "_cache", None))

    def test_full_title_exact_decimal_price_and_absolute_link(self):
        book = scraper.parse_books(BeautifulSoup(HTML, "html.parser"))[0]
        self.assertEqual(book["name"], "A Light in the Attic")
        self.assertEqual(book["price_minor"], 5177)
        self.assertEqual(book["currency"], "GBP")
        self.assertTrue(book["in_stock"])
        self.assertEqual(book["source_url"], "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")

    def test_invalid_source_data_is_rejected(self):
        for html in ["<html></html>", HTML.replace("51.77", "NaN"),
                     HTML.replace("catalogue/a-light-in-the-attic_1000/index.html", "https://evil.example/")]:
            with self.subTest(html=html), self.assertRaises(scraper.BookScrapeError):
                scraper.parse_books(BeautifulSoup(html, "html.parser"))

    @patch.object(scraper, "WebBaseLoader")
    def test_success_is_cached_and_store_currency_stays_inr(self, loader):
        loader.return_value.scrape.return_value = BeautifulSoup(HTML, "html.parser")
        product = Product(id=1, name="a light in the attic", price_paise=14900)
        result = scraper.compare_book(product)
        scraper.compare_book(product)
        self.assertEqual(loader.return_value.scrape.call_count, 1)
        self.assertEqual(result["store"]["currency"], "INR")
        self.assertEqual(result["external"]["price_minor"], 5177)
        self.assertIsNone(scraper.compare_book(Product(id=2, name="Unmatched", price_paise=100))["external"])

    @patch.object(scraper, "WebBaseLoader")
    def test_failures_are_not_cached(self, loader):
        loader.return_value.scrape.side_effect = TimeoutError()
        for _ in range(2):
            with self.assertRaises(scraper.BookScrapeError):
                scraper.load_books()
        self.assertEqual(loader.return_value.scrape.call_count, 2)

    def test_endpoint_missing_product_source_failure_and_success(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(Product(id=1, name="A Light in the Attic", price_paise=14900))
            session.commit()
        def override_session():
            with Session(engine) as session:
                yield session
        app.dependency_overrides[get_session] = override_session
        self.addCleanup(lambda: app.dependency_overrides.pop(get_session, None))
        client = TestClient(app)
        with patch("app.routers.products.compare_book", side_effect=scraper.BookScrapeError("Try again")) as compare:
            self.assertEqual(client.get("/products/999/compare").status_code, 404)
            compare.assert_not_called()
            self.assertEqual(client.get("/products/1/compare").status_code, 503)
        with patch.object(scraper, "WebBaseLoader") as loader:
            loader.return_value.scrape.return_value = BeautifulSoup(HTML, "html.parser")
            response = client.get("/products/1/compare")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["external"]["price_minor"], 5177)
