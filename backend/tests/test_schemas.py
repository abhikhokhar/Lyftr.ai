
import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest


def test_valid_chat_request():
    request = ChatRequest(
        session_id="session-001",
        message="What is an API?"
    )

    assert request.session_id == "session-001"
    assert request.message == "What is an API?"


def test_whitespace_is_trimmed():
    request = ChatRequest(
        session_id="  session-001  ",
        message="  Explain APIs  "
    )

    assert request.session_id == "session-001"
    assert request.message == "Explain APIs"


def test_empty_message_is_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="session-001",
            message=""
        )


def test_whitespace_message_is_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="session-001",
            message="     "
        )


def test_empty_session_id_is_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="",
            message="Hello"
        )


def test_session_id_length_limit():
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="s" * 129,
            message="Hello"
        )


def test_message_length_limit():
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="session-001",
            message="a" * 4001
        )


def test_optional_system_prompt():
    request = ChatRequest(
        session_id="session-001",
        message="Hello",
        system_prompt="Be concise."
    )

    assert request.system_prompt == "Be concise."
