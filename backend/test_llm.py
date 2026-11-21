
from app.services.llm_service import generate_response

messages = [
    {
        "role": "user",
        "content": "Explain what an API is in two simple sentences."
    }
]

try:
    result = generate_response(messages)

    print("\n========== LLM TEST RESULT ==========")
    print("Reply:", result["reply"])
    print("Model:", result["model"])
    print("Latency:", result["latency_ms"], "ms")
    print("Input tokens:", result["input_tokens"])
    print("Output tokens:", result["output_tokens"])
    print("Successful key:", result["key_id"])
    print("Fallback attempts:", result["fallback_attempts"])
    print("Resolution:", result["resolution_source"])

except Exception as error:
    print("LLM test failed:", error)
