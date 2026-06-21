"""Validation agent orchestrator.

Pipeline: generate test cases -> translate (system under test) -> judge -> report.

Usage:
    export ANTHROPIC_API_KEY=...
    python agent.py                 # 1 case per scenario per language
    python agent.py --per 2         # 2 cases per scenario

    # with Arize Phoenix live dashboard (optional):
    pip install arize-phoenix arize-phoenix-otel openinference-instrumentation-anthropic
    export USE_PHOENIX=1
    python agent.py
"""

import argparse
from statistics import mean

from judge import judge
from report import build_report
from testgen import generate_all
from translator import translate
import observability as obs


def run(per_scenario: int = 1) -> str:
    obs.init()  # no-op unless USE_PHOENIX=1 and phoenix is installed

    print("[1/3] Generating test cases ...")
    cases_by_sl = generate_all(per_scenario=per_scenario)
    total = sum(len(v) for v in cases_by_sl.values())
    print(f"      {total} cases across {len(cases_by_sl)} languages.")

    print("[2/3] Translating + judging ...")
    results = []
    done = 0
    for sl_code, cases in cases_by_sl.items():
        for case in cases:
            with obs.case_span(sl_code, case["scenario"], case["commentary"]) as span:
                gloss = translate(case["commentary"], sl_code)
                if hasattr(span, "set_output"):
                    span.set_output(gloss)
                verdict = judge(case["commentary"], gloss, sl_code)
                scores = verdict["scores"]
                case_avg = round(mean(scores.values()), 2)

                obs.record(
                    span_id=getattr(span, "span_id", ""),
                    sl_code=sl_code,
                    scenario=case["scenario"],
                    commentary=case["commentary"],
                    gloss=gloss,
                    scores=scores,
                    notes=verdict["notes"],
                    case_avg=case_avg,
                )

            results.append(
                {
                    "sl_code": sl_code,
                    "scenario": case["scenario"],
                    "commentary": case["commentary"],
                    "gloss": gloss,
                    "scores": scores,
                    "notes": verdict["notes"],
                    "case_avg": case_avg,
                }
            )
            done += 1
            print(f"      [{done}/{total}] {sl_code} {case['scenario']} -> avg {results[-1]['case_avg']}")

    print("[3/3] Building report ...")
    path = build_report(results)
    obs.flush()  # push scores to Phoenix UI (no-op if off)
    print(f"Done. Report written to: {path}")
    obs.shutdown()  # release the local Phoenix server before exit (no-op if off)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=1, help="test cases per scenario per language")
    args = ap.parse_args()
    run(per_scenario=args.per)
