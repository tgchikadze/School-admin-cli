"""
schemas.py - Pydantic-схемы для валидации запросов и ответов.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════
#  P4: Вузы / Программы / Олимпиады
# ═══════════════════════════════════════════════════════════════

# ─── University ───────────────────────────────────────────────
class UniversityBase(BaseModel):
    name: str
    city: str = "Санкт-Петербург"

class UniversityCreate(UniversityBase):
    pass

class UniversityOut(UniversityBase):
    id: int
    class Config:
        from_attributes = True


# ─── Program ─────────────────────────────────────────────────
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


# ─── Olympiad ────────────────────────────────────────────────
class OlympiadBase(BaseModel):
    university_id: int
    olympiad_name: str
    olympiad_level: int | None = None
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
    role: str = "manager"  # admin / manager / viewer

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

class SubjectPrice(BaseModel):
    """Предмет с ценой (элемент JSON-списка в SchoolClass.subjects)."""
    name: str
    price: float

class SchoolClassCreate(BaseModel):
    name: str = Field(..., max_length=8)          # "7", "8БТ", "10МИ"
    profile: str | None = None                     # "БТ", "МИ"
    subjects: list[SubjectPrice] = []

class SchoolClassOut(BaseModel):
    id: int
    name: str
    profile: str | None
    subjects: list[SubjectPrice] = []
    class Config:
        from_attributes = True

class SchoolClassUpdate(BaseModel):
    name: str | None = None
    profile: str | None = None
    subjects: list[SubjectPrice] | None = None


# ═══════════════════════════════════════════════════════════════
#  P5: Ученики
# ═══════════════════════════════════════════════════════════════

class StudentCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    class_id: int
    contract_number: str | None = None
    compensation: float = 0.0
    subjects: list[str] = []                      # ["Химия", "Биология"]

class StudentOut(BaseModel):
    id: int
    full_name: str
    class_id: int
    contract_number: str | None
    compensation: float
    subjects: list[str]
    total_cost: float
    class Config:
        from_attributes = True

class StudentUpdate(BaseModel):
    full_name: str | None = None
    class_id: int | None = None
    contract_number: str | None = None
    compensation: float | None = None
    subjects: list[str] | None = None


# ═══════════════════════════════════════════════════════════════
#  P5: Выбор ЕГЭ (11 класс)
# ═══════════════════════════════════════════════════════════════

class ExamChoiceCreate(BaseModel):
    student_id: int
    subject_name: str
    price: float = 3000.0

class ExamChoiceOut(BaseModel):
    id: int
    student_id: int
    subject_name: str
    price: float
    class Config:
        from_attributes = True

class ExamChoiceBatch(BaseModel):
    """Пакетное назначение предметов ЕГЭ ученику."""
    student_id: int
    subjects: list[str]                           # ["Химия", "Биология"]
    price_per_subject: float = 3000.0


# ═══════════════════════════════════════════════════════════════
#  P5: Квитанции
# ═══════════════════════════════════════════════════════════════

class ReceiptCreate(BaseModel):
    student_id: int
    subjects: list[SubjectPrice] = []             # [{"name": "Химия", "price": 5000}]

class ReceiptOut(BaseModel):
    id: int
    student_id: int
    created_by: int
    created_at: datetime | None
    subjects: list[SubjectPrice] = []
    total: float
    pdf_path: str | None
    class Config:
        from_attributes = True

class ReceiptBatch(BaseModel):
    """Массовая генерация квитанций для списка учеников."""
    student_ids: list[int]
