import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from openai import APIConnectionError, APIError, OpenAI
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.models import CalendarDay, ChatMessage, User
from app.calendar_merge import merge_calendar_day_from_llm, normalize_stored_plan_text
from app.profile_merge import _coerce_int_in_range, merge_gym_profile_from_llm
from app.schemas import GOALS_MAX_LENGTH

SYSTEM_PROMPT = """You are GymLife Coach, a supportive fitness assistant for people new to the gym.

Goals:
- Help them build realistic workout habits and learn basic exercise and safety concepts.
- Ask clarifying questions when needed (goals, injuries, schedule, equipment).
- Keep answers concise and actionable unless they ask for detail.
- Do not diagnose medical conditions; suggest seeing a professional when health issues are unclear.
- The user has an in-app calendar: they can save a training plan and a diet plan for each calendar day.
- **Saving:** Chat text alone does **not** update the database. To change their saved gym profile or calendar, you **must** call the matching tool (`update_gym_profile` or `update_calendar_day`) — but **only** when they clearly want to **save or edit** stored data.
- **Questions like “what’s the date today?”, “what day is it?”, or “what time is it?”** are **informational only**: answer using the **Real-time reference** section below in plain text. **Do not** call `update_calendar_day` or `update_gym_profile` for those.

Tone: encouraging, clear, and practical.
- **Greetings and small talk** (e.g. “hi”, “hello”, “thanks”): reply briefly and warmly. **Do not** bring up their saved calendar, training plan, or diet unless they ask."""

TOOLS_INSTRUCTION = """

You may call the function `update_gym_profile` when the user clearly asks to change what is saved in their gym profile
(name, sex, age, height_cm, weight_kg, goals, experience level, days per week, equipment, or injuries/limitations).
Only include fields they want to update. Do not call this tool for general questions that do not change their saved profile.
For `age`, `height_cm`, and `days_per_week`, use integers (e.g. age `28`, not the words "twenty-eight"). Field name for age is `age` (years).
After a successful update, briefly confirm what you saved in plain language.

You may call `update_calendar_day` **only** when the user **explicitly** wants to **save, change, remove, or log** their **stored** training plan and/or diet plan for a date (e.g. “put leg day on March 28”, “clear my diet for tomorrow”, “log this workout on my calendar”).
**Never** call `update_calendar_day` for: asking what day or date it is, what “today” means, general chat, or questions that do not request changing saved calendar content. For those, answer in text using the Real-time reference block.
Use `date` as ISO `YYYY-MM-DD`. Include `training_plan` and/or `diet_plan` when updating those fields as **plain text sentences** (never JSON objects). Omit a field to leave it unchanged. Use empty strings only if they explicitly want to clear that field.
When choosing `date` for `update_calendar_day`, use the user's **local calendar date** from the real-time block below (not a guess). For "today" / "tomorrow", compute from that local date.
Never write JSON tool calls, function names, or raw `parameters` in your reply text — use the tool API only."""

_EXPERIENCE_INDEX_LABELS = {
    1: "Beginner",
    2: "Novice",
    3: "Intermediate",
    4: "Advanced",
    5: "Expert",
}

GYM_PROFILE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "update_gym_profile",
            "description": (
                "Update this user's saved gym profile in the app. Call only when they ask to "
                "change stored fields: name, sex, age (years, integer), height_cm, weight_kg, goals, "
                "experience_level_index (1–5), days_per_week, equipment, or injuries_limitations. "
                "Include only fields they want to change. Use numeric types for age/height/weight/days."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Display name"},
                    "sex": {
                        "type": "string",
                        "enum": [
                            "female",
                            "male",
                            "non_binary",
                            "other",
                            "prefer_not_to_say",
                        ],
                    },
                    "age": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 120,
                        "description": "Age in years (whole number). JSON key must be `age`.",
                    },
                    "height_cm": {
                        "type": "integer",
                        "minimum": 50,
                        "maximum": 250,
                        "description": "Height in centimeters (integer).",
                    },
                    "weight_kg": {
                        "type": "number",
                        "minimum": 20,
                        "maximum": 400,
                    },
                    "experience_level_index": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "1=beginner … 5=expert",
                    },
                    "experience_level": {
                        "type": "string",
                        "description": "Legacy free-text experience if not using 1–5 scale",
                    },
                    "goals": {
                        "type": "string",
                        "maxLength": GOALS_MAX_LENGTH,
                        "description": "Short fitness goals (sentence or two)",
                    },
                    "days_per_week": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 7,
                    },
                    "equipment": {"type": "string"},
                    "injuries_limitations": {"type": "string"},
                },
            },
        },
    }
]

