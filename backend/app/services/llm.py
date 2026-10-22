"""Talks to the LLM. Uses Groq, which follows the OpenAI chat format.

All LLM calls go through `chat()`, so switching to another provider later
means changing only this file.
"""
import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_RETRIES = 3


class LLMError(Exception):
    pass


def chat(system: str, user: str, as_json: bool = False) -> str | dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your-key-here":
        raise LLMError("GROQ_API_KEY is missing. Add it to backend/.env")

    body = {
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.4,
    }
    if as_json:
        body["response_format"] = {"type": "json_object"}

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = httpx.post(API_URL, json=body, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
        except httpx.HTTPError as e:
            raise LLMError(f"LLM request failed: {e}") from e

        # 429 = rate limit hit (free plan allows ~8000 tokens per minute). Wait as long as Groq asks, then retry.
        if response.status_code == 429 and attempt < MAX_RETRIES:
            time.sleep(min(float(response.headers.get("retry-after", 10)), 60))
            continue
        if response.status_code != 200:
            raise LLMError(f"LLM request failed with status {response.status_code}: {response.text[:200]}")
        break

    text = response.json()["choices"][0]["message"]["content"]
    if not as_json:
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError("LLM returned invalid JSON") from e
