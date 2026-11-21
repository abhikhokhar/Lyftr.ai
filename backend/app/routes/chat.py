import json
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Message
from ..schemas import ChatRequest, ChatResponse, HistoryResponse
from ..services.chat_service import process_chat

router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    simulate_failure: str | None = Header(
        default=None,
        alias="X-Simulate-Failure"
    )
):
    try:
        return process_chat(
            db,
            request,
            simulate_failure=simulate_failure
        )

    except RuntimeError as error:
        print("Provider error:", error)

        raise HTTPException(
            status_code=503,
            detail="all providers unavailable"
        )

    except Exception as error:
        print("Chat error:", error)

        raise HTTPException(
            status_code=500,
            detail="Chat generation failed. Please try again."
        )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=HistoryResponse
)
def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.asc())
        .all()
    )

    if not messages:
        raise HTTPException(
            status_code=404,
            detail="session not found"
        )

    return {
        "session_id": session_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "metadata": (
                    json.loads(msg.metadata_json)
                    if msg.metadata_json else None
                )
            }
            for msg in messages
        ]
    }
