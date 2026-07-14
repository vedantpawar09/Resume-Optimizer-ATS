"""
Thin, resilient client for the Groq chat-completions API (OpenAI-compatible).

All AI calls in the app (ATS analysis, resume rewriting, interview question
generation, mock interview scoring) go through this single client so that
retries, timeouts, JSON-repair, and error logging are handled in one place.
"""
import json
import logging
import re
import time

import requests
from django.conf import settings

logger = logging.getLogger('resume_optimizer')


class GroqAPIError(Exception):
    pass


class GroqClient:
    def __init__(self, api_key=None, model=None, timeout=60):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.url = settings.GROQ_API_URL
        self.timeout = timeout

    def _headers(self):
        if not self.api_key:
            raise GroqAPIError(
                "No Groq API key configured. Add GROQ_API_KEY to your .env file "
                "or set it in Settings > Groq API Key inside the app."
            )
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def chat(self, system_prompt: str, user_prompt: str, temperature=0.4,
             max_tokens=4000, json_mode=False, retries=2):
        """Send a single-turn chat completion request to Groq."""
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if json_mode:
            payload['response_format'] = {'type': 'json_object'}

        last_error = None
        for attempt in range(retries + 1):
            try:
                resp = requests.post(self.url, headers=self._headers(), json=payload, timeout=self.timeout)
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("Groq rate-limited, retrying in %ss", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = data['choices'][0]['message']['content']
                return content
            except requests.exceptions.RequestException as exc:
                last_error = exc
                logger.warning("Groq request failed (attempt %s/%s): %s", attempt + 1, retries + 1, exc)
                time.sleep(1 + attempt)
        raise GroqAPIError(f"Groq API request failed after retries: {last_error}")

    def chat_json(self, system_prompt: str, user_prompt: str, temperature=0.3, max_tokens=4000):
        """Chat call that expects and repairs-parses a JSON object response."""
        raw = self.chat(system_prompt, user_prompt, temperature=temperature,
                         max_tokens=max_tokens, json_mode=True)
        return self._parse_json(raw)

    @staticmethod
    def _parse_json(raw: str):
        raw = raw.strip()
        raw = re.sub(r'^```(json)?', '', raw).strip()
        raw = re.sub(r'```$', '', raw).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError as exc:
                    raise GroqAPIError(f"Groq returned malformed JSON: {exc}") from exc
            raise GroqAPIError("Groq response did not contain valid JSON.")
