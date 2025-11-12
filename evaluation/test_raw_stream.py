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

    interesting_events = []

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8') if isinstance(line, bytes) else line

            # Parse SSE format
            if line_str.startswith('data:'):
                try:
                    json_str = line_str[5:].strip()
                    data = json.loads(json_str)

                    event_type = data.get('type')

                    # Collect interesting events
                    if event_type in ['text-delta', 'tool-output', 'finish', 'message']:
                        interesting_events.append(data)

                except json.JSONDecodeError:
                    pass

    print("INTERESTING EVENTS:")
    print("=" * 60)
    for i, event in enumerate(interesting_events[:5]):  # Show first 5
        print(f"\nEvent {i+1}:")
        print(json.dumps(event, indent=2))

except Exception as e:
    print(f"Error: {e}")
