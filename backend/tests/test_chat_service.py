
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Message, UsageLog
from app.schemas import ChatRequest
from app.services import chat_service


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def mock_llm_response():
    return {
        "reply": "This is a test AI response.",
        "model": "gemini/gemini-3.1-flash-lite",
        "latency_ms": 100,
        "input_tokens": 20,
        "output_tokens": 12,
        "key_id": "key_1",
        "fallback_attempts": 0,
        "cache_hit": False,
        "resolution_source": "LIVE_INFERENCE"
    }


def test_process_chat_saves_messages_and_usage(db, monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "generate_response",
        lambda messages, simulate_failure=None: mock_llm_response()
    )

    request = ChatRequest(
        session_id="test-session",
        message="Hello"
    )

    result = chat_service.process_chat(db, request)

    assert result["reply"] == "This is a test AI response."

    messages = (
        db.query(Message)
        .filter(Message.session_id == "test-session")
        .order_by(Message.id.asc())
        .all()
    )

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"

    saved_metadata = json.loads(messages[1].metadata_json)

    assert saved_metadata["resolution_source"] == "LIVE_INFERENCE"
    assert saved_metadata["input_tokens"] == 20
    assert saved_metadata["output_tokens"] == 12

    usage = db.query(UsageLog).filter(
        UsageLog.session_id == "test-session"
    ).first()

    assert usage is not None
    assert usage.cache_hit is False
    assert usage.model == "gemini/gemini-3.1-flash-lite"



def test_process_chat_includes_previous_history(db, monkeypatch):
    captured_calls = []

    def fake_generate_response(messages, simulate_failure=None):
        captured_calls.append(messages)
        return mock_llm_response()

    monkeypatch.setattr(
        chat_service,
        "generate_response",
        fake_generate_response
    )

    # First message
    chat_service.process_chat(
        db,
        ChatRequest(
            session_id="history-session",
            message="What is Python?"
        )
    )

    # Second message in the same session
    chat_service.process_chat(
        db,
        ChatRequest(
            session_id="history-session",
            message="What is it used for?"
        )
    )

    # Inspect only the second LLM request
    second_call = captured_calls[1]

    assert second_call[0]["role"] == "system"

    assert second_call[1] == {
        "role": "user",
        "content": "What is Python?"
    }

    assert second_call[2] == {
        "role": "assistant",
        "content": "This is a test AI response."
    }

    assert second_call[3] == {
        "role": "user",
        "content": "What is it used for?"
    }
