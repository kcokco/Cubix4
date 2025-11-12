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
    print(f"Status Code: {response.status_code}\n")

    collected_text = ""

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line

            # Parse SSE format: "data: {...json...}"
            if line_str.startswith('data:'):
                try:
                    json_str = line_str[5:].strip()  # Remove "data:" prefix
                    data = json.loads(json_str)

                    # Look for text delta events
                    if data.get('type') == 'text-delta':
                        text_delta = data.get('textDelta', '')
                        collected_text += text_delta
                        print(f"[TEXT DELTA]: {text_delta}")
                    elif data.get('type') == 'tool-output':
                        print(f"[TOOL OUTPUT]: {data.get('output', '')[:100]}...")
                    elif data.get('type') == 'finish':
                        print(f"[FINISH]: {data}")

                except json.JSONDecodeError:
                    pass

    print("\n" + "=" * 60)
    print("COLLECTED TEXT:")
    print("=" * 60)
    print(collected_text if collected_text else "No text collected")

except Exception as e:
    print(f"Error: {e}")
