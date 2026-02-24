"""
Admin endpoints: rebuild DB from partners.json, check status, clear.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.database import get_db, Base, engine, import_partners_json
from api.models import University, Program, Olympiad

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/status")
def db_status(db: Session = Depends(get_db)):
    """Текущее состояние БД."""
    return {
        "universities": db.query(University).count(),
        "programs": db.query(Program).count(),
        "olympiads": db.query(Olympiad).count(),
    }


@router.post("/rebuild")
def rebuild_db(db: Session = Depends(get_db)):
    """Удалить все данные и заново импортировать из partners.json."""
    # Очистить таблицы
    db.query(Olympiad).delete()
    db.query(Program).delete()
    db.query(University).delete()
    db.commit()
    db.close()

    # Импортировать заново
    import_partners_json(force=True)

    # Вернуть новый статус
    db2 = next(get_db())
    result = {
        "status": "ok",
        "universities": db2.query(University).count(),
        "programs": db2.query(Program).count(),
        "olympiads": db2.query(Olympiad).count(),
    }
    db2.close()
    return result


@router.post("/clear")
def clear_db(db: Session = Depends(get_db)):
    """Очистить все данные."""
    db.query(Olympiad).delete()
    db.query(Program).delete()
    db.query(University).delete()
    db.commit()
    return {"status": "cleared"}
