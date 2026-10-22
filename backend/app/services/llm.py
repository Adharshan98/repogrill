"""Talks to the LLM. Uses Groq, which follows the OpenAI chat format.

All LLM calls go through `chat()`, so switching to another provider later
means changing only this file.
"""
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.groq.com/openai/v1/chat/completions"


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

    try:
        response = httpx.post(API_URL, json=body, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise LLMError(f"LLM request failed: {e}") from e

    text = response.json()["choices"][0]["message"]["content"]
    return json.loads(text) if as_json else text
