"""
LLM Client for Agent Reasoning & Collaboration.
Directly interfaces with Google Gemini or OpenAI APIs using the key from .env,
with graceful fallback to calibrated clinical heuristics if no key is provided.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from .config import get_gemini_api_key, get_openai_api_key, get_llm_provider, get_llm_model


class LLMClient:
    """
    Unified client for LLM-powered clinical reasoning and multi-agent dialogue.
    """

    def __init__(self):
        self.gemini_key = get_gemini_api_key()
        self.openai_key = get_openai_api_key()
        self.provider = get_llm_provider()
        self.model = get_llm_model()

    def is_api_configured(self) -> bool:
        return bool(self.gemini_key or self.openai_key)

    def get_status_summary(self) -> Dict[str, Any]:
        has_gemini = bool(self.gemini_key and len(self.gemini_key) > 5)
        has_openai = bool(self.openai_key and len(self.openai_key) > 5)
        
        status_mode = "LIVE_LLM_CONNECTED" if (has_gemini or has_openai) else "AUTONOMOUS_HEURISTIC"
        active_provider = "Google Gemini" if has_gemini else ("OpenAI" if has_openai else "Clinical Heuristic Engine")
        
        return {
            "status": status_mode,
            "provider": active_provider,
            "model": self.model if (has_gemini or has_openai) else "Deterministic Clinical Solver",
            "has_gemini_key": has_gemini,
            "has_openai_key": has_openai,
            "active": has_gemini or has_openai
        }

    def generate_reasoning(self, system_prompt: str, prompt: str, temperature: float = 0.2) -> Optional[Dict[str, Any]]:
        """
        Generates clinical reasoning for an agent using live LLM.
        Returns None if offline or if API call fails, allowing heuristic fallback.
        """
        # 1. Try Google Gemini API if key is available
        if self.gemini_key and len(self.gemini_key) > 5:
            try:
                res = self._call_gemini(system_prompt, prompt, temperature)
                if res:
                    return {"text": res, "source": "GEMINI_LIVE", "model": self.model}
            except Exception as e:
                # Log and fallback gracefully
                pass

        # 2. Try OpenAI API if key is available
        if self.openai_key and len(self.openai_key) > 5:
            try:
                res = self._call_openai(system_prompt, prompt, temperature)
                if res:
                    return {"text": res, "source": "OPENAI_LIVE", "model": self.model}
            except Exception as e:
                pass

        return None

    def _call_gemini(self, system_prompt: str, user_prompt: str, temperature: float) -> Optional[str]:
        """
        Invokes Google Gemini REST API using standard library urllib.
        """
        # Supports models: gemini-2.5-flash, gemini-1.5-flash, gemini-1.5-pro
        model_name = self.model if "gemini" in self.model else "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"System Context:\n{system_prompt}\n\nTask:\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 500
            }
        }
        
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        return None

    def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float) -> Optional[str]:
        """
        Invokes OpenAI REST API using standard library urllib.
        """
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model if "gpt" in self.model else "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 500
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        return None


# Global singleton instance
llm_client = LLMClient()