CALENDAR_TOOL_SPEC: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "update_calendar_day",
        "description": (
            "Persists this user's training plan and/or diet plan for one calendar day in the app database. "
            "Call **only** if they explicitly want to save, edit, clear, or log workout/meal plans for a specific date. "
            "**Do not** call for questions about what day or date it is (answer those in chat from context). "
            "Include `date` (YYYY-MM-DD) and at least one of `training_plan`, `diet_plan` as **plain text** (not JSON). "
            "When updating both, pass both strings."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Calendar day as YYYY-MM-DD (local date).",
                },
                "training_plan": {
                    "type": "string",
                    "description": "Optional. Plain-language workout text for that day (not JSON).",
                },
                "diet_plan": {
                    "type": "string",
                    "description": "Optional. Plain-language diet/meals text for that day (not JSON).",
                },
            },
            "required": ["date"],
        },
    },
}

# Profile + calendar tools for the coach (same completion request).
COACH_TOOLS: list[dict[str, Any]] = GYM_PROFILE_TOOLS + [CALENDAR_TOOL_SPEC]

_NO_TOOL_DATETIME_PATTERNS: tuple[str, ...] = (
    r"what\s*'?s?\s+the\s+date",
    r"what\s+is\s+the\s+date",
    r"what\s+day\s+is",
    r"what\s+date\s+is\s+it",
    r"^date\s+today\s*$",
    r"today'?s?\s+date",
    r"what\s+time\s+is",
    r"current\s+date",
    r"what\s+is\s+today'?s?\s+date",
    r"which\s+day\s+is",
)

_SAVE_INTENT_MARKERS: frozenset[str] = frozenset(
    (
        "save ",
        "update ",
        " set ",
        " put ",
        "put ",
        " log ",
        "add to",
        "clear ",
        "remove ",
        "delete ",
        "edit my",
        "change my",
        "schedule",
        "rest day",
        "training plan",
        "diet plan",
        "workout for",
        "meal plan",
        "on my calendar",
        "to calendar",
    )
)


def is_informational_datetime_question(message: str) -> bool:
    """
    If True, the chat layer skips tools so local LLMs can't hallucinate
    `update_calendar_day` for “what's the date?” style questions.
    """
    c = message.strip().lower()
    if len(c) > 200:
        return False
    if any(m in c for m in _SAVE_INTENT_MARKERS):
        return False
    return any(re.search(p, c) for p in _NO_TOOL_DATETIME_PATTERNS)


def is_general_chat_without_save_intent(message: str) -> bool:
    """
    Short greetings / thanks with no save intent — skip tools and avoid injecting
    saved calendar/profile into the prompt (local models otherwise parrot “rest day”
    or hallucinate updates).
    """
    c = message.strip().lower()
    if len(c) > 100:
        return False
    if any(m in c for m in _SAVE_INTENT_MARKERS):
        return False
    c2 = re.sub(r"[^a-z0-9\s]", " ", c)
    c2 = re.sub(r"\s+", " ", c2).strip()
    if not c2:
        return False
    patterns = (
        r"^(hi|hello|hey|yo|sup|hiya|howdy|greetings)(\s+(there|coach|friend|buddy))?$",
        r"^(thanks?|thx|ty)(\s+(you|mate|a lot))?$",
        r"^thank you$",
        r"^(ok|okay|yes|no|yeah|yep|nope|nah)$",
        r"^good (morning|afternoon|evening)$",
        r"^how (are you|are ya|is it going|s it going)(\s+today)?$",
        r"^what'?s up$",
        r"^(bye|goodbye|cya|see you)$",
        # Social pleasantries (not training intent; local models confuse these with “updates”)
        r"^(nice|good|great|lovely|pleasure)\s+to\s+meet\s+you(\s+(too|as well))?$",
        r"^nice\s+meeting\s+you(\s+(too|as well))?$",
        r"^pleased\s+to\s+meet\s+you(\s+(too|as well))?$",
        r"^(good|nice)\s+to\s+see\s+you(\s+(too|again))?$",
        r"^(good|nice)\s+to\s+talk\s+to\s+you(\s+too)?$",
    )
    return any(re.match(p, c2) for p in patterns)


