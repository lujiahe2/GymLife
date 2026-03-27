from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=320)
    hashed_password: str = Field(max_length=256)
    # JSON object: experience_level, goals, days_per_week, equipment, injuries_limitations
    gym_profile_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=_utc_now)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_message"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(max_length=32)  # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=_utc_now)


class CalendarDay(SQLModel, table=True):
    """Per-user training + diet notes for a calendar date (local day, ISO date in DB)."""

    __tablename__ = "calendar_day"
    __table_args__ = (UniqueConstraint("user_id", "day_date", name="uq_calendar_user_day"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    day_date: date = Field(index=True)
    training_plan: str = Field(default="", max_length=8000)
    diet_plan: str = Field(default="", max_length=8000)
