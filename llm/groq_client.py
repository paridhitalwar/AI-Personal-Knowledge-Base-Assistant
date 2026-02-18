from typing import List

import requests

from app.config import settings


class GroqClient:
    """Minimal Groq LLM client for chat-style completions."""

    def __init__(self, model: str = "llama-3.1-8b-instant") -> None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set in the environment.")
        self.api_key = settings.groq_api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    def chat(self, system_prompt: str, user_content: str, history: List[dict] = None) -> str:
        """Send a chat completion request and return the assistant message content."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history if provided (excluding system/tool messages if any)
        if history:
            # Simple sanitization to ensure only user/assistant roles are passed if needed
            # For now, just append them.
            messages.extend(history)
            
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }

        response = requests.post(self.base_url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        choices: List[dict] = data.get("choices", [])
        if not choices:
            return ""

        return choices[0]["message"]["content"]

