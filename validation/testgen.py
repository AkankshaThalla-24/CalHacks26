"""Auto-generate sports-commentary test cases for each sign language."""

import json
import os

from languages import SCENARIOS, SIGN_LANGUAGES
from llm import complete_json

HERE = os.path.dirname(__file__)
TESTCASE_DIR = os.path.join(HERE, "testcases")

SYSTEM = (
    "You generate realistic live football (soccer) commentary snippets for testing a "
    "sign-language translation system. Each snippet is 1-2 sentences as a broadcaster "
    "would actually say it during a live match. Return strict JSON."
)


def generate_for_language(sl_code: str, per_scenario: int = 1) -> list[dict]:
    sl = SIGN_LANGUAGES[sl_code]
    scenarios = ", ".join(SCENARIOS)
    user = (
        f"Generate live commentary test snippets covering these scenarios: {scenarios}.\n"
        f"Produce {per_scenario} snippet(s) per scenario.\n"
        'Return a JSON array of objects: '
        '[{"scenario": "...", "commentary": "..."}].\n'
        "Make them vivid and specific (real-sounding team/player names, scores, minutes)."
    )
    items = complete_json(SYSTEM, user, max_tokens=2000)
    cases = []
    for i, it in enumerate(items):
        cases.append(
            {
                "id": f"{sl_code}-{i:02d}",
                "sl_code": sl_code,
                "sl_name": sl["name"],
                "scenario": it.get("scenario", ""),
                "commentary": it.get("commentary", ""),
            }
        )
    return cases


def generate_all(per_scenario: int = 1) -> dict[str, list[dict]]:
    os.makedirs(TESTCASE_DIR, exist_ok=True)
    out = {}
    for sl_code in SIGN_LANGUAGES:
        print(f"  [testgen] generating cases for {sl_code} ...")
        cases = generate_for_language(sl_code, per_scenario=per_scenario)
        with open(os.path.join(TESTCASE_DIR, f"{sl_code}.json"), "w", encoding="utf-8") as f:
            json.dump(cases, f, indent=2, ensure_ascii=False)
        out[sl_code] = cases
    return out
