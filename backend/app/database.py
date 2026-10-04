from pathlib import Path

from sqlmodel import create_engine, SQLModel, Session


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