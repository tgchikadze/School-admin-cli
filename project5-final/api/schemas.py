from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    university_id: str
    okso_code: str
    program_name: str
    program_level: str
    min_score: str
    budget_places: str
    cost: str
    ege_subjects: str


class OlympiadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    university_id: str
    olympiad_name: str = ""
    olympiad_level: str = ""
    subject: str = ""
    benefit_type: str = ""
    benefit_detail: str = ""
    source_url: str = ""
    reviewed: bool = False


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



class UniversityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    city: str


class UniversityDetailOut(UniversityOut):
    programs: List[ProgramOut] = []
    olympiads: List[OlympiadOut] = []
