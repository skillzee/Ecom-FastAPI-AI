"""Read the demo book listing without accepting arbitrary scrape URLs."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from threading import Lock
from time import monotonic
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader

SOURCE_URL = "https://books.toscrape.com/"
_cache = None
_expires = 0.0
_lock = Lock()


class BookScrapeError(Exception):
    pass


def parse_books(soup: BeautifulSoup) -> list[dict]:
    books = []
    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        price = card.select_one(".price_color")
        stock = card.select_one(".availability")
        if not link or not price or not stock:
            raise BookScrapeError("The book listing format has changed.")
        name = (link.get("title") or link.get_text()).strip()
        source_url = urljoin(SOURCE_URL, link.get("href", ""))
        if urlparse(source_url).hostname != "books.toscrape.com":
            raise BookScrapeError("Unexpected book source link.")
        try:
            # UTF-8 decoding is configured on the loader; currency is always GBP.
            value = Decimal(price.get_text(strip=True).removeprefix("£"))
            if not value.is_finite() or value < 0 or value * 100 != int(value * 100):
                raise ValueError("Invalid price")
            minor = int(value * 100)
        except (InvalidOperation, ValueError, OverflowError) as exc:
            raise BookScrapeError("Unable to read the book price.") from exc
        books.append({"name": name, "price_minor": minor, "currency": "GBP",
                      "in_stock": "in stock" in stock.get_text(" ", strip=True).casefold(),
                      "source_url": source_url})
    if not books:
        raise BookScrapeError("No books were found in the source listing.")
    return books


def load_books() -> tuple[list[dict], str]:
    """Cache successful first-page reads for five minutes; never cache failures."""
    global _cache, _expires
    with _lock:
        if _cache is not None and monotonic() < _expires:
            return _cache
        try:
            loader = WebBaseLoader(
                web_paths=(SOURCE_URL,), encoding="utf-8",
                header_template={"User-Agent": "EverydayBookComparison/1.0"},
                requests_kwargs={"timeout": 8, "allow_redirects": False},
                raise_for_status=True,
            )
            # scrape() returns BeautifulSoup, preserving titles, prices and links.
            books = parse_books(loader.scrape())
        except BookScrapeError:
            raise
        except Exception as exc:
            raise BookScrapeError("Books to Scrape is unavailable. Please try again.") from exc
        checked_at = datetime.now(timezone.utc).isoformat()
        _cache = (books, checked_at)
        _expires = monotonic() + 300
        return _cache


def compare_book(product) -> dict:
    books, checked_at = load_books()
    match = next((book for book in books
                  if book["name"].casefold() == product.name.strip().casefold()), None)
    return {
        "product_id": product.id,
        "name": product.name,
        "store": {"price_minor": product.price_paise, "currency": "INR", "in_stock": product.in_stock},
        "external": match,
        "checked_at": checked_at,
        "message": "Prices use different currencies; no conversion is applied." if match else
                   "No exact title match on the first page of Books to Scrape.",
    }
