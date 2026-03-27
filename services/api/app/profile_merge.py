import json
import re
from typing import Any

from pydantic import ValidationError
from sqlmodel import Session

from app.models import User
from app.schemas import GOALS_MAX_LENGTH, GymProfileData

_VALID_SEX = frozenset(
    {"female", "male", "non_binary", "other", "prefer_not_to_say"}
)


def _coerce_int_in_range(v: Any, lo: int, hi: int) -> int | None:
    """
    LLMs often return numbers as strings (e.g. \"25\"). Accept int, float, and plain digit strings.
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if lo <= v <= hi else None
    if isinstance(v, float):
        i = int(round(v))
        return i if lo <= i <= hi else None
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if not s:
            return None
        if re.fullmatch(r"-?\d+", s):
            try:
                i = int(s)
            except ValueError:
                return None
            return i if lo <= i <= hi else None
        m = re.search(r"\b(\d{1,3})\b", s)
        if m:
            i = int(m.group(1))
            return i if lo <= i <= hi else None
    return None


def merge_gym_profile_from_llm(user: User, args: Any, db: Session) -> User:
    """
    Merge tool arguments into `user.gym_profile_json` with validation.
    Ignores unknown keys and invalid values.
    """
    if not isinstance(args, dict):
        return user

    try:
        current = json.loads(user.gym_profile_json or "{}")
    except json.JSONDecodeError:
        current = {}
    if not isinstance(current, dict):
        current = {}

    allowed = set(GymProfileData.model_fields.keys())
    for k, v in args.items():
        if k not in allowed:
            continue
        if v is None:
            continue
        if k == "sex":
            if not isinstance(v, str) or v not in _VALID_SEX:
                continue
            current[k] = v
            continue
        if k == "age":
            a = _coerce_int_in_range(v, 1, 120)
            if a is not None:
                current[k] = a
            continue
        if k == "height_cm":
            h = _coerce_int_in_range(v, 50, 250)
            if h is not None:
                current[k] = h
            continue
        if k == "weight_kg":
            if isinstance(v, bool):
                continue
            try:
                w = float(v)
            except (TypeError, ValueError):
                continue
            if 20 <= w <= 400:
                current[k] = round(w, 1)
            continue
        if k == "experience_level_index":
            ei = _coerce_int_in_range(v, 1, 5)
            if ei is not None:
                current[k] = ei
            continue
        if k == "days_per_week":
            d = _coerce_int_in_range(v, 1, 7)
            if d is not None:
                current[k] = d
            continue
        if k in (
            "name",
            "experience_level",
            "goals",
            "equipment",
            "injuries_limitations",
        ):
            if not isinstance(v, str):
                continue
            s = v.strip()
            if not s:
                continue
            if k == "goals":
                s = s[:GOALS_MAX_LENGTH]
            current[k] = s

    try:
        validated = GymProfileData.model_validate(current)
    except ValidationError:
        return user

    user.gym_profile_json = validated.model_dump_json(exclude_none=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
