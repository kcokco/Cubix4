import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env from parent directory
load_dotenv("../ai-sdk-rag-starter/.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"API Key loaded: {OPENAI_API_KEY[:20]}..." if OPENAI_API_KEY else "No API key found")

try:
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10
    )
    print("[SUCCESS] OpenAI API key is valid!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"[ERROR] OpenAI API error: {e}")
