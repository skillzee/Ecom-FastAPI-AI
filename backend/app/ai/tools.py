import logging
from threading import Lock

from langchain_core.tools import tool
from pydantic import ValidationError
from sqlmodel import Session

from app.database import engine
from app.schemas.cart import CartItemCreate
from app.services import cart as cart_service
from app.services import products as product_service

from app.ai.rag import retrieve_policies

logger  = logging.getLogger(__name__)

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

