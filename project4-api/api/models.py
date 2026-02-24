from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from api.database import Base


class University(Base):
    __tablename__ = "universities"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, default="")

    programs = relationship("Program", back_populates="university")
    olympiads = relationship("Olympiad", back_populates="university")


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    university_id = Column(String, ForeignKey("universities.id"))
    okso_code = Column(String, default="")
    program_name = Column(String, default="")
    program_level = Column(String, default="")
    min_score = Column(String, default="")
    avg_score = Column(String, default="")
    budget_places = Column(String, default="")
    cost = Column(String, default="")
    ege_subjects = Column(String, default="")
    achievements = Column(String, default="")
    source = Column(String, default="")
    page_url = Column(String, default="")

    university = relationship("University", back_populates="programs")


class Olympiad(Base):
    __tablename__ = "olympiads"

    id = Column(Integer, primary_key=True, autoincrement=True)
    university_id = Column(String, ForeignKey("universities.id"))
    olympiad_name = Column(String, default="")
    olympiad_level = Column(String, default="")
    subject = Column(String, default="")
    benefit_type = Column(String, default="")
    benefit_detail = Column(String, default="")
    source_url = Column(String, default="")
    reviewed = Column(Boolean, default=False)

    university = relationship("University", back_populates="olympiads")
