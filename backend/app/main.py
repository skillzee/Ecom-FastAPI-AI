from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.core import config
from app.routers.health import router as health_router
from app.routers.products import router as products_router
from app.routers.chat import router as chat_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.cart import router as cart_router
from app.routers.orders import router as orders_router
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(config.JWT_SECRET_KEY.strip().encode("utf-8")) < 32:
        raise ValueError("Set JWT_SECRET_KEY in .env to a random secret of at least 32 bytes")
    create_db_and_tables()
    yield


app = FastAPI(
    title="Ecommerce API",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(products_router)
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(cart_router)
app.include_router(orders_router)
