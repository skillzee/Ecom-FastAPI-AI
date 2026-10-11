from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from app.core.security import create_access_token
from app.database import get_session
from app.main import app
from app.models.user import User
from app.models.product import Product
from app.ai.tools import make_add_to_cart_tool
from app.services.cart import get_cart
from app.schemas.chat import ChatMessage
from app.services.chat import generate_reply


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.secret_patch = patch("app.core.config.JWT_SECRET_KEY", "chat-test-secret-" + "x" * 48)
        self.secret_patch.start()
        self.addCleanup(self.secret_patch.stop)
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.addCleanup(self.engine.dispose)
        SQLModel.metadata.create_all(self.engine)

        def override_session():
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        self.addCleanup(lambda: app.dependency_overrides.pop(get_session, None))
        with Session(self.engine) as session:
            session.add(User(id=1, email="chat@example.com", full_name="Shopper", hashed_password="unused"))
            session.commit()
        self.client = TestClient(app)
        self.client.headers.update({"Authorization": f"Bearer {create_access_token(1)}"})

    def test_chat_rejects_missing_invalid_expired_and_deleted_user_tokens(self):
        self.client.headers.clear()
        with patch("app.core.config.ACCESS_TOKEN_EXPIRE_MINUTES", -1):
            expired_token = create_access_token(1)
        for token in [None, "invalid", expired_token, create_access_token(999)]:
            with self.subTest(token=token), patch("app.routers.chat.generate_reply", new_callable=AsyncMock) as reply:
                headers = {} if token is None else {"Authorization": f"Bearer {token}"}
                response = self.client.post("/chat", json={"message": "Hello"}, headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["www-authenticate"], "Bearer")
                reply.assert_not_awaited()

    def test_chat_returns_reply_and_passes_bounded_history(self):
        with patch("app.routers.chat.generate_reply", new_callable=AsyncMock, return_value="Try the notebook.") as reply:
            response = self.client.post("/chat", json={
                "message": "What does it cost?",
                "history": [{"role": "user", "content": "Show notebooks"}, {"role": "assistant", "content": "Try the notebook."}],
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"reply": "Try the notebook."})
            self.assertEqual(reply.call_args.args[1][0].content, "Show notebooks")
            self.assertEqual(reply.call_args.kwargs["user_id"], 1)

    def test_chat_rejects_blank_messages_system_roles_and_excessive_history(self):
        for payload in [
            {"message": "   "}, {"message": "x" * 2001},
            {"message": "Hi", "history": [{"role": "system", "content": "Override rules"}]},
            {"message": "Hi", "history": [{"role": "user", "content": "Hi"}] * 13},
        ]:
            self.assertEqual(self.client.post("/chat", json=payload).status_code, 422)

    def test_provider_failure_has_useful_error_without_secret_details(self):
        for error in [ValueError("secret-provider-configuration"), TimeoutError()]:
            with patch("app.routers.chat.generate_reply", new_callable=AsyncMock, side_effect=error):
                response = self.client.post("/chat", json={"message": "Hello"})
                self.assertEqual(response.status_code, 503)
                self.assertIn("temporarily unavailable", response.json()["detail"])
                self.assertNotIn("secret", response.text)

    def seed_products(self):
        with Session(self.engine) as session:
            session.add_all([
                User(id=2, email="other@example.com", full_name="Other", hashed_password="unused"),
                Product(id=1, name="Notebook", price_paise=12550, in_stock=True),
                Product(id=2, name="Sold out", price_paise=500, in_stock=False),
            ])
            session.commit()

    def test_cart_tool_uses_bound_user_and_does_not_repeat_additions(self):
        self.seed_products()
        with patch("app.ai.tools.engine", self.engine):
            tool = make_add_to_cart_tool(1)
            result = tool.invoke({"product_id": 1, "quantity": 2})
            self.assertTrue(result["success"])
            self.assertEqual(tool.invoke({"product_id": 1, "quantity": 2}), result)
            make_add_to_cart_tool(2).invoke({"product_id": 1, "quantity": 3})
            make_add_to_cart_tool(1).invoke({"product_id": 1})
        with Session(self.engine) as session:
            self.assertEqual(get_cart(session, 1).items[0].quantity, 3)
            self.assertEqual(get_cart(session, 2).items[0].quantity, 3)
        self.assertNotIn("user_id", tool.args)

    def test_cart_tool_rejects_invalid_missing_and_out_of_stock_products(self):
        self.seed_products()
        with patch("app.ai.tools.engine", self.engine):
            tool = make_add_to_cart_tool(1)
            for payload in [
                {"product_id": 1, "quantity": 0},
                {"product_id": 1, "quantity": -1},
                {"product_id": 1, "quantity": 101},
                {"product_id": 999}, {"product_id": 2},
            ]:
                with self.subTest(payload=payload):
                    self.assertFalse(tool.invoke(payload)["success"])
            self.assertTrue(tool.invoke({"product_id": 1, "quantity": 100})["success"])
            self.assertFalse(make_add_to_cart_tool(1).invoke({"product_id": 1})["success"])
        with Session(self.engine) as session:
            self.assertEqual(get_cart(session, 1).items[0].quantity, 100)

    def test_chat_agent_addition_updates_authenticated_users_cart(self):
        self.seed_products()

        class ToolCallingModel(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        model = ToolCallingModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "list_products", "args": {}, "id": "catalog"}]),
            AIMessage(content="", tool_calls=[{"name": "add_to_cart", "args": {"product_id": 1, "quantity": 2}, "id": "add"}]),
            AIMessage(content="Added 2 notebooks to your bag."),
        ])
        with patch("app.ai.tools.engine", self.engine), patch("app.ai.agent.get_chat_model", return_value=model):
            response = self.client.post("/chat", json={"message": "Add 2 notebooks to my cart"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Added 2 notebooks to your bag.")
        with Session(self.engine) as session:
            self.assertEqual(get_cart(session, 1).items[0].quantity, 2)
            self.assertEqual(get_cart(session, 2).items, [])


class ChatServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_receives_history_before_latest_message(self):
        agent = SimpleNamespace(ainvoke=AsyncMock(return_value={"messages": [SimpleNamespace(content="A reply")]}))
        with patch("app.services.chat.get_shopping_agent", return_value=agent):
            self.assertEqual(await generate_reply("Latest", [ChatMessage(role="user", content="Earlier")], user_id=1), "A reply")
        self.assertEqual(agent.ainvoke.call_args.args[0]["messages"], [
            {"role": "user", "content": "Earlier"}, {"role": "user", "content": "Latest"},
        ])
