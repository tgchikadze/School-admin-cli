"""
routers/students.py - CRUD учеников, школьных классов и выбора ЕГЭ.
Доступ: admin + manager (require_manager).
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_manager
from ..models import Student, SchoolClass, ExamChoice, User
from ..schemas import (
    StudentCreate, StudentUpdate, StudentOut,
    SchoolClassCreate, SchoolClassUpdate, SchoolClassOut,
    ExamChoiceOut, ExamChoiceBatch,
)

router = APIRouter(tags=["students"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "web", "templates"))


# ═══════════════════════════════════════════════════════════════
#  Расчёт ежемесячного платежа
# ═══════════════════════════════════════════════════════════════

def _recalc_payment(student: Student, db: Session) -> float:
    """
    Пересчитать monthly_payment ученика.
      7-10 (fixed):       base_price
      11   (per_subject): кол-во ЕГЭ * price_per_subject
    """
    sc = db.query(SchoolClass).get(student.class_id)
    if not sc:
        return 0.0
    if sc.pricing_type == "per_subject":
        exam_count = (
            db.query(ExamChoice)
            .filter(ExamChoice.student_id == student.id)
            .count()
        )
        return exam_count * sc.price_per_subject
    return sc.base_price


# ═══════════════════════════════════════════════════════════════
#  HTML-страница
# ═══════════════════════════════════════════════════════════════

@router.get("/students", response_class=HTMLResponse)
def students_page(request: Request, user: User = Depends(require_manager)):
    return templates.TemplateResponse("students.html", {
        "request": request, "role": user.role, "username": user.username,
    })


# ═══════════════════════════════════════════════════════════════
#  SCHOOL CLASSES
# ═══════════════════════════════════════════════════════════════

@router.get("/api/classes", response_model=list[SchoolClassOut])
def list_classes(db: Session = Depends(get_db), user: User = Depends(require_manager)):
    return db.query(SchoolClass).order_by(SchoolClass.name).all()


@router.post("/api/classes", response_model=SchoolClassOut, status_code=201)
def create_class(data: SchoolClassCreate, db: Session = Depends(get_db),
                 user: User = Depends(require_manager)):
    existing = db.query(SchoolClass).filter(SchoolClass.name == data.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Class \'{data.name}\' already exists")

    school_class = SchoolClass(
        name=data.name, subjects=data.subjects, pricing_type=data.pricing_type,
        base_price=data.base_price, price_per_subject=data.price_per_subject,
        exam_subjects=data.exam_subjects,
    )
    db.add(school_class)
    db.commit()
    db.refresh(school_class)
    return school_class


@router.put("/api/classes/{class_id}", response_model=SchoolClassOut)
def update_class(class_id: int, data: SchoolClassUpdate,
                 db: Session = Depends(get_db), user: User = Depends(require_manager)):
    school_class = db.query(SchoolClass).get(class_id)
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    for field in ("name", "subjects", "pricing_type", "base_price",
                  "price_per_subject", "exam_subjects"):
        value = getattr(data, field)
        if value is not None:
            setattr(school_class, field, value)

    db.commit()
    db.refresh(school_class)

    # Пересчитать платежи всех учеников этого класса
    for student in school_class.students:
        student.monthly_payment = _recalc_payment(student, db)
    db.commit()

    return school_class


@router.delete("/api/classes/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_manager)):
    school_class = db.query(SchoolClass).get(class_id)
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    student_count = db.query(Student).filter(Student.class_id == class_id).count()
    if student_count > 0:
        raise HTTPException(status_code=409,
                            detail=f"Cannot delete: {student_count} students in this class")

    db.delete(school_class)
    db.commit()
    return {"detail": "Class deleted"}


# ═══════════════════════════════════════════════════════════════
#  STUDENTS
# ═══════════════════════════════════════════════════════════════

@router.get("/api/students", response_model=list[StudentOut])
def list_students(class_id: int | None = None, search: str | None = None,
                  db: Session = Depends(get_db), user: User = Depends(require_manager)):
    q = db.query(Student)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    if search:
        q = q.filter(Student.full_name.ilike(f"%{search}%"))
    return q.order_by(Student.full_name).all()


@router.post("/api/students", response_model=StudentOut, status_code=201)
def create_student(data: StudentCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_manager)):
    school_class = db.query(SchoolClass).get(data.class_id)
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    if data.contract_number:
        existing = db.query(Student).filter(
            Student.contract_number == data.contract_number
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Contract number already exists")

    student = Student(
        full_name=data.full_name, class_id=data.class_id,
        contract_number=data.contract_number, compensation=data.compensation,
    )
    db.add(student)
    db.flush()

    student.monthly_payment = _recalc_payment(student, db)
    db.commit()
    db.refresh(student)
    return student


@router.get("/api/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_manager)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.put("/api/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, data: StudentUpdate, db: Session = Depends(get_db),
                   user: User = Depends(require_manager)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if data.full_name is not None:
        student.full_name = data.full_name
    if data.class_id is not None:
        if not db.query(SchoolClass).get(data.class_id):
            raise HTTPException(status_code=404, detail="Class not found")
        student.class_id = data.class_id
    if data.contract_number is not None:
        student.contract_number = data.contract_number
    if data.compensation is not None:
        student.compensation = data.compensation

    student.monthly_payment = _recalc_payment(student, db)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/api/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db),
                   user: User = Depends(require_manager)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return {"detail": "Student deleted"}


# ═══════════════════════════════════════════════════════════════
#  EXAM CHOICES (ЕГЭ, 11 класс)
# ═══════════════════════════════════════════════════════════════

@router.get("/api/students/{student_id}/exams", response_model=list[ExamChoiceOut])
def list_exams(student_id: int, db: Session = Depends(get_db),
               user: User = Depends(require_manager)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student.exam_choices


@router.post("/api/students/{student_id}/exams", response_model=list[ExamChoiceOut])
def set_exams_batch(student_id: int, data: ExamChoiceBatch,
                    db: Session = Depends(get_db), user: User = Depends(require_manager)):
    """Пакетное назначение предметов ЕГЭ (заменяет все текущие)."""
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.query(ExamChoice).filter(ExamChoice.student_id == student_id).delete()

    choices = []
    for subj_name in data.subjects:
        choice = ExamChoice(student_id=student_id, subject_name=subj_name)
        db.add(choice)
        choices.append(choice)

    db.flush()
    student.monthly_payment = _recalc_payment(student, db)
    db.commit()

    for c in choices:
        db.refresh(c)
    return choices


@router.delete("/api/students/{student_id}/exams/{exam_id}")
def delete_exam(student_id: int, exam_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_manager)):
    choice = db.query(ExamChoice).filter(
        ExamChoice.id == exam_id, ExamChoice.student_id == student_id,
    ).first()
    if not choice:
        raise HTTPException(status_code=404, detail="Exam choice not found")

    db.delete(choice)
    db.flush()

    student = db.query(Student).get(student_id)
    student.monthly_payment = _recalc_payment(student, db)
    db.commit()
    return {"detail": "Exam choice deleted"}
