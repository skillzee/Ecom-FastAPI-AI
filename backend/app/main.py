from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.core.config import get_auth_settings
from app.routers.health import router as health_router
from app.routers.products import router as products_router
from app.routers.chat import router as chat_router
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_auth_settings()
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
