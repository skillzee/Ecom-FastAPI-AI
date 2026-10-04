from pathlib import Path

from sqlmodel import create_engine, SQLModel, Session

# Import table models before create_all so their definitions are registered.
from app.models.product import Product
from app.models.user import User


DATABASE_PATH = Path(__file__).resolve().parent.parent / "ecommerce.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
