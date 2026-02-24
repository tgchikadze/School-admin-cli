
from typing import List, Optional
from pydantic import BaseModel, Field


class ProgramOut(BaseModel):
    id: int
    university_id: str
    okso_code: str
    program_name: str
    program_level: str
    min_score: str
    budget_places: str
    cost: str
    ege_subjects: str
    class Config:
        from_attributes = True


class OlympiadOut(BaseModel):
    id: int
    university_id: str
    olympiad_name: str
    olympiad_level: str
    subject: str
    benefit_type: str
    benefit_detail: str
    class Config:
        from_attributes = True


class UniversityOut(BaseModel):
    id: str
    name: str
    city: str
    class Config:
        from_attributes = True


class UniversityDetailOut(UniversityOut):
    programs: List[ProgramOut] = []
    olympiads: List[OlympiadOut] = []
