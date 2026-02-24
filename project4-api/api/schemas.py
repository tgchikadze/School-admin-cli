
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict




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
    olympiad_name: str = ""
    olympiad_level: str = ""       # ← было str без дефолта
    subject: str = ""
    benefit_type: str = ""
    benefit_detail: str = ""
    source_url: str = ""
    reviewed: bool = False

    model_config = ConfigDict(from_attributes=True)

class OlympiadUpdate(BaseModel):
    olympiad_name: str | None = None
    olympiad_level: str | None = None
    subject: str | None = None
    benefit_type: str | None = None
    benefit_detail: str | None = None
    source_url: str | None = None
    reviewed: bool | None = None

class OlympiadCreate(BaseModel):
    university_id: str
    olympiad_name: str = ""
    olympiad_level: str = ""
    subject: str = ""
    benefit_type: str = ""
    benefit_detail: str = ""
    source_url: str = ""
    notes: str = ""




class UniversityOut(BaseModel):
    id: str
    name: str
    city: str
    class Config:
        from_attributes = True


class UniversityDetailOut(UniversityOut):
    programs: List[ProgramOut] = []
    olympiads: List[OlympiadOut] = []
