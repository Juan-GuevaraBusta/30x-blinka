"""SQLAlchemy table definitions for rules and decision records (T4.2)."""

from __future__ import annotations

from sqlalchemy import Integer, MetaData, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

metadata = MetaData()


class Base(DeclarativeBase):
    metadata = metadata


class RulesDocument(Base):
    __tablename__ = "rules_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class DecisionRecordRow(Base):
    __tablename__ = "decision_record"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