def coach_should_disable_tools(message: str) -> bool:
    """Whether this user turn should not offer profile/calendar tools."""
    return is_informational_datetime_question(message) or is_general_chat_without_save_intent(
        message
    )


def _direct_answer_datetime_question(client_timezone: str | None) -> str:
    """
    Deterministic reply for date/time questions so local models never return empty
    replies or hallucinate calendar/profile updates.
    """
    now_local, local_date = _user_local_datetime_and_date(client_timezone)
    weekday = now_local.strftime("%A")
    time_s = now_local.strftime("%H:%M")
    return (
        f"Today is {weekday}, {local_date.isoformat()} "
        f"(your local time is about {time_s})."
    )


def _user_local_datetime_and_date(client_timezone: str | None) -> tuple[datetime, date]:
    """Best-effort local `now` and calendar date for the user (browser TZ when valid)."""
    now_utc = datetime.now(timezone.utc)
    if client_timezone:
        tz = client_timezone.strip()
        if tz:
            try:
                z = ZoneInfo(tz)
                now_local = now_utc.astimezone(z)
                return now_local, now_local.date()
            except Exception:
                pass
    now_local = datetime.now().astimezone()
    return now_local, now_local.date()


def _format_realtime_context_for_prompt(client_timezone: str | None) -> str:
    """Inject current wall-clock time so the model can resolve 'today', 'tomorrow', weekdays."""
    now_utc = datetime.now(timezone.utc)
    now_local, local_date = _user_local_datetime_and_date(client_timezone)
    utc_s = now_utc.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    local_s = now_local.isoformat(timespec="seconds")
    weekday = now_local.strftime("%A")
    lines = [
        "",
        "## Real-time reference (use this for scheduling language: today, tomorrow, next Monday, etc.)",
        f"- UTC now: {utc_s}",
    ]
    if client_timezone and client_timezone.strip():
        lines.append(f"- User timezone (from app): {client_timezone.strip()}")
    lines.extend(
        [
            f"- User local time: {local_s} ({weekday})",
            f"- User local calendar date: {local_date.isoformat()}",
            "- If they ask “what’s the date today?” or “what day is it?”, answer with the **User local calendar date** and weekday above — **no tools**.",
            "- When calling `update_calendar_day` (only if they ask to save/edit plans), use `YYYY-MM-DD` for the user's local calendar unless they specify otherwise.",
        ]
    )
    return "\n".join(lines)


def _format_realtime_context_minimal_for_prompt(client_timezone: str | None) -> str:
    """Short clock/date only — for greetings so we don't inject tool-scheduling hints."""
    now_local, local_date = _user_local_datetime_and_date(client_timezone)
    weekday = now_local.strftime("%A")
    local_s = now_local.isoformat(timespec="seconds")
    return (
        "\n\n## Real-time reference\n"
        f"- User local time: {local_s} ({weekday}), calendar date {local_date.isoformat()}.\n"
    )


def _format_calendar_for_prompt(
    user: User,
    db: Session,
    user_local_today: date,
) -> str:
    """Summarize today / tomorrow calendar rows so the coach can reference or edit them."""
    today = user_local_today
    parts: list[str] = []
    for label, d in (("Today", today), ("Tomorrow", today + timedelta(days=1))):
        stmt = select(CalendarDay).where(
            CalendarDay.user_id == user.id,
            CalendarDay.day_date == d,
        )
        row = db.exec(stmt).first()
        if not row:
            continue
        tr = normalize_stored_plan_text(row.training_plan or "").strip()
        di = normalize_stored_plan_text(row.diet_plan or "").strip()
        if not tr and not di:
            continue
        chunk = f"- {label} ({d.isoformat()}):"
        if tr:
            snippet = tr if len(tr) <= 400 else tr[:400] + "…"
            chunk += f"\n  Training: {snippet}"
        if di:
            snippet = di if len(di) <= 400 else di[:400] + "…"
            chunk += f"\n  Diet: {snippet}"
        parts.append(chunk)
    if not parts:
        return ""
    return "\n\nCalendar plans already saved in the app (you can update via `update_calendar_day`):\n" + "\n".join(
        parts
    )


