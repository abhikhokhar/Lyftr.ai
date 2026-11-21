
import os
import time

from dotenv import load_dotenv
import litellm
from litellm import completion

load_dotenv()

litellm.cache = litellm.Cache(type="local")

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "gemini/gemini-3.1-flash-lite"
)

API_KEYS = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]

ENABLE_FAILURE_SIMULATION = (
    os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower()
    == "true"
)

ALLOWED_FAILURE_STATUSES = {429, 500, 502, 503}


def parse_simulated_failures(header_value):
    """Parse the X-Simulate-Failure header."""

    failures = {}

    if not ENABLE_FAILURE_SIMULATION or not header_value:
        return failures

    for item in header_value.split(","):
        try:
            key_id, status = item.strip().split("=", 1)
            status = int(status)

            if status not in ALLOWED_FAILURE_STATUSES:
                raise ValueError("Unsupported failure status")

            failures[key_id.strip()] = status

        except ValueError:
            raise ValueError(
                "Invalid X-Simulate-Failure header format"
            )

    return failures


def generate_response(messages: list, simulate_failure=None):
    """
    Generate an AI response using LiteLLM.

    Tries API keys sequentially and supports
    request-specific simulated failures.
    """

    if not API_KEYS:
        raise RuntimeError("No LLM API keys configured.")

    simulated_failures = parse_simulated_failures(
        simulate_failure
    )

    errors = []

    for index, api_key in enumerate(API_KEYS):

        key_id = f"key_{index + 1}"
        start_time = time.perf_counter()

        simulated_status = simulated_failures.get(
            key_id,
            simulated_failures.get("*")
        )

        if simulated_status is not None:
            errors.append(
                f"{key_id}: simulated {simulated_status}"
            )

            print(
                f"{key_id} simulated failure: "
                f"HTTP {simulated_status}"
            )
            continue

        try:
            print(f"Trying API key {index + 1}...")

            response = completion(
                model=MODEL_NAME,
                messages=messages,
                api_key=api_key,
                max_tokens=1024,
                caching=not bool(simulated_failures)
            )

            latency_ms = int(
                (time.perf_counter() - start_time) * 1000
            )

            hidden_params = getattr(response, "_hidden_params", {}) or {}
            cache_hit = hidden_params.get("cache_hit") is True

            reply = response.choices[0].message.content

            usage = response.usage

            input_tokens = (
                usage.prompt_tokens if usage else 0
            )

            output_tokens = (
                usage.completion_tokens if usage else 0
            )

            resolution_source = (
                "LLM_CACHE" if cache_hit
                else "LIVE_INFERENCE"
            )

            print(
                f"Response source: {resolution_source}"
            )

            return {
                "reply": reply,
                "model": MODEL_NAME,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "key_id": None if cache_hit else key_id,
                "fallback_attempts": 0 if cache_hit else index,
                "cache_hit": cache_hit,
                "resolution_source": resolution_source
            }

        except Exception as error:

            error_message = str(error)

            # Never expose API keys in error logs
            for secret in API_KEYS:
                error_message = error_message.replace(
                    secret,
                    "[REDACTED]"
                )

            errors.append(
                f"{key_id}: {type(error).__name__}"
            )

            print(f"{key_id} failed.")
            print("Error type:", type(error).__name__)
            print("Error details:", error_message)

    raise RuntimeError(
        "All providers unavailable. " + "; ".join(errors)
    )
