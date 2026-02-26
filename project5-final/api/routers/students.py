"""
routers/students.py — CRUD учеников, 1-в-1 повторяет API-контракт student_db.py.

Эндпоинты:
  GET    /api/students          — список всех учеников (+ ?search=… &class_id=…)
  GET    /api/students/{id}     — получить ученика по ID
  POST   /api/students          — добавить ученика
  PUT    /api/students/{id}     — обновить ученика
  DELETE /api/students/{id}     — удалить ученика
  DELETE /api/students          — очистить всю базу учеников
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from api.database import get_db
from api.models import Student, ExamChoice, SchoolClass
from api.schemas import StudentCreate, StudentUpdate, StudentOut

router = APIRouter(prefix="/api/students", tags=["students"])


def _next_student_id(db: Session) -> str:
    """Генерация следующего ID в формате '001', '002', …"""
    last = db.query(Student).order_by(Student.id.desc()).first()
    if last:
        return f"{int(last.id) + 1:03d}"
    return "001"


def _calculate_payment(db: Session, class_id: str, selected_exams: list[str] | None = None) -> float:
    """Рассчитать ежемесячную оплату по классу и выбранным предметам."""
    sc = db.query(SchoolClass).filter_by(id=class_id).first()
    if not sc:
        return 0.0
    if sc.pricing_type == "per_subject" and selected_exams:
        return len(selected_exams) * (sc.price_per_subject or 3000)
    return sc.base_price


@router.get("", response_model=list[StudentOut])
def list_students(
    search: Optional[str] = Query(None, description="Поиск по ФИО"),
    class_id: Optional[str] = Query(None, description="Фильтр по классу"),
    db: Session = Depends(get_db),
):
    """Список всех учеников с опциональной фильтрацией."""
    q = db.query(Student)
    if search:
        q = q.filter(Student.fio.ilike(f"%{search}%"))
    if class_id:
        q = q.filter(Student.class_id == class_id)
    return q.order_by(Student.id).all()


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: str, db: Session = Depends(get_db)):
    """Получить ученика по ID."""
    student = db.query(Student).filter_by(id=student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")
    return student


@router.post("", response_model=StudentOut, status_code=201)
def create_student(data: StudentCreate, db: Session = Depends(get_db)):
    """Добавить ученика (дубликаты по ФИО или договору запрещены)."""
    # Проверка дубликатов
    dup = db.query(Student).filter(
        (Student.fio == data.fio) | (Student.contract_number == data.contract_number)
    ).first()
    if dup:
        raise HTTPException(
            status_code=409,
            detail="Ученик с таким ФИО или номером договора уже существует",
        )

    # Проверка класса
    sc = db.query(SchoolClass).filter_by(id=data.class_id).first()
    if not sc:
        raise HTTPException(status_code=400, detail=f"Класс {data.class_id} не найден")

    # Авто-расчёт оплаты для не-11 классов
    payment = data.monthly_payment
    if sc.pricing_type == "fixed" and payment == 0:
        payment = sc.base_price

    student = Student(
        id=_next_student_id(db),
        fio=data.fio,
        contract_number=data.contract_number,
        class_id=data.class_id,
        monthly_payment=payment,
        compensation=data.compensation,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.put("/{student_id}", response_model=StudentOut)
def update_student(student_id: str, data: StudentUpdate, db: Session = Depends(get_db)):
    """Обновить данные ученика (частичное обновление)."""
    student = db.query(Student).filter_by(id=student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")

    # Проверка дубликатов при смене ФИО / договора
    if data.fio or data.contract_number:
        check_fio = data.fio or student.fio
        check_contract = data.contract_number or student.contract_number
        dup = db.query(Student).filter(
            Student.id != student_id,
            (Student.fio == check_fio) | (Student.contract_number == check_contract),
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail="Дубликат ФИО или договора")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}")
def delete_student(student_id: str, db: Session = Depends(get_db)):
    """Удалить ученика (каскадно удалит exam_choices)."""
    student = db.query(Student).filter_by(id=student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")
    db.delete(student)
    db.commit()
    return {"detail": f"Ученик {student_id} удалён"}


@router.delete("")
def clear_all_students(db: Session = Depends(get_db)):
    """Очистить всю базу учеников (и связанные exam_choices)."""
    count = db.query(Student).count()
    db.query(ExamChoice).delete()
    db.query(Student).delete()
    db.commit()
    return {"detail": f"Удалено {count} учеников"}
