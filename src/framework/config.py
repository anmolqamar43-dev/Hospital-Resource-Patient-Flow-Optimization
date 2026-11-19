"""
Environment configuration loader and API key manager.
Loads variables from .env file with zero external dependencies.
"""

import os
import re
from typing import Dict, Optional


def load_env_file(filepath: Optional[str] = None) -> Dict[str, str]:
    """
    Parses a .env file and loads variables into os.environ.
    Handles comments, empty lines, and single/double quoted values.
    """
    if filepath is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        filepath = os.path.join(base_dir, ".env")

    env_vars = {}
    if not os.path.exists(filepath):
        return env_vars

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Match KEY=VALUE
                match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
                if match:
                    key = match.group(1).strip()
                    val = match.group(2).strip()

                    # Strip outer quotes if any
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]

                    env_vars[key] = val
                    # Populate into os.environ if not already set by system
                    if key not in os.environ or not os.environ[key]:
                        os.environ[key] = val
    except Exception as e:
        print(f"[Config] Note: Error reading .env file: {e}")

    return env_vars


# Automatically load on module import
_loaded_env = load_env_file()


def get_gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def get_openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def get_llm_provider() -> str:
    if get_gemini_api_key():
        return "gemini"
    if get_openai_api_key():
        return "openai"
    return os.environ.get("LLM_PROVIDER", "heuristic").strip().lower()


def get_llm_model() -> str:
    provider = get_llm_provider()
    default_model = "gemini-2.5-flash" if provider == "gemini" else "gpt-4o-mini"
    return os.environ.get("LLM_MODEL", default_model).strip()


def get_server_port() -> int:
    try:
        return int(os.environ.get("PORT", "8080"))
    except ValueError:
        return 8080


def get_live_interval_seconds() -> float:
    try:
        return float(os.environ.get("LIVE_SIMULATION_INTERVAL_SEC", "4.0"))
    except ValueError:
        return 4.0
