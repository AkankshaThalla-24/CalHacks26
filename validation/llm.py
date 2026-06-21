"""Thin Anthropic client wrapper shared by the agent's components."""

import json
import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

# Load secrets from the project-root .env (one level up from validation/).
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(_HERE), ".env"), override=True)

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

_client = None


def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


def complete(system: str, user: str, max_tokens: int = 1500) -> str:
    """Single-turn completion, returns the text of the first content block."""
    msg = client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def complete_json(system: str, user: str, max_tokens: int = 1500):
    """Completion that must return JSON. Strips ```json fences and parses."""
    raw = complete(system, user, max_tokens=max_tokens)
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    # Grab the outermost JSON object/array if there's surrounding prose.
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1)
    return json.loads(cleaned)
