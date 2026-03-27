import os
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

# SQLite file under services/api/data/ (created on first run)
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(_DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(_DATA_DIR, 'gymlife.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    # Import models so SQLModel registers tables before create_all
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
