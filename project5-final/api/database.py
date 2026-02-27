"""database.py — Engine, SessionLocal, init_db + seed из classes.json."""

import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, SchoolClass

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATADIR = os.path.join(BASEDIR, "data")
os.makedirs(DATADIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATADIR, 'school.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_classes(db: Session):
    """Если таблица school_classes пуста — заполняет из data/classes.json."""
    if db.query(SchoolClass).count() > 0:

        return  # уже есть данные
    print(f"[seed] BASEDIR={BASEDIR}  DATADIR={DATADIR}")  # ← добавь эту строку
    # Ищем classes.json в нескольких местах
    candidates = [
        os.path.join(DATADIR, "classes.json"),
        os.path.join(BASEDIR, "classes.json"),
        os.path.join(BASEDIR, "data", "json", "classes.json"),
    ]
    json_path = None
    for p in candidates:
        if os.path.exists(p):
            json_path = p
            break

    if not json_path:
        print("[seed] classes.json не найден — классы не созданы")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    classes_list = data.get("classes", [])
    count = 0
    for cls_data in classes_list:
        pricing = cls_data.get("pricing", {})
        pricing_type = pricing.get("type", "fixed")

        sc = SchoolClass(
            name=cls_data.get("name", cls_data.get("id", "")),
            subjects=cls_data.get("subjects", []),
            pricing_type=pricing_type,
            base_price=float(pricing.get("base_price",
                             cls_data.get("base_price", 0))),
            price_per_subject=float(pricing.get("price_per_subject", 0)),
            exam_subjects=cls_data.get("exam_subjects", []),
        )
        db.add(sc)
        count += 1

    db.commit()
    print(f"[seed] Создано {count} классов из {json_path}")


def init_db():
    """Создаёт таблицы и заполняет классы из JSON при первом запуске."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_classes(db)
    finally:
        db.close()


def drop_db():
    Base.metadata.drop_all(bind=engine)
