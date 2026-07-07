from config import GEMINI_API_KEY, MODEL_NAME

import httpx
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"


request = {
    "contents": [
        {
            "role": "user",
            "parts": [{"text": "What is the capital of Africa"}]
        }
    ]
}
response = httpx.post(URL,json=request)
print(response.status_code)
print(response.json())