def _format_profile_for_prompt(user: User) -> str:
    try:
        data = json.loads(user.gym_profile_json or "{}")
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict) or not data:
        return ""
    sex_labels = {
        "female": "Female",
        "male": "Male",
        "non_binary": "Non-binary",
        "other": "Other",
        "prefer_not_to_say": "Prefer not to say",
    }
    lines: list[str] = []

    name = data.get("name")
    if name is not None and str(name).strip():
        lines.append(f"- Name: {str(name).strip()}")

    sex = data.get("sex")
    if isinstance(sex, str) and sex.strip():
        lines.append(f"- Sex: {sex_labels.get(sex, sex)}")

    age = data.get("age")
    a = _coerce_int_in_range(age, 1, 120)
    if a is not None:
        lines.append(f"- Age: {a} years")

    hcm = data.get("height_cm")
    h = _coerce_int_in_range(hcm, 50, 250)
    if h is not None:
        lines.append(f"- Height: {h} cm")

    wkg = data.get("weight_kg")
    if wkg is not None:
        try:
            w = float(wkg)
            if 20 <= w <= 400:
                lines.append(f"- Weight: {w:.1f} kg")
        except (TypeError, ValueError):
            pass

    idx = data.get("experience_level_index")
    if idx is not None:
        try:
            i = int(idx)
            if 1 <= i <= 5:
                lines.append(
                    f"- Experience: {_EXPERIENCE_INDEX_LABELS[i]} ({i}/5)",
                )
        except (TypeError, ValueError):
            pass
    else:
        el = data.get("experience_level")
        if el is not None and str(el).strip():
            lines.append(f"- Experience: {str(el).strip()}")

    for key, label in (
        ("goals", "Goals"),
        ("days_per_week", "Days per week"),
        ("equipment", "Equipment"),
        ("injuries_limitations", "Injuries / limitations"),
    ):
        val = data.get(key)
        if val is None or str(val).strip() == "":
            continue
        lines.append(f"- {label}: {val}")

    if not lines:
        return ""
    return (
        "\n\nThis user's saved gym profile (private to them only — use when relevant, do not recite verbatim):\n"
        + "\n".join(lines)
    )


def _fallback_when_not_configured() -> str:
    return (
        "LLM is not configured yet. For Ollama, copy `services/api/env.example` to `.env`, "
        "run `ollama serve` and `ollama pull <model>`, then restart the API."
    )


def _resolve_api_key(settings: Settings) -> str | None:
    """Ollama’s OpenAI-compatible API ignores the key; use a placeholder if base URL is set."""
    key = (settings.openai_api_key or "").strip()
    if key:
        return key
    if (settings.openai_base_url or "").strip():
        return "ollama"
    return None


def _looks_like_leaked_tool_json(content: str) -> bool:
    c = content.strip()
    if len(c) < 12:
        return False
    if "update_gym_profile" in c:
        return True
    if "update_calendar_day" in c:
        return True
    return c.startswith("{") and '"name"' in c and (
        "parameters" in c or "arguments" in c
    )


def _first_json_object(s: str) -> dict[str, Any] | None:
    """Parse the first complete JSON object in `s` (helps with model garbage after `}`)."""
    dec = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _end = dec.raw_decode(s[i:])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            continue
    return None


def _decode_tool_arguments_json(s: str | None) -> dict[str, Any]:
    """Ollama often returns malformed JSON; try strict parse then first `{...}` object."""
    if s is None or not str(s).strip():
        return {}
    s = str(s).strip()
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        obj = _first_json_object(s)
        return obj if isinstance(obj, dict) else {}


def _parse_leaked_profile_tool(content: str) -> dict[str, Any] | None:
    """
    Some OpenAI-compatible servers (notably Ollama) sometimes put tool calls in `content`
    as JSON text instead of structured `tool_calls`. Parse common shapes into merge args.
    """
    s = content.strip()
    if not s:
        return None
    outer: dict[str, Any] | None = None
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            parsed = parsed[0]
        if isinstance(parsed, dict):
            outer = parsed
    except json.JSONDecodeError:
        outer = _first_json_object(s)
    if outer is None:
        return None
    name = outer.get("name")
    if name != "update_gym_profile":
        return None
    params = outer.get("parameters")
    if params is None:
        params = outer.get("arguments")
    if params is None:
        return None
    inner: Any
    if isinstance(params, str):
        try:
            inner = json.loads(params)
        except json.JSONDecodeError:
            inner = _first_json_object(params)
            if inner is None:
                return None
    else:
        inner = params
    if not isinstance(inner, dict):
        return None
    if "object" in inner and isinstance(inner["object"], str):
        raw_obj = inner["object"]
        try:
            obj = json.loads(raw_obj)
        except json.JSONDecodeError:
            obj = _first_json_object(raw_obj)
        return obj if isinstance(obj, dict) else None
    return inner


