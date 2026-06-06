from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    ingredients: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: list[str]
    steps: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: list[str]

    prep_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cook_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    servings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dietary_flags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: list[str]
    nutrition: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: NutritionReport
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source_context_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyLogEntry(Base):
    """Meals logged per day (single-user MVP)."""

    __tablename__ = "daily_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    recipe_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    servings: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    nutrition: Mapped[str] = mapped_column(Text, nullable=False)  # JSON Nutrition per serving
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Profile(Base):
    """Single-user profile (MVP, no auth). One row, conventionally id=1."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(10), nullable=True)  # male/female/other
    activity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(20), nullable=True)  # lose/maintain/gain
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: list[str]
    dietary_prefs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: list[str]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
