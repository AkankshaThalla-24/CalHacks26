import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic
from prompt import build_system_prompt
from validator import validate_gloss_output
import wlasl_lookup

load_dotenv()

_client = Anthropic()
_system_prompt = build_system_prompt()

MAX_RETRIES = 1


def _resolve_against_dictionary(steps):
    """Demote any 'sign' step with no matching WLASL clip to fingerspelling,
    so the returned steps accurately reflect what can actually be played."""
    resolved = []
    for step in steps:
        if step["type"] == "sign" and wlasl_lookup.find(step["id"]) is None:
            resolved.append({"type": "fingerspell", "text": step["id"]})
        else:
            resolved.append(step)
    return resolved


def process_transcript(text: str, context: str = None):
    if not text or not text.strip():
        return None

    user_message = f'Transcript: "{text.strip()}"'
    if context:
        user_message += f"\nContext: {context}"

    for attempt in range(MAX_RETRIES + 1):
        try:
            t0 = time.perf_counter()
            response = _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=_system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            latency_ms = (time.perf_counter() - t0) * 1000
            print(f"[gloss_pipeline] latency: {latency_ms:.0f}ms (attempt {attempt})")
            raw_text = response.content[0].text.strip()
            steps = json.loads(raw_text)
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            print(f"[gloss_pipeline] parse error on attempt {attempt}: {e}")
            continue

        is_valid, errors = validate_gloss_output(steps)
        if is_valid:
            return _resolve_against_dictionary(steps)
        else:
            print(f"[gloss_pipeline] invalid output on attempt {attempt}: {errors}")

    print(f"[gloss_pipeline] giving up on: {text!r}")
    return None
