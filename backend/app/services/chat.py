import json

from langchain_core.messages import ToolMessage
from app.ai.agent import get_shopping_agent
from app.schemas.chat import ChatMessage, ChatResponse
from app.schemas.product import Product


async def generate_reply(message: str, history: list[ChatMessage] | None = None, *, user_id: int) -> ChatResponse:
    agent = get_shopping_agent(user_id)

    result = await agent.ainvoke(
        {
            "messages": [
                *(entry.model_dump() for entry in (history or [])),
                {"role": "user", "content": message},
            ]
        }
    )

    final_message = result["messages"][-1]

    if not isinstance(final_message.content, str):
        raise ValueError("Expected a text response from the agent")

    # Cards come from successful tool results, never IDs invented in reply text.
    products = {}
    for entry in result["messages"]:
        if isinstance(entry, ToolMessage) and entry.name == "show_products" and isinstance(entry.content, str):
            payload = json.loads(entry.content)
            if payload.get("success"):
                for data in payload["products"]:
                    product = Product.model_validate(data)
                    products[product.id] = product
    return ChatResponse(reply=final_message.content, products=list(products.values())[:6])
