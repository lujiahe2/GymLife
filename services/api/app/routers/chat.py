from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.llm import coach_should_disable_tools, generate_coach_reply
from app.models import ChatMessage, User
from app.schemas import ChatMessageOut, ChatSendBody, ChatSendResponse

router = APIRouter()

_HISTORY_LIMIT = 40


@router.post("/messages", response_model=ChatSendResponse)
def send_message(
    body: ChatSendBody,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChatSendResponse:
    user_msg = ChatMessage(
        user_id=user.id,
        role="user",
        content=body.content,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at)
        .limit(_HISTORY_LIMIT)
    )
    history = list(db.exec(stmt).all())

    try:
        assistant_text = generate_coach_reply(
            history,
            user,
            db,
            client_timezone=body.client_timezone,
            disable_tools=coach_should_disable_tools(body.content),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM request failed: {exc!s}",
        ) from exc
    bot_msg = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=assistant_text,
        created_at=datetime.now(timezone.utc),
    )
    db.add(bot_msg)
    db.commit()
    db.refresh(bot_msg)

    return ChatSendResponse(
        user_message=ChatMessageOut.model_validate(user_msg),
        assistant_message=ChatMessageOut.model_validate(bot_msg),
    )


@router.get("/messages", response_model=list[ChatMessageOut])
def list_messages(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    limit: int = 100,
) -> list[ChatMessageOut]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at)
        .limit(min(limit, 500))
    )
    rows = db.exec(stmt).all()
    return [ChatMessageOut.model_validate(m) for m in rows]


@router.delete("/messages")
def delete_messages(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict[str, int]:
    stmt = delete(ChatMessage).where(ChatMessage.user_id == user.id)
    result = db.execute(stmt)
    db.commit()
    return {"deleted": int(result.rowcount or 0)}
