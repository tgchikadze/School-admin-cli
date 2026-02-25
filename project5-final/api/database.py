"""
database.py - SQLAlchemy engine, SessionLocal, инициализация БД.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

# ─── Путь к БД ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'school.db')}"

# ─── Engine + Session ─────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite + FastAPI
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── Создание таблиц ─────────────────────────────────────────
def init_db():
    """Создать все таблицы (если не существуют)."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Удалить все таблицы (для пересборки)."""
    Base.metadata.drop_all(bind=engine)