def _parse_leaked_calendar_tool(content: str) -> dict[str, Any] | None:
    """Recover `update_calendar_day` args from model text (Ollama-style leaks)."""
    s = content.strip()
    if not s:
        return None
    outer: dict[str, Any] | None = None
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            parsed = parsed[0]
        if isinstance(parsed, dict):
            outer = parsed
    except json.JSONDecodeError:
        outer = _first_json_object(s)
    if outer is None:
        return None
    if outer.get("name") != "update_calendar_day":
        return None
    params = outer.get("parameters")
    if params is None:
        params = outer.get("arguments")
    if params is None:
        return None
    inner: Any
    if isinstance(params, str):
        try:
            inner = json.loads(params)
        except json.JSONDecodeError:
            inner = _first_json_object(params)
            if inner is None:
                return None
    else:
        inner = params
    if not isinstance(inner, dict):
        return None
    if "object" in inner and isinstance(inner["object"], str):
        raw_obj = inner["object"]
        try:
            obj = json.loads(raw_obj)
        except json.JSONDecodeError:
            obj = _first_json_object(raw_obj)
        return obj if isinstance(obj, dict) else None
    return inner


def _assistant_message_to_dict(msg: Any) -> dict[str, Any]:
    d: dict[str, Any] = {"role": "assistant", "content": msg.content}
    if msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "{}",
                },
            }
            for tc in msg.tool_calls
        ]
    return d


