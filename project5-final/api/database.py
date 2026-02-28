"""database.py — Engine, SessionLocal, init_db + seed из classes.json."""

import os
import json
import csv
import re
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

def _normalize_name(s: str) -> str:
    """
    Приводит строку к каноническому виду для сравнения:
    lowercase, убираем лишние пробелы, «ё»→«е», убираем кавычки и точки.
    """
    if not s:
        return ""
    s = s.strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r"[«»\"'\.]+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _find_university(db, uni_key: str, uni_name: str):
    """
    Ищет вуз в БД по точному имени → по нормализованному имени → по uni_key.
    Возвращает University или None.
    """
    from .models import University

    # 1) Точное совпадение по name
    uni = db.query(University).filter(University.name == uni_name).first()
    if uni:
        return uni

    # 2) Нормализованное сравнение по всем вузам в БД
    norm_target = _normalize_name(uni_name)
    if norm_target:
        for u in db.query(University).all():
            if _normalize_name(u.name) == norm_target:
                return u

    # 3) Поиск по подстроке uni_key в name (напр. "ИТМО" содержит "итмо")
    norm_key = _normalize_name(uni_key)
    if norm_key:
        for u in db.query(University).all():
            if norm_key in _normalize_name(u.name):
                return u

    return None

def _olympiad_signature(uni_id: int, name: str, subject: str,
                        benefit_type: str, program_name: str) -> str:
    """
    Уникальная сигнатура олимпиадной записи для проверки дубликатов.
    Одна и та же олимпиада + предмет + тип льготы + программа = дубль.
    """
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

    - Нормализует названия для предотвращения дубликатов
    - Маппит university_id из CSV → University в БД
    - Создаёт Olympiad(reviewed=False)
    - Идемпотентен: повторный вызов НЕ создаёт дубли

    Возвращает: {created, skipped_noname, skipped_nouni, skipped_dup, total}
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
        # Собираем существующие сигнатуры из БД
        existing_sigs = set()
        for o in db.query(Olympiad).all():
            sig = _olympiad_signature(
                o.university_id,
                o.olympiad_name or "",
                o.subject or "",
                o.benefit_type or "",
                ""  # program_name нет в модели — пока без неё
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

                # --- Фильтр: пустое имя олимпиады ---
                raw_name = (row.get("olympiad_name") or "").strip()
                if not raw_name or raw_name.lower() == "nan":
                    stats["skipped_noname"] += 1
                    continue

                # --- Маппинг вуза ---
                uni_key = (row.get("university_id") or "").strip()
                uni_name_csv = (row.get("university_name") or "").strip()
                if uni_name_csv.lower() == "nan":
                    uni_name_csv = ""

                uni = _find_university(db, uni_key, uni_name_csv)

                if not uni:
                    # Создаём новый вуз с пометкой
                    display_name = uni_name_csv or uni_key
                    city = (row.get("city") or "").strip()
                    city = {"spb": "Санкт-Петербург", "msk": "Москва"}.get(
                        city.lower(), city
                    ) or "нет данных"

                    uni = University(name=display_name, city=city)
                    db.add(uni)
                    db.flush()  # получаем uni.id
                    stats["new_universities"] += 1

                # --- Нормализация полей ---
                subject = (row.get("subject") or "").strip()
                if subject.lower() == "nan":
                    subject = ""

                benefit_type = (row.get("benefit_type") or "").strip()
                if benefit_type.lower() == "nan":
                    benefit_type = ""
                # Нормализуем разделитель: "БВИ;100 баллов" → "БВИ; 100 баллов"
                benefit_type = "; ".join(
                    s.strip() for s in benefit_type.replace(";", ";").split(";")
                    if s.strip() and s.strip().lower() != "nan"
                )

                level_raw = (row.get("olympiad_level") or "").strip()
                level = _safe_int(level_raw) if level_raw.lower() != "nan" else None

                benefit_detail = (row.get("benefit_detail") or "").strip()
                if benefit_detail.lower() == "nan":
                    benefit_detail = ""
                # Обрезаем мусорные длинные тексты (HTML-дампы)
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

                # --- Дедупликация ---
                sig = _olympiad_signature(
                    uni.id, raw_name, subject, benefit_type, ""
                )
                if sig in existing_sigs:
                    stats["skipped_dup"] += 1
                    continue
                existing_sigs.add(sig)

                # --- Формируем benefit_detail из notes + detail ---
                combined_detail = ""
                if notes:
                    combined_detail = notes
                if benefit_detail and benefit_detail != notes:
                    if combined_detail:
                        combined_detail += " | "
                    combined_detail += benefit_detail

                # --- Создаём запись ---
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
