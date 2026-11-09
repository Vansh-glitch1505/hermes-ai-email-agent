import os

from dotenv import load_dotenv
from openai import OpenAI


# =========================================================
# LOAD API KEY
# =========================================================

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY not found in .env"
    )


# =========================================================
# OPENROUTER CLIENT
# =========================================================

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


# =========================================================
# ONE SMALL TEST
# =========================================================

MODEL_NAME = "qwen/qwen3.8-27b:free"

print("\nTesting OpenRouter model...")
print("Model:", MODEL_NAME)

response = client.chat.completions.create(
    model="google/gemma-4-31b-it:free",
    messages=[
        {
            "role": "user",
            "content": "Reply with exactly: OPENROUTER_OK"
        }
    ],
    max_tokens=10
)


# =========================================================
# RESULT
# =========================================================

message = response.choices[0].message

print("\nFinish reason:")
print(response.choices[0].finish_reason)

print("\nResponse:")
print(repr(message.content))

print("\nTest complete.")