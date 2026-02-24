"""
SQLite + SQLAlchemy connection, sessions, JSON import.
"""
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'data' / 'school.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def import_partners_json():
    # Импорт здесь (не наверху) чтобы избежать circular import
    from api.models import University, Program, Olympiad

    db = SessionLocal()
    if db.query(University).count() > 0:
        db.close()
        return

    json_path = BASE_DIR / "data" / "partners.json"
    if not json_path.exists():
        print(f"WARNING: {json_path} not found, DB stays empty")
        db.close()
        return

    with open(json_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    for uni_id, uni_data in data.items():
        progs = uni_data.get("programs", [])
        olyms = uni_data.get("olympiads", [])
        if not progs and not olyms:
            continue

        first = progs[0] if progs else {}
        db.add(University(
            id=uni_id,
            name=first.get("university_name", uni_id),
            city=first.get("city", ""),
        ))

        for p in progs:
            db.add(Program(
                university_id=uni_id,
                okso_code=p.get("okso_code", ""),
                program_name=p.get("program_name", ""),
                program_level=p.get("program_level", ""),
                min_score=p.get("min_score", ""),
                avg_score=p.get("avg_score", ""),
                budget_places=p.get("budget_places", ""),
                cost=p.get("cost", ""),
                ege_subjects=p.get("ege_subjects", ""),
                achievements=p.get("achievements", "")[:500],
                source=p.get("source", ""),
                page_url=p.get("page_url", ""),
            ))

        for o in olyms:
            db.add(Olympiad(
                university_id=uni_id,
                olympiad_name=o.get("olympiad_name", ""),
                olympiad_level=o.get("olympiad_level", ""),
                subject=o.get("subject", ""),
                benefit_type=o.get("benefit_type", o.get("benefit_types", "")),
                benefit_detail=o.get("benefit_detail", "")[:1000],
                source_url=o.get("olympiad_url", ""),
            ))

    db.commit()
    total_u = db.query(University).count()
    total_p = db.query(Program).count()
    total_o = db.query(Olympiad).count()
    print(f"Imported: {total_u} universities, {total_p} programs, {total_o} olympiads")
    db.close()
