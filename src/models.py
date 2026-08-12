"""
Unified client for calling free-tier LLM APIs.

All three providers below have a free tier as of writing:
  - Groq        (https://console.groq.com)      -> very fast, generous free rate limits
  - Google Gemini (https://aistudio.google.com)  -> free tier via API key
  - OpenRouter  (https://openrouter.ai)          -> routes to several ":free" models

Set API keys as environment variables (see .env.example). If a key is missing,
the client falls back to MOCK MODE for that provider so the pipeline still runs
end-to-end for demoing/testing the harness without spending anything or needing
keys yet. Swap in real keys to get real benchmark numbers.
"""
import os
import time
import random
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


class ModelClient:
    """provider: 'groq' | 'gemini' | 'openrouter'"""

    def __init__(self, provider: str, model: str, label: str = None, temperature: float = 0.0):
        self.provider = provider
        self.model = model
        self.label = label or f"{provider}:{model}"
        self.temperature = temperature

    def _mock_response(self, prompt: str) -> str:
        # Use a stable digest instead of Python's process-randomized hash().
        # This keeps offline runs reproducible across machines and processes.
        seed = int.from_bytes(
            hashlib.sha256(f"{self.label}\0{prompt}".encode("utf-8")).digest()[:8],
            "big",
        )
        random.seed(seed)
        return (
            f"[MOCK RESPONSE from {self.label} — no API key set for '{self.provider}'. "
            f"This is a placeholder so the harness runs end-to-end; set the real key "
            f"in your environment to get an actual model response for: {prompt[:60]}...]"
        )

    def generate(self, prompt: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                if self.provider == "groq":
                    return self._call_groq(prompt)
                elif self.provider == "gemini":
                    return self._call_gemini(prompt)
                elif self.provider == "openrouter":
                    return self._call_openrouter(prompt)
                else:
                    raise ValueError(f"Unknown provider: {self.provider}")
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"[ERROR after {max_retries} attempts: {e}]"
                time.sleep(2 ** attempt)

    def _call_groq(self, prompt: str) -> str:
        if not GROQ_API_KEY:
            return self._mock_response(prompt)
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_openrouter(self, prompt: str) -> str:
        if not OPENROUTER_API_KEY:
            return self._mock_response(prompt)
        resp = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, prompt: str) -> str:
        if not GOOGLE_API_KEY:
            return self._mock_response(prompt)
        url = GEMINI_URL_TMPL.format(model=self.model, key=GOOGLE_API_KEY)
        resp = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": self.temperature},
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


def load_models_from_config(config: dict):
    """config: list of dicts like {"provider": "groq", "model": "llama-3.1-8b-instant", "label": "...", "temperature": 0.0}"""
    return [ModelClient(**c) for c in config]
