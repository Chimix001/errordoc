from __future__ import annotations
import json
import os
from typing import Any

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

DEFAULT_SKIP_DIRS: tuple[str, ...] = (
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "build", "dist", "site-packages", ".idea", ".vscode",
)

DEFAULT_PROTECTED_GLOBS: tuple[str, ...] = (
    ".git/**", ".git", ".env", ".env.*", "*.pem", "*.key", "*.p12",
    "id_rsa*", "id_ed25519*", "secrets/**", "**/secrets/**",
    "config/local_settings.py",
)

REQUIRED_KEYS = ("description", "fix")


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_object(text: str) -> str:
    """Fallback: pull the first {...} block if the model wrapped JSON in prose."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")
    return text[start : end + 1]


def parse_response(response_text: str) -> dict[str, Any]:
    cleaned = _strip_code_fences(response_text)
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = json.loads(_extract_json_object(cleaned))

    if not isinstance(result, dict):
        raise ValueError("The LLM response must be a JSON object.")
    missing = [k for k in REQUIRED_KEYS if k not in result]
    if missing:
        raise ValueError(f"LLM response missing keys: {missing}")
    if not isinstance(result["description"], str) or not isinstance(result["fix"], str):
        raise ValueError("'description' and 'fix' must both be strings.")
    return result


def _build_system_prompt(user_message: str, source_code: str) -> str:
    skip = ", ".join(DEFAULT_SKIP_DIRS)
    protected = ", ".join(DEFAULT_PROTECTED_GLOBS)
    return f"""You are a software-engineering CLI agent that reviews and fixes Python code in a repository.

Rules:
- Only reason about files under the repo root, except for the skip directories below.
- Never write to the protected paths below, even if they match a write glob.

Directories to NEVER inspect: {skip}
Paths to NEVER write: {protected}

Respond with a single JSON object and nothing else (no prose, no markdown fences):
{{
  "description": "<what is wrong and why>",
  "fix": "<the corrected code or precise patch instructions>"
}}

USER REQUEST:
{user_message}

SOURCE CODE:
{source_code}
"""


def get_llm_suggestion(user_message: str, source_code: str) -> dict[str, Any]:
    system_prompt = _build_system_prompt(user_message, source_code)
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    errors: list[str] = []

    if groq_key:
        try:
            llm = ChatGroq(model="openai/gpt-oss-120b", api_key=groq_key)
            return parse_response(llm.invoke(system_prompt).content)
        except Exception as exc:
            errors.append(f"Groq failed: {exc}")
            print("Groq failed, trying Gemini...")

    if gemini_key:
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_key)
            return parse_response(llm.invoke(system_prompt).content)
        except Exception as exc:
            errors.append(f"Gemini failed: {exc}")

    raise RuntimeError(
        "No LLM provider could generate a valid suggestion.\n" + "\n".join(errors)
        if errors
        else "No LLM provider configured. Set GROQ_API_KEY and/or GEMINI_API_KEY."
    )