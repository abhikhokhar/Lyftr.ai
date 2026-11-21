
from types import SimpleNamespace

import pytest

from app.services import llm_service


def mock_response(cache_hit=False):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="This is a test response."
                )
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=20,
            completion_tokens=10
        ),
        _hidden_params={"cache_hit": cache_hit}
    )


def test_key_failover_to_second_key(monkeypatch):
    monkeypatch.setattr(
        llm_service, "API_KEYS", ["fake-key-1", "fake-key-2"]
    )
    monkeypatch.setattr(
        llm_service, "ENABLE_FAILURE_SIMULATION", True
    )

    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return mock_response()

    monkeypatch.setattr(
        llm_service, "completion", fake_completion
    )

    result = llm_service.generate_response(
        [{"role": "user", "content": "Hello"}],
        simulate_failure="key_1=429"
    )

    assert len(calls) == 1
    assert calls[0]["api_key"] == "fake-key-2"
    assert result["key_id"] == "key_2"
    assert result["fallback_attempts"] == 1
    assert result["resolution_source"] == "LIVE_INFERENCE"


def test_all_keys_fail(monkeypatch):
    monkeypatch.setattr(
        llm_service, "API_KEYS", ["fake-key-1", "fake-key-2"]
    )
    monkeypatch.setattr(
        llm_service, "ENABLE_FAILURE_SIMULATION", True
    )

    with pytest.raises(RuntimeError, match="All providers unavailable"):
        llm_service.generate_response(
            [{"role": "user", "content": "Hello"}],
            simulate_failure="*=429"
        )


def test_cache_hit_metadata(monkeypatch):
    monkeypatch.setattr(
        llm_service, "API_KEYS", ["fake-key-1"]
    )
    monkeypatch.setattr(
        llm_service, "ENABLE_FAILURE_SIMULATION", False
    )

    def fake_completion(**kwargs):
        return mock_response(cache_hit=True)

    monkeypatch.setattr(
        llm_service, "completion", fake_completion
    )

    result = llm_service.generate_response(
        [{"role": "user", "content": "Hello"}]
    )

    assert result["cache_hit"] is True
    assert result["resolution_source"] == "LLM_CACHE"
    assert result["key_id"] is None
    assert result["fallback_attempts"] == 0


def test_simulated_failure_disables_caching(monkeypatch):
    monkeypatch.setattr(
        llm_service, "API_KEYS", ["fake-key-1", "fake-key-2"]
    )
    monkeypatch.setattr(
        llm_service, "ENABLE_FAILURE_SIMULATION", True
    )

    calls = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return mock_response()

    monkeypatch.setattr(
        llm_service, "completion", fake_completion
    )

    llm_service.generate_response(
        [{"role": "user", "content": "Hello"}],
        simulate_failure="key_1=429"
    )

    assert len(calls) == 1
    assert calls[0]["api_key"] == "fake-key-2"
    assert calls[0]["caching"] is False