def generate_coach_reply(
    history: list[ChatMessage],
    user: User,
    db: Session,
    *,
    client_timezone: str | None = None,
    disable_tools: bool = False,
) -> str:
    """
    Chat completion with optional tools: `update_gym_profile` and `update_calendar_day`.
    Requires DB session to apply merges.
    When ``disable_tools`` is True, tools are not offered (plain chat only).
    """
    settings = get_settings()
    key = _resolve_api_key(settings)
    if not key:
        return _fallback_when_not_configured()

    if disable_tools and history:
        last = history[-1]
        if last.role == "user" and is_informational_datetime_question(last.content):
            return _direct_answer_datetime_question(client_timezone)

    _, user_local_today = _user_local_datetime_and_date(client_timezone)
    last_msg = history[-1] if history else None
    suppress_saved = (
        last_msg is not None
        and last_msg.role == "user"
        and is_general_chat_without_save_intent(last_msg.content)
    )
    if disable_tools:
        realtime = (
            _format_realtime_context_minimal_for_prompt(client_timezone)
            if suppress_saved
            else _format_realtime_context_for_prompt(client_timezone)
        )
        profile_part = "" if suppress_saved else _format_profile_for_prompt(user)
        cal_part = "" if suppress_saved else _format_calendar_for_prompt(user, db, user_local_today)
        greeting_note = (
            "\n**This turn only:** They sent a short greeting or thanks — reply in one or two friendly sentences. "
            "Do **not** mention their saved calendar, training plan, or diet, and do **not** say you updated anything.\n"
            if suppress_saved
            else ""
        )
        system_content = (
            SYSTEM_PROMPT
            + "\n\n**This turn:** Answer in plain text only. Do **not** call any tools or claim you saved data in the app.\n"
            + greeting_note
            + realtime
            + profile_part
            + cal_part
        )
    else:
        system_content = (
            SYSTEM_PROMPT
            + TOOLS_INSTRUCTION
            + _format_realtime_context_for_prompt(client_timezone)
            + _format_profile_for_prompt(user)
            + _format_calendar_for_prompt(user, db, user_local_today)
        )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_content}
    ]
    for row in history:
        if row.role not in ("user", "assistant"):
            continue
        messages.append({"role": row.role, "content": row.content})

    timeout = httpx.Timeout(300.0, connect=15.0)
    client_kwargs: dict = {
        "api_key": key,
        "timeout": timeout,
    }
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url.rstrip("/")

    client = OpenAI(**client_kwargs)

    max_rounds = 5
    use_tools = not disable_tools
    # Ollama sometimes errors with multiple tools; retry with calendar-only before disabling tools.
    tool_mode: str = "full"
    empty_reply_retries = 0

    for _ in range(max_rounds):
        try:
            create_kwargs: dict[str, Any] = {
                "model": settings.openai_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024,
            }
            if use_tools:
                if tool_mode == "full":
                    create_kwargs["tools"] = COACH_TOOLS
                else:
                    create_kwargs["tools"] = [CALENDAR_TOOL_SPEC]
                create_kwargs["tool_choice"] = "auto"

            response = client.chat.completions.create(**create_kwargs)
        except APIError as exc:
            if use_tools and tool_mode == "full":
                tool_mode = "calendar_only"
                continue
            if use_tools:
                use_tools = False
                continue
            raise RuntimeError(
                f"Model API error: {exc!s}. Check OPENAI_MODEL matches `ollama list` (e.g. llama3.2:latest)."
            ) from exc
        except APIConnectionError as exc:
            base = settings.openai_base_url or "(OpenAI default)"
            raise RuntimeError(
                f"Cannot reach the LLM at {base}. If you use Ollama, run `ollama serve` "
                f"and ensure OPENAI_BASE_URL is http://127.0.0.1:11434/v1. ({exc})"
            ) from exc

        choice = response.choices[0]
        msg = choice.message
        finish = choice.finish_reason

        if msg.tool_calls:
            messages.append(_assistant_message_to_dict(msg))
            for tc in msg.tool_calls:
                if tc.function.name == "update_gym_profile":
                    raw = _decode_tool_arguments_json(
                        getattr(tc.function, "arguments", None),
                    )
                    user = merge_gym_profile_from_llm(user, raw, db)
                    try:
                        snapshot = json.loads(user.gym_profile_json or "{}")
                    except json.JSONDecodeError:
                        snapshot = {}
                    tool_payload = {
                        "ok": True,
                        "saved": True,
                        "updated_fields": list(raw.keys()) if isinstance(raw, dict) else [],
                        "profile": snapshot,
                    }
                elif tc.function.name == "update_calendar_day":
                    raw = _decode_tool_arguments_json(
                        getattr(tc.function, "arguments", None),
                    )
                    tool_payload = merge_calendar_day_from_llm(user, raw, db)
                else:
                    tool_payload = {"ok": False, "error": "unknown_tool"}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_payload),
                    }
                )
            continue

        text = (msg.content or "").strip()

        # Leaked tool JSON in content (no structured tool_calls) — merge profile, then ask for plain text.
        if text and _looks_like_leaked_tool_json(text):
            leaked = _parse_leaked_profile_tool(text)
            if leaked is not None:
                user = merge_gym_profile_from_llm(user, leaked, db)
                messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "The user's gym profile was updated in the app from your tool arguments."
                        ),
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Reply to the user in plain language only — no JSON, no code, no tool syntax. "
                            "If you updated their profile, briefly confirm what you saved. "
                            "Otherwise greet them and offer help."
                        ),
                    }
                )
                use_tools = False
                continue
            leaked_cal = _parse_leaked_calendar_tool(text)
            if leaked_cal is not None:
                cal_result = merge_calendar_day_from_llm(user, leaked_cal, db)
                ok_cal = cal_result.get("ok") is True
                messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "Success: calendar day saved in the app."
                            if ok_cal
                            else (
                                "Calendar save did not apply: "
                                + str(cal_result.get("error", "unknown"))
                            )
                        ),
                    }
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Reply in plain language only — no JSON. "
                            + (
                                "Confirm what you saved on their calendar."
                                if ok_cal
                                else "Apologize briefly and ask for an explicit YYYY-MM-DD date and the training/diet text to save."
                            )
                        ),
                    }
                )
                use_tools = False
                continue
            return (
                "I couldn't read that reply cleanly. Please try again in one short message "
                "(plain words only, no JSON)."
            )

        if text:
            return text

        if finish == "tool_calls" or finish == "length":
            continue

        # Ollama often returns finish=stop with empty content (especially with tools / long context).
        if empty_reply_retries < 2:
            empty_reply_retries += 1
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your last reply was empty. Write one short helpful sentence "
                        "to the user in plain English (no tools unless they asked to save data)."
                    ),
                }
            )
            if use_tools and empty_reply_retries == 2:
                use_tools = False
                tool_mode = "full"
            continue

        return (
            "Sorry — the coach didn’t return any text. "
            "Try again with a shorter message, or ask one thing at a time (local models sometimes need this)."
        )

    return (
        "Sorry — that request took too many internal steps. "
        "Try again, or split profile/calendar updates from general questions."
    )
