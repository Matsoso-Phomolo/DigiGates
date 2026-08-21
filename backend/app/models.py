from datetime import datetime
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="learner")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LogicGate(Base):
    __tablename__ = "logic_gates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    description: Mapped[str] = mapped_column(Text)
    expression: Mapped[str] = mapped_column(String(100))
    arity: Mapped[int]

class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    gate_name: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(default=0)

class PrebuiltCircuit(Base):
    __tablename__ = "prebuilt_circuits"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    definition: Mapped[dict] = mapped_column(JSON)

class SavedCircuit(Base):
    __tablename__ = "saved_circuits"
    __table_args__ = (UniqueConstraint("user_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    definition: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Progress(Base):
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "mode", "item_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    item_key: Mapped[str] = mapped_column(String(100))
    state: Mapped[dict] = mapped_column(JSON)

class Exercise(Base):
    __tablename__ = "exercises"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    prompt: Mapped[str] = mapped_column(Text)
    solution: Mapped[dict] = mapped_column(JSON)

