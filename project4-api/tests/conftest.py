import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_db
from api.models import University, Program, Olympiad
from api.main import app

TEST_DB = "sqlite:///./test.db"
test_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)

    db = TestSession()
    db.add(University(id="test_uni", name="Test University", city="Testville"))
    db.add(Program(
        university_id="test_uni",
        okso_code="09.03.01",
        program_name="CS",
        program_level="bachelor",
        min_score="250",
        ege_subjects="math, cs",
    ))
    db.add(Olympiad(
        university_id="test_uni",
        olympiad_name="VSOSH",
        olympiad_level="1",
        subject="cs",
        benefit_type="BVI",
        benefit_detail="Enrollment without exams",
    ))
    db.commit()
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield

    app.dependency_overrides.clear()
    test_engine.dispose()
    try:
        os.remove("test.db")
    except (PermissionError, FileNotFoundError):
        pass


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
