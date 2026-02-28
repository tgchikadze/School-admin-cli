"""database.py — Engine, SessionLocal, init_db + seed из classes.json."""

import os
import json
import csv
import re
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from .models import Base, SchoolClass

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATADIR = os.path.join(BASEDIR, "data")
os.makedirs(DATADIR, exist_ok=True)

# ── При тестировании используем in-memory SQLite с единым соединением ──
if os.environ.get("TESTING"):
    DATABASE_URL = "sqlite://"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
else:
    DATABASE_URL = f"sqlite:///{os.path.join(DATADIR, 'school.db')}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_classes(db: Session):
    """Если таблица school_classes пуста — заполняет из data/classes.json."""
    if db.query(SchoolClass).count() > 0:
        return
    print(f"[seed] BASEDIR={BASEDIR} DATADIR={DATADIR}")
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


def import_partners_json(db: Session | None = None) -> dict:
    """
    Импортирует данные из data/partners.json в таблицы
    universities, programs, olympiads.
    """
    from .models import University, Program, Olympiad

    json_path = os.path.join(DATADIR, "partners.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"partners.json не найден: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        stats = {"universities": 0, "programs": 0, "olympiads": 0}

        for uni_key, uni_data in data.items():
            if not isinstance(uni_data, dict):
                continue

            programs_list = uni_data.get("programs", [])
            olympiads_list = uni_data.get("olympiad_benefits", uni_data.get("olympiads", []))

            uni_name = None
            uni_city = "Санкт-Петербург"

            for p in programs_list:
                name = p.get("university_name", "").strip()
                if name:
                    uni_name = name
                    uni_city = p.get("city", uni_city).strip() or uni_city
                    break

            if not uni_name:
                for o in olympiads_list:
                    name = o.get("university_name", "").strip()
                    if name:
                        uni_name = name
                        uni_city = o.get("city", uni_city).strip() or uni_city
                        break

            if not uni_name:
                uni_name = uni_key

            uni = db.query(University).filter(University.name == uni_name).first()
            if not uni:
                uni = University(name=uni_name, city=uni_city)
                db.add(uni)
                db.flush()
                stats["universities"] += 1

            for p in programs_list:
                prog_name = (p.get("program_name") or "").strip()
                if not prog_name:
                    continue

                prog = Program(
                    university_id=uni.id,
                    okso_code=(p.get("okso_code") or "").strip(),
                    program_name=prog_name,
                    program_level=(p.get("program_level") or "").strip(),
                    min_score=_safe_int(p.get("min_score")),
                    budget_places=_safe_int(p.get("budget_places")),
                    cost=_safe_float(p.get("cost")),
                    ege_subjects=(p.get("ege_subjects") or "").strip(),
                )
                db.add(prog)
                stats["programs"] += 1

            for o in olympiads_list:
                oly_name = (o.get("olympiad_name") or o.get("name") or "").strip()
                if not oly_name:
                    continue

                oly = Olympiad(
                    university_id=uni.id,
                    olympiad_name=oly_name,
                    olympiad_level=_safe_int(o.get("olympiad_level") or o.get("level")),
                    subject=(o.get("subject") or "").strip(),
                    benefit_type=(o.get("benefit_type") or "").strip(),
                    benefit_detail=(o.get("benefit_detail") or o.get("detail") or "").strip(),
                    source_url=(o.get("source_url") or o.get("url") or "").strip(),
                    reviewed=bool(o.get("reviewed", False)),
                )
                db.add(oly)
                stats["olympiads"] += 1

        db.commit()
        return stats

    except Exception:
        db.rollback()
        raise
    finally:
        if close_after:
            db.close()


def _normalize_name(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r'[«»"\'\.]+', "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _find_university(db, uni_key: str, uni_name: str):
    from .models import University

    uni = db.query(University).filter(University.name == uni_name).first()
    if uni:
        return uni

    norm_target = _normalize_name(uni_name)
    if norm_target:
        for u in db.query(University).all():
            if _normalize_name(u.name) == norm_target:
                return u

    norm_key = _normalize_name(uni_key)
    if norm_key:
        for u in db.query(University).all():
            if norm_key in _normalize_name(u.name):
                return u

    return None


def _olympiad_signature(uni_id: int, name: str, subject: str,
                        benefit_type: str, program_name: str) -> str:
    parts = [
        str(uni_id),
        _normalize_name(name),
        _normalize_name(subject),
        _normalize_name(benefit_type),
        _normalize_name(program_name),
    ]
    return "|".join(parts)


def import_olympiads_csv(db: Session | None = None) -> dict:
    """
    Черновой импорт олимпиад из data/olympiads_raw.csv.
    """
    from .models import University, Olympiad

    csv_path = os.path.join(DATADIR, "olympiads_raw.csv")
    if not os.path.exists(csv_path):
        return {"error": "olympiads_raw.csv not found", "path": csv_path}

    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        existing_sigs = set()
        for o in db.query(Olympiad).all():
            sig = _olympiad_signature(
                o.university_id,
                o.olympiad_name or "",
                o.subject or "",
                o.benefit_type or "",
                ""
            )
            existing_sigs.add(sig)

        stats = {
            "total": 0,
            "created": 0,
            "skipped_noname": 0,
            "skipped_nouni": 0,
            "skipped_dup": 0,
            "new_universities": 0,
        }

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total"] += 1

                raw_name = (row.get("olympiad_name") or "").strip()
                if not raw_name or raw_name.lower() == "nan":
                    stats["skipped_noname"] += 1
                    continue

                uni_key = (row.get("university_id") or "").strip()
                uni_name_csv = (row.get("university_name") or "").strip()
                if uni_name_csv.lower() == "nan":
                    uni_name_csv = ""

                uni = _find_university(db, uni_key, uni_name_csv)

                if not uni:
                    display_name = uni_name_csv or uni_key
                    city = (row.get("city") or "").strip()
                    city = {"spb": "Санкт-Петербург", "msk": "Москва"}.get(
                        city.lower(), city
                    ) or "нет данных"

                    uni = University(name=display_name, city=city)
                    db.add(uni)
                    db.flush()
                    stats["new_universities"] += 1

                subject = (row.get("subject") or "").strip()
                if subject.lower() == "nan":
                    subject = ""

                benefit_type = (row.get("benefit_type") or "").strip()
                if benefit_type.lower() == "nan":
                    benefit_type = ""
                benefit_type = "; ".join(
                    s.strip() for s in benefit_type.replace(";", ";").split(";")
                    if s.strip() and s.strip().lower() != "nan"
                )

                level_raw = (row.get("olympiad_level") or "").strip()
                level = _safe_int(level_raw) if level_raw.lower() != "nan" else None

                benefit_detail = (row.get("benefit_detail") or "").strip()
                if benefit_detail.lower() == "nan":
                    benefit_detail = ""
                if len(benefit_detail) > 500:
                    benefit_detail = benefit_detail[:500] + "…"

                notes = (row.get("notes") or "").strip()
                if notes.lower() == "nan":
                    notes = ""

                source_url = (row.get("olympiad_url") or "").strip()
                if source_url.lower() == "nan":
                    source_url = ""

                program_name = (row.get("program_name") or "").strip()
                if program_name.lower() == "nan":
                    program_name = ""

                sig = _olympiad_signature(
                    uni.id, raw_name, subject, benefit_type, ""
                )
                if sig in existing_sigs:
                    stats["skipped_dup"] += 1
                    continue
                existing_sigs.add(sig)

                combined_detail = ""
                if notes:
                    combined_detail = notes
                if benefit_detail and benefit_detail != notes:
                    if combined_detail:
                        combined_detail += " | "
                    combined_detail += benefit_detail

                o = Olympiad(
                    university_id=uni.id,
                    olympiad_name=raw_name,
                    olympiad_level=level,
                    subject=subject,
                    benefit_type=benefit_type,
                    benefit_detail=combined_detail[:1000] if combined_detail else "",
                    source_url=source_url,
                    reviewed=False,
                )
                db.add(o)
                stats["created"] += 1

        db.commit()
        return stats

    except Exception:
        db.rollback()
        raise
    finally:
        if close_after:
            db.close()


def _safe_int(val) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(" ", "").replace(",", "."))
    except (ValueError, TypeError):
        return None
