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


def import_partners_json(force=False):
    from api.models import University, Program, Olympiad

    def normalize_benefit(raw: str) -> str:
        """Извлечь чистые типы льгот из сырого текста."""
        raw_lower = raw.lower()
        types = []
        if "бви" in raw_lower or "без вступительных" in raw_lower:
            types.append("БВИ")
        if "100 баллов" in raw_lower or "100 за егэ" in raw_lower or "ege100" in raw_lower:
            types.append("100 баллов")
        if ("доп" in raw_lower and "балл" in raw_lower) or "idpoints" in raw_lower:
            types.append("доп. баллы")
        return "; ".join(types) if types else raw[:100]

    def clean(val):
        if val is None or str(val).strip().lower() == "nan":
            return ""
        return str(val).strip()

    db = SessionLocal()

    # Если не force — пропустить если данные уже есть
    if not force and db.query(University).count() > 0:
        db.close()
        return

    json_path = BASE_DIR / "data" / "partners.json"
    if not json_path.exists():
        db.close()
        return

    with open(json_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    for uni_id, uni_data in data.items():
        progs = uni_data.get("programs", [])
        olyms = uni_data.get("olympiads", [])

        if not progs and not olyms:
            continue

        first = progs[0] if progs else olyms[0]
        db.add(University(
            id=uni_id,
            name=clean(first.get("university_name", first.get("universityname", uni_id))),
            city=clean(first.get("city", "")),
        ))

        for p in progs:
            db.add(Program(
                university_id=uni_id,
                okso_code=clean(p.get("okso_code", p.get("oksocode", ""))),
                program_name=clean(p.get("program_name", p.get("programname", ""))),
                program_level=clean(p.get("program_level", p.get("programlevel", ""))),
                min_score=clean(p.get("min_score", p.get("minscore", ""))),
                budget_places=clean(p.get("budget_places", p.get("budgetplaces", ""))),
                cost=clean(p.get("cost", "")),
                ege_subjects=clean(p.get("ege_subjects", p.get("egesubjects", ""))),
            ))

        for o in olyms:
            raw_benefit = clean(o.get("benefit_type", o.get("benefittype", "")))
            db.add(Olympiad(
                university_id=uni_id,
                olympiad_name=clean(o.get("olympiad_name", o.get("olympiadname", ""))),
                olympiad_level=clean(o.get("olympiad_level", o.get("olympiadlevel", ""))),
                subject=clean(o.get("subject", "")),
                benefit_type=normalize_benefit(raw_benefit),
                benefit_detail=clean(o.get("benefit_detail", o.get("benefitdetail", "")))[:1000],
                source_url=clean(o.get("olympiad_url", o.get("olympiadurl", ""))),
                reviewed=False,
            ))

    db.commit()
    t = db.query(University).count(), db.query(Program).count(), db.query(Olympiad).count()
    print(f"Imported: {t[0]} universities, {t[1]} programs, {t[2]} olympiads")
    db.close()