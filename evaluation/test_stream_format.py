import requests
import json

API_URL = "http://localhost:3000/api/chat"

payload = {
    "messages": [
        {
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": "What can I make with chickpeas?"
                }
            ]
        }
    ]
}

print("Making request to API...")
try:
    response = requests.post(API_URL, json=payload, timeout=30, stream=True)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print("\nStreaming response:")
    print("=" * 60)

    line_count = 0
    for line in response.iter_lines():
        if line:
            line_count += 1
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
            print(f"Line {line_count}: {line_str[:200]}")  # Print first 200 chars

            if line_count >= 10:  # Show first 10 lines
                print("... (truncated)")
                break

    if line_count == 0:
        print("No lines received!")

except Exception as e:
    print(f"Error: {e}")
