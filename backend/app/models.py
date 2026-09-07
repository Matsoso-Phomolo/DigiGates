import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class UserRole(str, enum.Enum): LEARNER="LEARNER"; ADMIN="ADMIN"
class ProgressStatus(str, enum.Enum): NOT_STARTED="NOT_STARTED"; IN_PROGRESS="IN_PROGRESS"; COMPLETED="COMPLETED"
class TimestampMixin:
    created_at: Mapped[datetime]=mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime]=mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class User(TimestampMixin, Base):
    __tablename__="users"
    user_id: Mapped[int]=mapped_column(Integer, primary_key=True)
    full_name: Mapped[str]=mapped_column(String(120), nullable=False)
    email: Mapped[str]=mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String(255), nullable=False)
    role: Mapped[UserRole]=mapped_column(Enum(UserRole), nullable=False, default=UserRole.LEARNER)
    is_active: Mapped[bool]=mapped_column(Boolean, nullable=False, default=True, server_default="1")
    saved_circuits=relationship("SavedCircuit", back_populates="learner")
    progress_entries=relationship("Progress", back_populates="learner")
    attempts=relationship("ExerciseAttempt", back_populates="learner")
    created_circuits=relationship("PrebuiltCircuit", back_populates="creator")

class LogicGate(TimestampMixin, Base):
    __tablename__="logic_gates"
    __table_args__=(CheckConstraint("input_count IN (1,2)", name="ck_gate_input_count"),)
    gate_id: Mapped[int]=mapped_column(Integer, primary_key=True)
    gate_name: Mapped[str]=mapped_column(String(20), nullable=False, unique=True)
    description: Mapped[str]=mapped_column(Text, nullable=False)
    input_count: Mapped[int]=mapped_column(Integer, nullable=False)
    boolean_symbol: Mapped[str]=mapped_column(String(30), nullable=False)
    expression_pattern: Mapped[str]=mapped_column(String(100), nullable=False)
    lessons=relationship("Lesson", back_populates="gate")

class Lesson(TimestampMixin, Base):
    __tablename__="lessons"
    __table_args__=(Index("ix_lessons_published_order", "is_published", "lesson_order"),)
    lesson_id: Mapped[int]=mapped_column(Integer, primary_key=True)
    gate_id: Mapped[int]=mapped_column(ForeignKey("logic_gates.gate_id", ondelete="RESTRICT"), nullable=False, index=True)
    title: Mapped[str]=mapped_column(String(180), nullable=False)
    theory_content: Mapped[str]=mapped_column(Text, nullable=False)
    lesson_order: Mapped[int]=mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool]=mapped_column(Boolean, nullable=False, default=False, server_default="0")
    gate=relationship("LogicGate", back_populates="lessons")
    progress_entries=relationship("Progress", back_populates="lesson")
    exercises=relationship("Exercise", back_populates="lesson")

class PrebuiltCircuit(TimestampMixin, Base):
    __tablename__="prebuilt_circuits"
    __table_args__=(Index("ix_prebuilt_published_difficulty", "is_published", "difficulty"),)
    circuit_id: Mapped[int]=mapped_column(Integer, primary_key=True)
    title: Mapped[str]=mapped_column(String(180), nullable=False)
    description: Mapped[str]=mapped_column(Text, nullable=False)
    difficulty: Mapped[str]=mapped_column(String(30), nullable=False)
    circuit_definition: Mapped[dict]=mapped_column(JSON, nullable=False)
    expression: Mapped[str]=mapped_column(Text, nullable=False)
    created_by: Mapped[int]=mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    is_published: Mapped[bool]=mapped_column(Boolean, nullable=False, default=False, server_default="0")
    creator=relationship("User", back_populates="created_circuits")
    exercises=relationship("Exercise", back_populates="circuit")

class SavedCircuit(TimestampMixin, Base):
    __tablename__="saved_circuits"
    __table_args__=(UniqueConstraint("learner_id","circuit_name",name="uq_saved_learner_name"),)
    saved_circuit_id: Mapped[int]=mapped_column(Integer, primary_key=True)
    learner_id: Mapped[int]=mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    circuit_name: Mapped[str]=mapped_column(String(180), nullable=False)
    circuit_definition: Mapped[dict]=mapped_column(JSON, nullable=False)
    expression: Mapped[str]=mapped_column(Text, nullable=False)
    learner=relationship("User", back_populates="saved_circuits")

class Progress(Base):
    __tablename__="progress"
    __table_args__=(UniqueConstraint("learner_id","lesson_id",name="uq_progress_learner_lesson"),)
    progress_id: Mapped[int]=mapped_column(Integer, primary_key=True)
    learner_id: Mapped[int]=mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    lesson_id: Mapped[int]=mapped_column(ForeignKey("lessons.lesson_id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[ProgressStatus]=mapped_column(Enum(ProgressStatus), nullable=False, default=ProgressStatus.NOT_STARTED)
    last_accessed_at: Mapped[datetime]=mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime|None]=mapped_column(DateTime)
    learner=relationship("User", back_populates="progress_entries")
    lesson=relationship("Lesson", back_populates="progress_entries")

class Exercise(TimestampMixin, Base):
    __tablename__="exercises"
    exercise_id: Mapped[int]=mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int|None]=mapped_column(ForeignKey("lessons.lesson_id", ondelete="RESTRICT"), index=True)
    circuit_id: Mapped[int|None]=mapped_column(ForeignKey("prebuilt_circuits.circuit_id", ondelete="RESTRICT"), index=True)
    title: Mapped[str]=mapped_column(String(180), nullable=False)
    instructions: Mapped[str]=mapped_column(Text, nullable=False)
    exercise_type: Mapped[str]=mapped_column(String(50), nullable=False)
    expected_result: Mapped[dict]=mapped_column(JSON, nullable=False)
    is_published: Mapped[bool]=mapped_column(Boolean, nullable=False, default=False, server_default="0")
    lesson=relationship("Lesson", back_populates="exercises")
    circuit=relationship("PrebuiltCircuit", back_populates="exercises")
    attempts=relationship("ExerciseAttempt", back_populates="exercise")

class ExerciseAttempt(Base):
    __tablename__="exercise_attempts"
    __table_args__=(CheckConstraint("score >= 0 AND score <= 100", name="ck_attempt_score"), Index("ix_attempt_learner_exercise", "learner_id", "exercise_id"))
    attempt_id: Mapped[int]=mapped_column(Integer, primary_key=True)
    exercise_id: Mapped[int]=mapped_column(ForeignKey("exercises.exercise_id", ondelete="RESTRICT"), nullable=False, index=True)
    learner_id: Mapped[int]=mapped_column(ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    submitted_answer: Mapped[dict]=mapped_column(JSON, nullable=False)
    is_correct: Mapped[bool]=mapped_column(Boolean, nullable=False)
    score: Mapped[Decimal]=mapped_column(Numeric(5,2), nullable=False)
    attempted_at: Mapped[datetime]=mapped_column(DateTime, nullable=False, server_default=func.now())
    exercise=relationship("Exercise", back_populates="attempts")
    learner=relationship("User", back_populates="attempts")
