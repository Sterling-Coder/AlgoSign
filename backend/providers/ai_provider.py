"""OpenAI-backed assistant. Grounded in AlgoSign's live market data.

Reads OPENAI_API_KEY from the environment (loaded from backend/.env). Uses raw
HTTP so there's no heavy SDK dependency. Model overridable via OPENAI_MODEL.
"""
from __future__ import annotations

import os

import httpx

_URL = "https://api.openai.com/v1/chat/completions"
_TIMEOUT = httpx.Timeout(40.0)


class AIProvider:
    def available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def chat(self, system: str, user: str) -> str:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return ""
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        r = httpx.post(
            _URL,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.4,
                "max_tokens": 700,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
