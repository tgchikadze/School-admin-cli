"""
schemas.py - Pydantic-схемы для валидации запросов и ответов.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
#  P4: Вузы / Программы / Олимпиады
# ═══════════════════════════════════════════════════════════════

class UniversityBase(BaseModel):
    name: str
    city: str = "Санкт-Петербург"

class UniversityCreate(UniversityBase):
    pass

class UniversityOut(UniversityBase):
    id: int
    class Config:
        from_attributes = True


class ProgramBase(BaseModel):
    university_id: int
    okso_code: str | None = None
    program_name: str
    program_level: str | None = None
    min_score: int | None = None
    budget_places: int | None = None
    cost: float | None = None
    ege_subjects: str | None = None

class ProgramCreate(ProgramBase):
    pass

class ProgramOut(ProgramBase):
    id: int
    class Config:
        from_attributes = True


class OlympiadBase(BaseModel):
    university_id: int
    olympiad_name: str
    olympiad_level: str | None = None
    subject: str | None = None
    benefit_type: str | None = None
    benefit_detail: str | None = None
    source_url: str | None = None
    reviewed: bool = False


class OlympiadCreate(OlympiadBase):
    pass

class OlympiadOut(OlympiadBase):
    id: int
    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  P5: Пользователи
# ═══════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=4)
    full_name: str | None = None
    role: str = "manager"

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    full_name: str | None
    is_active: bool
    created_at: datetime | None = None
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


# ═══════════════════════════════════════════════════════════════
#  P5: Школьные классы
# ═══════════════════════════════════════════════════════════════

class SchoolClassCreate(BaseModel):
    name: str = Field(..., max_length=8)
    subjects: list[str] = []
    pricing_type: str = "fixed"
    base_price: float = 0.0
    price_per_subject: float = 0.0
    exam_subjects: list[str] = []

class SchoolClassOut(BaseModel):
    id: int
    name: str
    subjects: list[str]
    pricing_type: str
    base_price: float
    price_per_subject: float
    exam_subjects: list[str]
    class Config:
        from_attributes = True

class SchoolClassUpdate(BaseModel):
    name: str | None = None
    subjects: list[str] | None = None
    pricing_type: str | None = None
    base_price: float | None = None
    price_per_subject: float | None = None
    exam_subjects: list[str] | None = None


# ═══════════════════════════════════════════════════════════════
#  P5: Ученики
# ═══════════════════════════════════════════════════════════════

class StudentCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    class_id: int
    contract_number: str | None = None
    compensation: float = 0.0

class StudentOut(BaseModel):
    id: int
    full_name: str
    class_id: int
    contract_number: str | None
    monthly_payment: float
    compensation: float
    class Config:
        from_attributes = True

class StudentUpdate(BaseModel):
    full_name: str | None = None
    class_id: int | None = None
    contract_number: str | None = None
    compensation: float | None = None


# ═══════════════════════════════════════════════════════════════
#  P5: Выбор ЕГЭ (11 класс)
# ═══════════════════════════════════════════════════════════════

class ExamChoiceOut(BaseModel):
    id: int
    student_id: int
    subject_name: str
    class Config:
        from_attributes = True

class ExamChoiceBatch(BaseModel):
    student_id: int
    subjects: list[str]


# ═══════════════════════════════════════════════════════════════
#  P5: Квитанции
# ═══════════════════════════════════════════════════════════════

class ReceiptCreate(BaseModel):
    student_id: int

class ReceiptOut(BaseModel):
    id: int
    student_id: int
    created_by: int
    created_at: datetime | None
    amount: float
    pdf_path: str | None
    class Config:
        from_attributes = True

class ReceiptBatch(BaseModel):
    student_ids: list[int]