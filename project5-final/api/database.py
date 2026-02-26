"""
database.py — SQLAlchemy engine + SessionLocal + init_db() с seed из JSON.

При первом запуске:
  1. Создаёт все таблицы из models.py
  2. Импортирует classes.json   -> school_classes
  3. Импортирует students.json  -> students
  4. Импортирует exam_choices.json -> exam_choices
  5. Импортирует partners.json  -> universities + programs + olympiads
  6. Создаёт дефолтного admin-пользователя
"""

import json
import math
import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from .models import (
    Base, User, SchoolClass, Student, ExamChoice,
    University, Program, Olympiad, OlympiadProgramBenefit,
)

# --- Путь к БД ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'school.db')}"

# --- Engine + Session ---
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency — генератор сессий."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ====================================================================
#  SEED HELPERS
# ====================================================================

def _safe_str(val) -> Optional[str]:
    """NaN / None / пустая строка -> None, иначе str."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    s = str(val).strip()
    return s if s else None


def _truncate_text(text, max_len: int = 500) -> Optional[str]:
    """Обрезаем сырой текст для хранения до review."""
    if not text:
        return None
    text = str(text).strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def _seed_classes(session, json_path: Path):
    """classes.json -> school_classes."""
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    for c in raw["classes"]:
        pricing = c.get("pricing", {})
        obj = SchoolClass(
            id=c["id"],
            name=c.get("name", c["id"]),
            base_price=pricing.get("base_price", c.get("base_price", 0)),
            pricing_type=pricing.get("type", "fixed"),
            price_per_subject=pricing.get("price_per_subject"),
            subjects=c.get("subjects", []),
            exam_subjects=c.get("exam_subjects"),
        )
        session.merge(obj)
    session.flush()


def _seed_students(session, json_path: Path):
    """students.json -> students."""
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    students = raw if isinstance(raw, list) else raw.get("students", raw)
    for s in students:
        obj = Student(
            id=s["id"],
            fio=s["fio"],
            contract_number=s["contract_number"],
            class_id=s["class_id"],
            monthly_payment=s.get("monthly_payment", 0.0),
            compensation=s.get("compensation", ""),
        )
        session.merge(obj)
    session.flush()


def _seed_exam_choices(session, json_path: Path):
    """exam_choices.json -> exam_choices."""
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    choices = raw.get("exam_choices", raw)
    for ec in choices:
        obj = ExamChoice(
            student_id=ec["student_id"],
            selected_exams=ec["selected_exams"],
        )
        session.merge(obj)
    session.flush()


def _seed_partners(session, json_path: Path):
    """partners.json -> universities + programs + olympiads + benefits."""
    raw = json.loads(json_path.read_text(encoding="utf-8"))

    for uni_slug, uni_data in raw.items():
        progs = uni_data.get("programs", [])
        olymps = uni_data.get("olympiads", [])

        first = (progs[0] if progs else olymps[0]) if (progs or olymps) else {}
        uni_name = first.get("university_name", uni_slug)
        city = first.get("city", "")

        uni = University(slug=uni_slug, name=uni_name, city=city)
        session.add(uni)
        session.flush()

        seen_programs: dict = {}
        for p in progs:
            pname = _safe_str(p.get("program_name"))
            if not pname:
                continue
            okso = _safe_str(p.get("okso_code"))
            key = (pname, okso)
            if key in seen_programs:
                continue

            prog = Program(
                university_id=uni.id,
                program_name=pname,
                program_level=_safe_str(p.get("program_level")),
                okso_code=okso,
                min_score=_safe_str(p.get("min_score")),
                avg_score=_safe_str(p.get("avg_score")),
                budget_places=_safe_str(p.get("budget_places")),
                cost=_safe_str(p.get("cost")),
                ege_subjects=_safe_str(p.get("ege_subjects")),
                page_url=_safe_str(p.get("page_url")),
                source=_safe_str(p.get("source")),
                achievements_raw=_truncate_text(p.get("achievements"), 500),
                reviewed=False,
                timestamp=_safe_str(p.get("timestamp")),
            )
            session.add(prog)
            session.flush()
            seen_programs[key] = prog

        seen_olympiads: dict = {}
        for o in olymps:
            oname = _safe_str(o.get("olympiad_name"))
            if not oname:
                continue
            subj = _safe_str(o.get("subject"))
            oly_key = (oname, subj)

            if oly_key not in seen_olympiads:
                oly = Olympiad(
                    university_id=uni.id,
                    olympiad_name=oname,
                    olympiad_level=_safe_str(o.get("olympiad_level")),
                    subject=subj,
                    source_site=_safe_str(o.get("source_site")),
                    olympiad_url=_safe_str(o.get("olympiad_url")),
                    notes=_truncate_text(o.get("notes"), 1000),
                    benefit_detail_raw=_truncate_text(o.get("benefit_detail"), 500),
                    reviewed=False,
                    timestamp=_safe_str(o.get("timestamp")),
                )
                session.add(oly)
                session.flush()
                seen_olympiads[oly_key] = oly
            else:
                oly = seen_olympiads[oly_key]

            prog_name = _safe_str(o.get("program_name"))
            prog_okso = _safe_str(o.get("okso_code"))
            benefit_type = _safe_str(o.get("benefit_type"))

            target_prog = seen_programs.get((prog_name, prog_okso))
            if target_prog:
                link = OlympiadProgramBenefit(
                    olympiad_id=oly.id,
                    program_id=target_prog.id,
                    benefit_type=benefit_type,
                )
                session.add(link)

    session.flush()


def _seed_default_admin(session):
    """Создаём дефолтного admin-пользователя (admin / admin)."""
    from passlib.hash import bcrypt as passlib_bcrypt
    existing = session.query(User).filter_by(username="admin").first()
    if not existing:
        session.add(User(
            username="admin",
            hashed_password=passlib_bcrypt.hash("admin"),
            role="admin",
            full_name="Администратор",
        ))
        session.flush()


# ====================================================================
#  INIT / DROP
# ====================================================================

def init_db():
    """Создаёт таблицы и заливает seed-данные из JSON при первом запуске."""
    inspector = inspect(engine)
    tables_exist = inspector.has_table("students")

    Base.metadata.create_all(bind=engine)

    if tables_exist:
        return

    data_dir = Path(DATA_DIR)
    session = SessionLocal()
    try:
        def find_json(name):
            p = data_dir / name
            if p.exists():
                return p
            p2 = Path(BASE_DIR) / name
            if p2.exists():
                return p2
            return None

        classes_path = find_json("classes.json")
        students_path = find_json("students.json")
        exams_path = find_json("exam_choices.json")
        partners_path = find_json("partners.json")

        if classes_path:
            _seed_classes(session, classes_path)
            print("  ok classes.json -> school_classes")

        if students_path:
            _seed_students(session, students_path)
            print("  ok students.json -> students")

        if exams_path:
            _seed_exam_choices(session, exams_path)
            print("  ok exam_choices.json -> exam_choices")

        if partners_path:
            _seed_partners(session, partners_path)
            print("  ok partners.json -> universities / programs / olympiads")

        _seed_default_admin(session)
        print("  ok default admin user created")

        session.commit()
        print("\nDatabase initialized: data/school.db")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def drop_db():
    """Удалить все таблицы (для пересборки)."""
    Base.metadata.drop_all(bind=engine)