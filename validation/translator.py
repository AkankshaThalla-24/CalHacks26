"""System under test: English sports commentary -> target sign-language gloss/grammar.

This mirrors the Claude "English -> SL grammar" step in the team architecture. The
validation agent measures the quality of this function's output.
"""

from languages import SIGN_LANGUAGES
from llm import complete

SYSTEM = (
    "You are a real-time sign-language interpreter for live sports broadcasts. "
    "You convert spoken English commentary into the gloss notation and grammar of a "
    "specific sign language so a signer or avatar can render it. Output ONLY the gloss "
    "line (signs in CAPS, no English sentences, no explanation). Keep it concise enough "
    "to sign in real time."
)


def translate(commentary: str, sl_code: str) -> str:
    sl = SIGN_LANGUAGES[sl_code]
    user = (
        f"Target sign language: {sl['name']} ({sl_code}).\n"
        f"Grammar rules to follow:\n{sl['grammar_notes']}\n\n"
        f"English commentary:\n\"{commentary}\"\n\n"
        f"Produce the {sl_code} gloss:"
    )
    return complete(SYSTEM, user, max_tokens=300)
