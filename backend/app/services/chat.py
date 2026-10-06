from app.ai.agent import get_shopping_agent
from app.schemas.chat import ChatMessage


async def generate_reply(message: str, history: list[ChatMessage] | None = None) -> str:
    agent = get_shopping_agent()

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

    return final_message.content
