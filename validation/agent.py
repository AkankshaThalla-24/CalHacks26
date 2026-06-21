"""Validation agent orchestrator.

Pipeline: generate test cases -> translate (system under test) -> judge -> report.

Usage:
    export ANTHROPIC_API_KEY=...
    python agent.py                 # 1 case per scenario per language
    python agent.py --per 2         # 2 cases per scenario
"""

import argparse
from statistics import mean

from judge import judge
from report import build_report
from testgen import generate_all
from translator import translate


def run(per_scenario: int = 1) -> str:
    print("[1/3] Generating test cases ...")
    cases_by_sl = generate_all(per_scenario=per_scenario)
    total = sum(len(v) for v in cases_by_sl.values())
    print(f"      {total} cases across {len(cases_by_sl)} languages.")

    print("[2/3] Translating + judging ...")
    results = []
    done = 0
    for sl_code, cases in cases_by_sl.items():
        for case in cases:
            gloss = translate(case["commentary"], sl_code)
            verdict = judge(case["commentary"], gloss, sl_code)
            scores = verdict["scores"]
            results.append(
                {
                    "sl_code": sl_code,
                    "scenario": case["scenario"],
                    "commentary": case["commentary"],
                    "gloss": gloss,
                    "scores": scores,
                    "notes": verdict["notes"],
                    "case_avg": round(mean(scores.values()), 2),
                }
            )
            done += 1
            print(f"      [{done}/{total}] {sl_code} {case['scenario']} -> avg {results[-1]['case_avg']}")

    print("[3/3] Building report ...")
    path = build_report(results)
    print(f"Done. Report written to: {path}")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=1, help="test cases per scenario per language")
    args = ap.parse_args()
    run(per_scenario=args.per)
