import json
import re
from datetime import date
from typing import Any

from sqlmodel import Session, select

from app.models import CalendarDay, User


def _parse_calendar_date(raw: Any) -> date | None:
    """
    LLMs often emit dates like 2025-3-7 or MM/DD/YYYY; strict ISO parsing fails.
    """
    if raw is None:
        return None
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str):
        raw = str(raw).strip()
    else:
        raw = raw.strip()
    if not raw:
        return None
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", raw)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        pass
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", raw)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            pass
    return None


def unescape_plan_newlines(s: str) -> str:
    """
    Turn literal ``\\n`` / ``\\r`` (as stored by some LLM outputs) into real newlines
    so calendar textareas show line breaks instead of backslash-n.
    """
    if not s:
        return s
    return (
        s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
    )


def _dict_to_plan_text(d: dict[str, Any]) -> str:
    """
    LLMs sometimes pass structured objects instead of prose. Prefer readable lines;
    empty or all-blank objects become "" (never persist raw `{"cuisine":""}`).
    """
    if not d:
        return ""
    for key in (
        "text",
        "plan",
        "notes",
        "description",
        "training_plan",
        "diet_plan",
        "content",
        "summary",
    ):
        val = d.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:8000]
    parts: list[str] = []
    for key in (
        "cuisine",
        "meals",
        "meal_plan",
        "protein",
        "calories",
        "breakfast",
        "lunch",
        "dinner",
    ):
        val = d.get(key)
        if val is None or val == "":
            continue
        if isinstance(val, (dict, list)):
            try:
                inner = json.dumps(val, ensure_ascii=False)
            except Exception:
                inner = str(val)
            parts.append(f"{key}: {inner}")
        else:
            parts.append(f"{key}: {val}".strip())
    if parts:
        return "\n".join(parts)[:8000]
    lines: list[str] = []
    for k, v in d.items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, dict):
            inner = _dict_to_plan_text(v)
            if inner:
                lines.append(f"{k}: {inner}")
        elif isinstance(v, list):
            lines.append(f"{k}: " + "\n".join(str(x) for x in v))
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)[:8000] if lines else ""


def _coerce_plan_text(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        return unescape_plan_newlines(v)
    if isinstance(v, (int, float, bool)):
        return str(v)
    if isinstance(v, dict):
        return unescape_plan_newlines(_dict_to_plan_text(v))
    if isinstance(v, list):
        joined = "\n".join(str(x).strip() for x in v if x not in (None, "")).strip()
        return unescape_plan_newlines(joined[:8000] if joined else "")
    try:
        return unescape_plan_newlines(json.dumps(v)[:8000])
    except Exception:
        return unescape_plan_newlines(str(v)[:8000])


def normalize_stored_plan_text(raw: str) -> str:
    """
    Fix legacy rows where a dict was json-dumped into a string field (e.g. `{"cuisine":""}`).
    Also fixes literal ``\\n`` in plain-text plans so the UI shows real line breaks.
    """
    t = (raw or "").strip()
    if not t.startswith("{"):
        return unescape_plan_newlines(raw or "")
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        return unescape_plan_newlines(raw or "")
    if isinstance(obj, dict):
        return unescape_plan_newlines(_dict_to_plan_text(obj))
    if isinstance(obj, list):
        return unescape_plan_newlines(_coerce_plan_text(obj) or "")
    return unescape_plan_newlines(raw or "")


def merge_calendar_day_from_llm(user: User, args: Any, db: Session) -> dict[str, Any]:
    """
    Upsert `calendar_day` from LLM tool args. Only updates fields present in `args`.
    Returns a JSON-serializable dict for the tool result message.
    """
    if not isinstance(args, dict):
        return {"ok": False, "error": "invalid_args"}

    raw_date = args.get("date")
    d = _parse_calendar_date(raw_date)
    if d is None:
        return {
            "ok": False,
            "error": "missing_or_invalid_date",
            "received": repr(raw_date)[:120],
        }

    stmt = select(CalendarDay).where(
        CalendarDay.user_id == user.id,
        CalendarDay.day_date == d,
    )
    row = db.exec(stmt).first()
    if row is None:
        row = CalendarDay(user_id=user.id, day_date=d, training_plan="", diet_plan="")

    if "training_plan" in args:
        v = args["training_plan"]
        if v is None:
            pass
        else:
            t = _coerce_plan_text(v)
            if t is not None:
                row.training_plan = t[:8000]
    if "diet_plan" in args:
        v = args["diet_plan"]
        if v is None:
            pass
        else:
            t = _coerce_plan_text(v)
            if t is not None:
                row.diet_plan = t[:8000]

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "ok": True,
        "saved": True,
        "date": row.day_date.isoformat(),
        "training_plan": row.training_plan or "",
        "diet_plan": row.diet_plan or "",
    }
