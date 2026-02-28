import os
os.environ["TESTING"] = "1"

import pytest
from starlette.testclient import TestClient

from api.database import engine, SessionLocal
from api.models import Base, SchoolClass, User
from api.auth import create_access_token
from api.main import app
from api.dependencies import get_db, require_manager, require_any


def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _fake_user():
    return User(id=1, username="testadmin", role="admin", hashed_password="x")


app.dependency_overrides[get_db] = _override_get_db
app.dependency_overrides[require_manager] = _fake_user
app.dependency_overrides[require_any] = _fake_user


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    for name, price, ptype, pps in [
        ("7", 8500, "fixed", 0),
        ("8", 8000, "fixed", 0),
        ("9", 7000, "fixed", 0),
        ("10", 6500, "fixed", 0),
        ("11", 5000, "per_subject", 3000),
    ]:
        db.add(SchoolClass(
            name=name, base_price=price,
            pricing_type=ptype, price_per_subject=pps,
            subjects=["Математика", "Русский язык"],
            exam_subjects=["Химия", "Физика", "Биология"] if name == "11" else [],
        ))
    db.commit()
    db.close()
    yield


@pytest.fixture
def client():
    token = create_access_token({"sub": "testadmin", "role": "admin"})
    return TestClient(app, cookies={"access_token": token})
