"""
routers/programs.py - CRUD образовательных программ. Доступ: все авторизованные.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_any
from ..models import Program, University, User
from ..schemas import ProgramCreate, ProgramOut

router = APIRouter(tags=["programs"])


@router.get("/api/programs", response_model=list[ProgramOut])
def list_programs(
    university_id: int | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_any),
):
    q = db.query(Program)
    if university_id:
        q = q.filter(Program.university_id == university_id)
    if search:
        q = q.filter(Program.program_name.ilike(f"%{search}%"))
    return q.order_by(Program.program_name).offset(skip).limit(limit).all()


@router.get("/api/programs/{prog_id}", response_model=ProgramOut)
def get_program(prog_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_any)):
    prog = db.query(Program).get(prog_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    return prog


@router.post("/api/programs", response_model=ProgramOut, status_code=201)
def create_program(data: ProgramCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_any)):
    if not db.query(University).get(data.university_id):
        raise HTTPException(status_code=404, detail="University not found")
    prog = Program(**data.model_dump())
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return prog


@router.put("/api/programs/{prog_id}", response_model=ProgramOut)
def update_program(prog_id: int, data: ProgramCreate,
                   db: Session = Depends(get_db), user: User = Depends(require_any)):
    prog = db.query(Program).get(prog_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    for key, value in data.model_dump().items():
        setattr(prog, key, value)
    db.commit()
    db.refresh(prog)
    return prog


@router.delete("/api/programs/{prog_id}")
def delete_program(prog_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_any)):
    prog = db.query(Program).get(prog_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    db.delete(prog)
    db.commit()
    return {"detail": "Program deleted"}
