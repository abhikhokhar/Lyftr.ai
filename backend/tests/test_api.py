
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


# Separate in-memory database for testing
TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


@pytest.fixture
def client(monkeypatch):
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Mock LLM response
    def mock_generate_response(messages, simulate_failure=None):
        return {
            "reply": "An API allows different applications to communicate.",
            "model": "gemini/gemini-3.1-flash-lite",
            "latency_ms": 100,
            "input_tokens": 20,
            "output_tokens": 12,
            "key_id": "key_1",
            "fallback_attempts": 0,
            "cache_hit": False,
            "resolution_source": "LIVE_INFERENCE"
        }

    monkeypatch.setattr(
        "app.services.chat_service.generate_response",
        mock_generate_response
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["keys_configured"] >= 0
    assert response.json()["cache_enabled"] is True


def test_valid_chat_request(client):
    response = client.post(
        "/chat",
        json={
            "session_id": "test-session-001",
            "message": "What is an API?"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["session_id"] == "test-session-001"
    assert data["reply"] == (
        "An API allows different applications to communicate."
    )
    assert data["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert data["metadata"]["input_tokens"] == 20
    assert data["metadata"]["output_tokens"] == 12


def test_empty_message_returns_422(client):
    response = client.post(
        "/chat",
        json={
            "session_id": "test-session-002",
            "message": ""
        }
    )

    assert response.status_code == 422


def test_whitespace_message_returns_422(client):
    response = client.post(
        "/chat",
        json={
            "session_id": "test-session-003",
            "message": "    "
        }
    )

    assert response.status_code == 422


def test_missing_session_id_returns_422(client):
    response = client.post(
        "/chat",
        json={
            "message": "Hello"
        }
    )

    assert response.status_code == 422


def test_provider_failure_returns_503(client, monkeypatch):
    def mock_failure(messages, simulate_failure=None):
        raise RuntimeError("All providers unavailable")

    monkeypatch.setattr(
        "app.services.chat_service.generate_response",
        mock_failure
    )

    response = client.post(
        "/chat",
        json={
            "session_id": "failure-session",
            "message": "Hello"
        }
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "all providers unavailable"


def test_chat_history_endpoint(client):
    client.post(
        "/chat",
        json={
            "session_id": "history-session",
            "message": "What is an API?"
        }
    )

    response = client.get(
        "/sessions/history-session/messages"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["session_id"] == "history-session"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


def test_unknown_session_returns_404(client):
    response = client.get(
        "/sessions/unknown-session/messages"
    )

    assert response.status_code == 404


def test_session_isolation(client):
    client.post(
        "/chat",
        json={
            "session_id": "session-A",
            "message": "Message for A"
        }
    )

    client.post(
        "/chat",
        json={
            "session_id": "session-B",
            "message": "Message for B"
        }
    )

    response_a = client.get(
        "/sessions/session-A/messages"
    )

    response_b = client.get(
        "/sessions/session-B/messages"
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    messages_a = response_a.json()["messages"]
    messages_b = response_b.json()["messages"]

    assert len(messages_a) == 2
    assert len(messages_b) == 2

    assert messages_a[0]["content"] == "Message for A"
    assert messages_b[0]["content"] == "Message for B"
