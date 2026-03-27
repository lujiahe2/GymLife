from datetime import date as DateType
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# --- Auth & profile ---


class UserRegister(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


SexOption = Literal["female", "male", "non_binary", "other", "prefer_not_to_say"]

# Short fitness goals blurb — keeps prompts and UI manageable.
GOALS_MAX_LENGTH = 500


class GymProfileData(BaseModel):
    name: str | None = Field(None, max_length=120)
    sex: SexOption | None = None
    age: int | None = Field(None, ge=1, le=120)
    height_cm: int | None = Field(None, ge=50, le=250)
    weight_kg: float | None = Field(None, ge=20, le=400)
    # 1 = beginner … 5 = expert (UI slider); legacy free-text may still exist in experience_level
    experience_level_index: int | None = Field(None, ge=1, le=5)
    experience_level: str | None = Field(None, max_length=200)
    goals: str | None = Field(None, max_length=GOALS_MAX_LENGTH)
    days_per_week: int | None = Field(None, ge=1, le=7)
    equipment: str | None = Field(None, max_length=2000)
    injuries_limitations: str | None = Field(None, max_length=2000)


class ProfileResponse(BaseModel):
    email: str
    profile: GymProfileData


# --- Chat ---


class ChatSendBody(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    client_timezone: str | None = Field(
        None,
        max_length=80,
        description="IANA timezone from the browser (e.g. America/Los_Angeles) for local date/time.",
    )


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSendResponse(BaseModel):
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut


# --- Calendar (training + diet per day) ---


class CalendarDayOut(BaseModel):
    date: DateType
    training_plan: str
    diet_plan: str


class CalendarDayUpsert(BaseModel):
    date: DateType
    training_plan: str = Field(default="", max_length=8000)
    diet_plan: str = Field(default="", max_length=8000)


class CalendarMonthOut(BaseModel):
    year: int
    month: int
    days_with_plans: list[DateType]
