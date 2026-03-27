import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.auth import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import GymProfileData, ProfileResponse

router = APIRouter(prefix="/profile", tags=["profile"])


def _parse_profile(raw: str) -> GymProfileData:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return GymProfileData.model_validate(data)


@router.get("", response_model=ProfileResponse)
def get_profile(
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    return ProfileResponse(email=user.email, profile=_parse_profile(user.gym_profile_json))


@router.patch("", response_model=ProfileResponse)
def patch_profile(
    body: GymProfileData,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    try:
        current = json.loads(user.gym_profile_json or "{}")
    except json.JSONDecodeError:
        current = {}
    if not isinstance(current, dict):
        current = {}
    patch = body.model_dump(exclude_unset=True)
    merged = {**current, **patch}
    user.gym_profile_json = json.dumps(merged)
    db.add(user)
    db.commit()
    db.refresh(user)
    return ProfileResponse(email=user.email, profile=_parse_profile(user.gym_profile_json))
