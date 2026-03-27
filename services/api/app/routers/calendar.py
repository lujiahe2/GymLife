import calendar as cal
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.auth import get_current_user
from app.calendar_merge import normalize_stored_plan_text
from app.database import get_session
from app.models import CalendarDay, User
from app.schemas import CalendarDayOut, CalendarDayUpsert, CalendarMonthOut

router = APIRouter()


def _has_plan_content(row: CalendarDay) -> bool:
    tr = normalize_stored_plan_text(row.training_plan or "")
    di = normalize_stored_plan_text(row.diet_plan or "")
    return bool(tr.strip()) or bool(di.strip())


@router.get("/day", response_model=CalendarDayOut)
def get_calendar_day(
    day: date = Query(..., alias="date", description="ISO date YYYY-MM-DD"),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarDayOut:
    stmt = select(CalendarDay).where(
        CalendarDay.user_id == user.id,
        CalendarDay.day_date == day,
    )
    row = db.exec(stmt).first()
    if not row:
        return CalendarDayOut(date=day, training_plan="", diet_plan="")
    return CalendarDayOut(
        date=row.day_date,
        training_plan=normalize_stored_plan_text(row.training_plan or ""),
        diet_plan=normalize_stored_plan_text(row.diet_plan or ""),
    )


@router.put("/day", response_model=CalendarDayOut)
def upsert_calendar_day(
    body: CalendarDayUpsert,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarDayOut:
    stmt = select(CalendarDay).where(
        CalendarDay.user_id == user.id,
        CalendarDay.day_date == body.date,
    )
    row = db.exec(stmt).first()
    if row:
        row.training_plan = body.training_plan
        row.diet_plan = body.diet_plan
        db.add(row)
    else:
        row = CalendarDay(
            user_id=user.id,
            day_date=body.date,
            training_plan=body.training_plan,
            diet_plan=body.diet_plan,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return CalendarDayOut(
        date=row.day_date,
        training_plan=normalize_stored_plan_text(row.training_plan or ""),
        diet_plan=normalize_stored_plan_text(row.diet_plan or ""),
    )


@router.get("/month", response_model=CalendarMonthOut)
def get_calendar_month(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarMonthOut:
    last = cal.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last)
    stmt = (
        select(CalendarDay)
        .where(
            CalendarDay.user_id == user.id,
            CalendarDay.day_date >= start,
            CalendarDay.day_date <= end,
        )
        .order_by(CalendarDay.day_date)
    )
    rows = list(db.exec(stmt).all())
    days_with_plans = [r.day_date for r in rows if _has_plan_content(r)]
    return CalendarMonthOut(year=year, month=month, days_with_plans=days_with_plans)
