from app.ai.agent import get_shopping_agent


async def generate_reply(message: str) -> str:
    agent = get_shopping_agent()

    result = await agent.ainvoke(
        {
            "messages": [
                {"role": "user", "content": message},
            ]
        }
    )

    final_message = result["messages"][-1]

    if not isinstance(final_message.content, str):
        raise ValueError("Expected a text response from the agent")

    return final_message.content