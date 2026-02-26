"""
conftest.py — фикстуры для pytest.

Использует in-memory SQLite, чтобы не трогать боевую data/school.db.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from api.models import Base, SchoolClass
from api.database import get_db
from api.main import app

# In-memory SQLite для тестов
TEST_ENGINE = create_engine("sqlite:///:memory:", echo=False, future=True)
TestSession = sessionmaker(bind=TEST_ENGINE, expire_on_commit=False)


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


# Подменяем dependency глобально
app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Пересоздаём таблицы перед каждым тестом — чистая БД."""
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)

    # Seed: минимальные классы (без них POST /api/students упадёт с 400)
    db = TestSession()
    classes_data = [
        ("7",  "7",  8500, "fixed",      None),
        ("8",  "8",  8000, "fixed",      None),
        ("9",  "9",  7000, "fixed",      None),
        ("10", "10", 6500, "fixed",      None),
        ("11", "11", 5000, "per_subject", 3000),
    ]
    for cid, name, price, ptype, pps in classes_data:
        db.merge(SchoolClass(
            id=cid, name=name, base_price=price,
            pricing_type=ptype,
            price_per_subject=pps,
            subjects=["Математика", "Русский язык"],
            exam_subjects=["Химия", "Физика", "Биология"] if cid == "11" else None,
        ))
    db.commit()
    db.close()
    yield


@pytest.fixture
def client():
    """TestClient для FastAPI."""
    return TestClient(app)
