import os
import litellm

from pathlib import Path
from dotenv import load_dotenv
from litellm import completion

# Load backend .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# Read configured API keys
api_keys = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]

if not api_keys:
    raise ValueError("No API keys found in LLM_API_KEYS")

print("LiteLLM version:", __import__("importlib.metadata", fromlist=["version"]).version("litellm"))
print("Configured API keys:", len(api_keys))

# Enable local caching
litellm.cache = litellm.Cache(type="local")

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is an API? Explain in one sentence."}
]

for i in range(2):
    response = completion(
        model="gemini/gemini-3.1-flash-lite",
        messages=messages,
        api_key=api_keys[0],
        max_tokens=1024,
        caching=True
    )

    print(f"\nRequest {i + 1}")
    print("Cache metadata:", response._hidden_params)
    print("Reply:", response.choices[0].message.content)