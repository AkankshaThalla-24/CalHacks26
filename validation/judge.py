"""Claude-as-judge: score one translation across all 5 metrics in a single call."""

from languages import SIGN_LANGUAGES
from llm import complete_json
from metrics import METRICS

SYSTEM = (
    "You are a strict bilingual evaluator of sign-language gloss translations for live "
    "sports. You grade objectively on a 1-5 integer scale (1=very poor, 5=excellent) and "
    "return strict JSON only."
)


def _rubric_block() -> str:
    return "\n".join(f"- {k}: {desc}" for k, desc in METRICS.items())


def judge(commentary: str, gloss: str, sl_code: str) -> dict:
    sl = SIGN_LANGUAGES[sl_code]
    metric_keys = ", ".join(METRICS.keys())
    user = (
        f"Target sign language: {sl['name']} ({sl_code}).\n"
        f"Grammar reference:\n{sl['grammar_notes']}\n\n"
        f"Original English commentary:\n\"{commentary}\"\n\n"
        f"Candidate {sl_code} gloss to evaluate:\n\"{gloss}\"\n\n"
        f"Score each metric 1-5:\n{_rubric_block()}\n\n"
        "Return strict JSON of the form:\n"
        '{"scores": {' + ", ".join(f'"{k}": <int>' for k in METRICS) + "}, "
        '"notes": "<one short sentence on the main weakness, or \'none\'>"}\n'
        f"Use exactly these score keys: {metric_keys}."
    )
    result = complete_json(SYSTEM, user, max_tokens=600)
    scores = {k: int(result.get("scores", {}).get(k, 0)) for k in METRICS}
    return {"scores": scores, "notes": result.get("notes", "")}
