import requests
import json

API_URL = "http://localhost:3000/api/chat"

payload = {
    "messages": [
        {"role": "user", "content": "test"}
    ]
}

print("Making request to API...")
try:
    response = requests.post(API_URL, json=payload, timeout=10, stream=True)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print("\nResponse body:")

    if response.status_code == 500:
        print("Server returned 500 error")
        body = response.text
        if body:
            print(f"Error body: {body}")
        else:
            print("No error body returned (empty response)")

        # Try to get more details
        print("\nRaw response:")
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                print(chunk)
    else:
        for line in response.iter_lines():
            if line:
                print(line.decode('utf-8'))

except Exception as e:
    print(f"Error: {e}")
