"""
Pydantic-схемы (request/response) для Биотех225 API.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ─────────────── Students ───────────────

class StudentCreate(BaseModel):
    fio: str = Field(..., min_length=1, max_length=300)
    contract_number: str = Field(..., min_length=1, max_length=50)
    class_id: str = Field(..., pattern=r"^(7|8|9|10|11)$")
    monthly_payment: float = Field(default=0.0, ge=0)
    compensation: str = Field(default="")


class StudentUpdate(BaseModel):
    fio: Optional[str] = None
    contract_number: Optional[str] = None
    class_id: Optional[str] = None
    monthly_payment: Optional[float] = None
    compensation: Optional[str] = None


class StudentOut(BaseModel):
    id: str
    fio: str
    contract_number: str
    class_id: str
    monthly_payment: float
    compensation: str

    model_config = {"from_attributes": True}


# ─────────────── Exam Choices ───────────────

class ExamChoiceCreate(BaseModel):
    student_id: str
    selected_exams: list[str]


class ExamChoiceOut(BaseModel):
    id: int
    student_id: str
    selected_exams: list[str]

    model_config = {"from_attributes": True}


# ─────────────── Classes ───────────────

class SchoolClassOut(BaseModel):
    id: str
    name: str
    base_price: float
    pricing_type: str
    price_per_subject: Optional[float]
    subjects: list[str]
    exam_subjects: Optional[list[str]]

    model_config = {"from_attributes": True}


class PriceCalcRequest(BaseModel):
    class_id: str
    selected_subjects: list[str] = []


class PriceCalcResponse(BaseModel):
    class_id: str
    pricing_type: str
    total: float
    detail: str


# ─────────────── Universities ───────────────

class UniversityOut(BaseModel):
    id: int
    slug: str
    name: str
    city: str

    model_config = {"from_attributes": True}


class ProgramOut(BaseModel):
    id: int
    university_id: int
    program_name: str
    program_level: Optional[str]
    okso_code: Optional[str]
    min_score: Optional[str]
    avg_score: Optional[str]
    budget_places: Optional[str]
    cost: Optional[str]
    ege_subjects: Optional[str]
    page_url: Optional[str]
    reviewed: bool

    model_config = {"from_attributes": True}


class OlympiadOut(BaseModel):
    id: int
    university_id: int
    olympiad_name: str
    olympiad_level: Optional[str]
    subject: Optional[str]
    olympiad_url: Optional[str]
    notes: Optional[str]
    reviewed: bool

    model_config = {"from_attributes": True}


class BenefitOut(BaseModel):
    id: int
    olympiad_id: int
    program_id: int
    benefit_type: Optional[str]

    model_config = {"from_attributes": True}


# ─────────────── Auth ───────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=3)
    role: str = Field(default="viewer", pattern=r"^(admin|manager|viewer)$")
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    full_name: Optional[str]

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
