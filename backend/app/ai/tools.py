import logging
from threading import Lock

from langchain_core.tools import tool
from pydantic import ValidationError
from sqlmodel import Session

from app.database import engine
from app.schemas.cart import CartItemCreate
from app.services import cart as cart_service
from app.services import products as product_service
from app.services import orders as order_service
from app.services.book_scraper import BookScrapeError, compare_book

from app.ai.rag import retrieve_policies

logger  = logging.getLogger(__name__)

def make_order_tools(user_id: int):
    """Bind read-only order access to the authenticated user for this request."""
    @tool
    def list_my_orders(limit: int = 20, offset: int = 0) -> dict:
        """Fetch the signed-in user's orders, newest first, with items and INR totals.

        Use for order history, latest order, purchases and order status questions.
        Limit is 1 to 50; offset skips earlier results. Follow next_offset when
        has_more is true to search older purchases or calculate complete totals.
        Use get_my_order for a specific order's full details and shipping address.
        """
        if not 1 <= limit <= 50 or offset < 0:
            return {"success": False, "error": "Use limit 1 to 50 and a nonnegative offset."}
        with Session(engine) as session:
            orders = order_service.list_orders(session, user_id, limit=limit + 1, offset=offset)
        has_more = len(orders) > limit
        return {"success": True, "currency": "INR",
                "orders": [order.model_dump(mode="json", exclude={"shipping"}) for order in orders[:limit]],
                "has_more": has_more, "next_offset": offset + limit if has_more else None}

    @tool
    def get_my_order(order_id: int) -> dict:
        """Fetch one of the signed-in user's orders by ID, including shipping details.

        Returns saved item names, quantities, INR prices, total, date and status.
        This is read-only; it does not track shipments or change orders.
        """
        if order_id <= 0:
            return {"success": False, "error": "Use a positive order ID."}
        with Session(engine) as session:
            order = order_service.get_order(session, user_id, order_id)
        if order is None:
            return {"success": False, "error": "Order not found in your account."}
        return {"success": True, "currency": "INR", "order": order.model_dump(mode="json")}

    return [list_my_orders, get_my_order]


def make_add_to_cart_tool(user_id: int):
    """Bind a cart tool to the authenticated user for one chat request."""
    added = {}
    lock = Lock()

    @tool
    def add_to_cart(product_id: int, quantity: int = 1) -> dict:
        """Add a catalog product to the signed-in user's cart when requested.

        Use list_products to resolve the product ID. Quantity is the number to
        add (1 to 100), not the final cart quantity. Never choose a user ID.
        """
        try:
            item_data = CartItemCreate(product_id=product_id, quantity=quantity)
        except ValidationError:
            return {"success": False, "error": "Use a positive product ID and a quantity from 1 to 100."}
        with lock:
            # A repeated tool call in the same turn must not add twice.
            if product_id in added:
                return added[product_id]
            with Session(engine) as session:
                try:
                    item = cart_service.add_cart_item(session, user_id, item_data.product_id, item_data.quantity)
                except cart_service.ProductNotFoundError:
                    return {"success": False, "error": "Product not found. Check the catalog again."}
                except cart_service.ProductOutOfStockError:
                    return {"success": False, "error": "This product is out of stock."}
                except cart_service.CartQuantityLimitError:
                    return {"success": False, "error": "Maximum cart quantity is 100 per product."}
                result = {"success": True, "product_id": item.product_id, "quantity_added": quantity, "cart_quantity": item.quantity}
                added[product_id] = result
                return result

    return add_to_cart

@tool
def list_products() -> list[dict]:
    """List catalog products with IDs, names, prices in paise, and stock status."""
    logger.info("Agent called list_products")
    with Session(engine) as session:
        products = product_service.list_products(session)

        result = [
            product.model_dump(mode = "json") 
            for product in products
        ]
    logger.info("list_products returned %s products", len(result))
    return result



@tool
def compare_product_price(product_id: int) -> dict:
    """Compare an Everyday book's current INR price with Books to Scrape's GBP price.

    Resolve the product ID with list_products first. Returns source timestamp,
    availability and source link. Different currencies cannot establish savings.
    """
    with Session(engine) as session:
        product = product_service.get_product(session, product_id)
        if product is None:
            return {"success": False, "error": "Product not found. Check the catalog again."}
        try:
            return {"success": True, **compare_book(product)}
        except BookScrapeError as exc:
            return {"success": False, "error": str(exc)}


@tool
def show_products(product_ids: list[int]) -> dict:
    """Display up to six catalog products as chat cards with Compare price buttons.

    Use list_products to find IDs, then select only products relevant to the user's
    search or recommendation request. This does not scrape prices or add to cart.
    """
    if not product_ids or len(product_ids) > 6:
        return {"success": False, "error": "Select between one and six product IDs."}
    with Session(engine) as session:
        products = [product_service.get_product(session, pid) for pid in dict.fromkeys(product_ids)]
        if any(product is None for product in products):
            return {"success": False, "error": "Product not found. Check the catalog again."}
        return {"success": True, "products": [product.model_dump(mode="json") for product in products]}


@tool
def search_store_policies(question: str) ->str:
    """Search store policies about returns, refunds, shipping, and other rules."""
    docs = retrieve_policies(question)

    if not docs:
        return "No policy passages were found."

    return "\n\n".join(
        f"Source: {doc.metadata.get('source', 'policy PDF')}, "
        f"page {doc.metadata.get('page', 0) + 1}\n"
        f"{doc.page_content}"
        for doc in docs
    )

