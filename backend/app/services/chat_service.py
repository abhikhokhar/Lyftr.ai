
import json

from sqlalchemy.orm import Session

from ..models import Message, UsageLog
from ..schemas import ChatRequest
from .llm_service import generate_response


MAX_HISTORY_MESSAGES = 20


def process_chat(
    db: Session,
    request: ChatRequest,
    simulate_failure: str | None = None
):
    try:
        history = (
            db.query(Message)
            .filter(Message.session_id == request.session_id)
            .order_by(Message.id.desc())
            .limit(MAX_HISTORY_MESSAGES)
            .all()
        )

        history.reverse()

        system_prompt = request.system_prompt or (
            "You are Lyftr AI, a helpful and intelligent AI assistant. "
            "Provide clear, accurate and concise answers."
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        for msg in history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        messages.append({
            "role": "user",
            "content": request.message
        })

        result = generate_response(
            messages,
            simulate_failure=simulate_failure
        )

        reply = result["reply"]

        metadata = {
            "resolution_source": result["resolution_source"],
            "model": result["model"],
            "latency_ms": result["latency_ms"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "key_id": result["key_id"],
            "fallback_attempts": result["fallback_attempts"],
            "cache_hit": result["cache_hit"]
        }

        user_message = Message(
            session_id=request.session_id,
            role="user",
            content=request.message
        )

        assistant_message = Message(
            session_id=request.session_id,
            role="assistant",
            content=reply,
            metadata_json=json.dumps(metadata)
        )

        usage_log = UsageLog(
            session_id=request.session_id,
            cache_hit=metadata["cache_hit"],
            model=metadata["model"],
            input_tokens=metadata["input_tokens"],
            output_tokens=metadata["output_tokens"],
            latency_ms=metadata["latency_ms"],
            resolution_source=metadata["resolution_source"]
        )

        db.add_all([
            user_message,
            assistant_message,
            usage_log
        ])

        db.commit()

        return {
            "session_id": request.session_id,
            "reply": reply,
            "metadata": metadata
        }

    except Exception:
        db.rollback()
        raise
