import logging

from langchain_core.tools import tool
from sqlmodel import Session

from app.database import engine
from app.services import products as product_service

from app.ai.rag import retrieve_policies

logger  = logging.getLogger(__name__)

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
    docs = retrieve_policies()

    if not docs:
        return "No policy passages were found."

    return "\n\n".join(
        f"Source: {doc.metadata.get('source', 'policy PDF')}, "
        f"page {doc.metadata.get('page', 0) + 1}\n"
        f"{doc.page_content}"
        for doc in docs
    )

