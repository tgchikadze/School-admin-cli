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


# ─── Добавить в конец database.py (перед drop_db) ───────────


# ═══════════════════════════════════════════════════════════════
# ЗАМЕНИ функцию import_partners_json() в database.py ЦЕЛИКОМ:
# ═══════════════════════════════════════════════════════════════

def import_partners_json(db: Session | None = None) -> dict:
    """
    Импортирует данные из data/partners.json в таблицы
    universities, programs, olympiads.

    Формат JSON (из P3 scraper):
    {
      "spbau": {
        "programs": [{"university_name": "АУ РАН", "city": "...", "program_name": "...", ...}],
        "olympiad_benefits": [{"olympiad_name": "...", ...}]
      },
      "itmo": { ... },
      ...
    }
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

        # Формат: {uni_key: {"programs": [...], "olympiad_benefits": [...]}}
        for uni_key, uni_data in data.items():
            if not isinstance(uni_data, dict):
                continue

            programs_list = uni_data.get("programs", [])
            olympiads_list = uni_data.get("olympiad_benefits", uni_data.get("olympiads", []))

            # Определяем название вуза из первой программы или олимпиады
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
                uni_name = uni_key  # fallback — используем ключ

            # Создаём/находим вуз
            uni = db.query(University).filter(University.name == uni_name).first()
            if not uni:
                uni = University(name=uni_name, city=uni_city)
                db.add(uni)
                db.flush()
                stats["universities"] += 1

            # Импорт программ
            for p in programs_list:
                prog_name = (p.get("program_name") or "").strip()
                if not prog_name:
                    continue  # пропускаем пустые

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

            # Импорт олимпиад
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


def _safe_int(val) -> int | None:
    """Безопасное преобразование в int (пустые строки → None)."""
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    """Безопасное преобразование в float (пустые строки → None)."""
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(" ", "").replace(",", "."))
    except (ValueError, TypeError):
        return None
