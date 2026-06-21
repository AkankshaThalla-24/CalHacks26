"""Aggregate evaluation results into a markdown report."""

import os
from datetime import datetime
from statistics import mean

from metrics import METRICS, PASS_THRESHOLD

HERE = os.path.dirname(__file__)
REPORT_DIR = os.path.join(HERE, "reports")


def _avg(values):
    return round(mean(values), 2) if values else 0.0


def build_report(results: list[dict]) -> str:
    """results: list of {sl_code, scenario, commentary, gloss, scores{}, notes, case_avg}."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    metric_keys = list(METRICS.keys())
    sl_codes = sorted({r["sl_code"] for r in results})

    lines = []
    lines.append("# Sign-Language Translation — Validation Report")
    lines.append("")
    lines.append(f"_Generated: {datetime.now():%Y-%m-%d %H:%M}_")
    lines.append("")
    lines.append(
        f"Languages: **{', '.join(sl_codes)}** · Test cases: **{len(results)}** · "
        f"Metrics: **{len(metric_keys)}** · Pass threshold: **{PASS_THRESHOLD}/5**"
    )
    lines.append("")

    # Per-language x per-metric summary table.
    lines.append("## Summary — average score per language × metric")
    lines.append("")
    header = "| Language | " + " | ".join(metric_keys) + " | **Overall** | Pass rate |"
    sep = "|" + "---|" * (len(metric_keys) + 3)
    lines.append(header)
    lines.append(sep)

    overall_all = []
    for sl in sl_codes:
        rows = [r for r in results if r["sl_code"] == sl]
        cells = []
        for m in metric_keys:
            cells.append(f"{_avg([r['scores'][m] for r in rows]):.2f}")
        overall = _avg([r["case_avg"] for r in rows])
        overall_all.extend([r["case_avg"] for r in rows])
        pass_rate = sum(1 for r in rows if r["case_avg"] >= PASS_THRESHOLD) / len(rows)
        lines.append(
            f"| {sl} | " + " | ".join(cells) + f" | **{overall:.2f}** | {pass_rate*100:.0f}% |"
        )
    lines.append("")
    lines.append(f"**Overall system score: {_avg(overall_all):.2f}/5**")
    lines.append("")

    # Weakest cases.
    failing = sorted(
        [r for r in results if r["case_avg"] < PASS_THRESHOLD], key=lambda r: r["case_avg"]
    )
    lines.append("## Failing / weakest cases")
    lines.append("")
    if not failing:
        lines.append("_None — all cases met the threshold._")
    else:
        for r in failing[:10]:
            lines.append(f"- **{r['sl_code']}** ({r['scenario']}) — avg {r['case_avg']:.2f}")
            lines.append(f"  - EN: {r['commentary']}")
            lines.append(f"  - Gloss: `{r['gloss']}`")
            lines.append(f"  - Judge: {r['notes']}")
    lines.append("")

    # Full appendix.
    lines.append("## Appendix — all cases")
    lines.append("")
    for sl in sl_codes:
        lines.append(f"### {sl}")
        lines.append("")
        for r in [x for x in results if x["sl_code"] == sl]:
            scoretxt = ", ".join(f"{m}={r['scores'][m]}" for m in metric_keys)
            lines.append(f"- _{r['scenario']}_ (avg {r['case_avg']:.2f})")
            lines.append(f"  - EN: {r['commentary']}")
            lines.append(f"  - Gloss: `{r['gloss']}`")
            lines.append(f"  - Scores: {scoretxt}")
        lines.append("")

    report = "\n".join(lines)
    path = os.path.join(REPORT_DIR, "validation_report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return path
