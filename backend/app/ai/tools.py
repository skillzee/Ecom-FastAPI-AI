from langchain_core.tools import tool
from sqlmodel import Session

from app.database import engine
from app.services import products as product_service

@tool
def list_products() -> list[dict]:
    """List catalog products with IDs, names, prices in paise, and stock status."""
    with Session(engine) as session:
        products = product_service.list_products(session)

        return[
            product.model_dump(mode = "json") 
            for product in products
        ]