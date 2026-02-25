"""
models.py - ORM-модели для Project 5 "Биотех225".
SQLAlchemy 2.0, SQLite.
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, JSON,
    ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ───────────────────────── P4: Вузы / Программы / Олимпиады ─────────────────

class University(Base):
    """Вуз-партнёр."""
    __tablename__ = "universities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False, unique=True)
    city = Column(String(128), nullable=False, default="Санкт-Петербург")

    programs = relationship("Program", back_populates="university",
                            cascade="all, delete-orphan")
    olympiads = relationship("Olympiad", back_populates="university",
                             cascade="all, delete-orphan")

    def __repr__(self):
        return f"<University {self.id}: {self.name}>"


class Program(Base):
    """Образовательная программа вуза."""
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False)

    okso_code = Column(String(32))
    program_name = Column(String(512), nullable=False)
    program_level = Column(String(64))
    min_score = Column(Integer)
    budget_places = Column(Integer)
    cost = Column(Float)
    ege_subjects = Column(Text)

    university = relationship("University", back_populates="programs")

    def __repr__(self):
        return f"<Program {self.id}: {self.program_name}>"


class Olympiad(Base):
    """Олимпиадная льгота."""
    __tablename__ = "olympiads"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False)

    olympiad_name = Column(String(256), nullable=False)
    olympiad_level = Column(Integer)
    subject = Column(String(128))
    benefit_type = Column(String(128))
    benefit_detail = Column(Text)
    source_url = Column(String(512))
    reviewed = Column(Boolean, default=False)

    university = relationship("University", back_populates="olympiads")

    def __repr__(self):
        return f"<Olympiad {self.id}: {self.olympiad_name}>"


# ───────────────────────── P5: Пользователи / Авторизация ───────────────────

class User(Base):
    """Пользователь системы (техадмин / завуч / директор)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(16), nullable=False, default="manager")
    full_name = Column(String(256))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    receipts_created = relationship("Receipt", back_populates="created_by_user")

    def __repr__(self):
        return f"<User {self.id}: {self.username} ({self.role})>"


# ───────────────────────── P5: Школьные классы ──────────────────────────────

class SchoolClass(Base):
    """
    Школьный класс (7, 8, 9, 10, 11).

    Два типа ценообразования (pricing_type):
      "fixed"       — классы 7-10: фиксированная стоимость base_price,
                      фиксированный набор предметов.
      "per_subject" — класс 11: кол-во_ЕГЭ × price_per_subject,
                      ученик выбирает предметы ЕГЭ из exam_subjects.
    """
    __tablename__ = "school_classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(8), unique=True, nullable=False)

    subjects = Column(JSON, nullable=False, default=list)
    # ["Химия", "Биология", ...] — предметы класса

    pricing_type = Column(String(16), nullable=False, default="fixed")
    # "fixed" или "per_subject"

    base_price = Column(Float, nullable=False, default=0.0)
    # fixed: полная ежемесячная стоимость

    price_per_subject = Column(Float, default=0.0)
    # per_subject: цена за 1 выбранный предмет ЕГЭ (3000)

    exam_subjects = Column(JSON, default=list)
    # per_subject: список доступных предметов ЕГЭ для выбора

    students = relationship("Student", back_populates="school_class")

    def __repr__(self):
        return f"<SchoolClass {self.id}: {self.name}>"


# ───────────────────────── P5: Ученики ──────────────────────────────────────

class Student(Base):
    """Ученик профильной школы «Биотех225»."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(256), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    contract_number = Column(String(64), unique=True)

    monthly_payment = Column(Float, default=0.0)
    # Рассчитывается автоматически:
    #   fixed:       base_price
    #   per_subject: len(exam_choices) * price_per_subject

    compensation = Column(Float, default=0.0)
    # Баланс задолженности: >0 школа должна ученику, <0 ученик должен школе

    school_class = relationship("SchoolClass", back_populates="students")
    exam_choices = relationship("ExamChoice", back_populates="student",
                                cascade="all, delete-orphan")
    receipts = relationship("Receipt", back_populates="student",
                            cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student {self.id}: {self.full_name}>"


# ───────────────────────── P5: Выбор ЕГЭ (11 класс) ────────────────────────

class ExamChoice(Base):
    """Предмет ЕГЭ, выбранный учеником 11 класса."""
    __tablename__ = "exam_choices"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_name = Column(String(128), nullable=False)

    student = relationship("Student", back_populates="exam_choices")

    __table_args__ = (
        UniqueConstraint("student_id", "subject_name",
                         name="uq_student_exam_subject"),
    )

    def __repr__(self):
        return f"<ExamChoice {self.id}: student={self.student_id} {self.subject_name}>"


# ───────────────────────── P5: Квитанции ────────────────────────────────────

class Receipt(Base):
    """Сгенерированная PDF-квитанция на оплату."""
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    amount = Column(Float, nullable=False, default=0.0)
    pdf_path = Column(String(512))

    student = relationship("Student", back_populates="receipts")
    created_by_user = relationship("User", back_populates="receipts_created")

    def __repr__(self):
        return f"<Receipt {self.id}: student={self.student_id} amount={self.amount}>"