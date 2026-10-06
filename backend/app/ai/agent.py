from functools import lru_cache

from langchain.agents import create_agent

from app.ai.model import get_chat_model
from app.ai.tools import list_products

@lru_cache
def get_shopping_agent():
    return create_agent(
        model=get_chat_model(),
        tools=[list_products],
        system_prompt=(
            "You are an ecommerce shopping assistant. "
            "Use list_products when answering questions about the catalog, "
            "product prices, or stock availability. "
            "Base catalog answers on the tool results. "
            "You can help users discover products but cannot access accounts, carts, "
            "orders, shipping details, or payments. Never claim to modify a cart, "
            "place an order, or collect payment. Direct users to the bag for checkout. "
            "Prices are stored in paise; divide by 100 to express rupees. "
            "Give concise, helpful answers."
        )
    )
