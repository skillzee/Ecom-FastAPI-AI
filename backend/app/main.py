from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.routers.health import router as health_router
from app.routers.products import router as products_router
from app.routers.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Ecommerce API",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(products_router)
app.include_router(chat_router)