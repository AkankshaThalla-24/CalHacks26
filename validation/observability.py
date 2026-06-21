"""
Optional Arize Phoenix observability layer for the validation harness.

What it adds (without touching your judge logic):
  - traces every translate -> judge cycle as a span (commentary, gloss, language)
  - logs your 5 metric scores + notes onto that span
  - gives you a live UI: score distributions, per-language breakdown,
    click into any failing translation to see the gloss and the judge's note

Design: this is a NO-OP if phoenix isn't installed or PHOENIX is disabled, so
the harness runs identically with or without it. Turn it on with:
    pip install arize-phoenix arize-phoenix-otel openinference-instrumentation-anthropic
    export USE_PHOENIX=1
    python agent.py

Then open the Phoenix UI (printed at startup, default http://localhost:6006).
"""

import os
import uuid

_ENABLED = os.environ.get("USE_PHOENIX", "").lower() in ("1", "true", "yes")

_px = None
_tracer = None
_session_url = None
_rows = []  # collected per-case eval rows -> logged as SpanEvaluations at the end


def enabled() -> bool:
    return _ENABLED and _px is not None


def init():
    """Launch/attach Phoenix and instrument Anthropic. Safe to call once."""
    global _px, _tracer, _session_url
    if not _ENABLED:
        return
    try:
        import phoenix as px
        from phoenix.otel import register

        # launch a local Phoenix app (no API key, no cloud needed)
        session = px.launch_app()
        _session_url = getattr(session, "url", "http://localhost:6006")

        # register a tracer + auto-instrument Anthropic calls
        tracer_provider = register(project_name="asl-validation", auto_instrument=True)
        _tracer = tracer_provider.get_tracer(__name__)
        _px = px
        print(f"[phoenix] tracing ON — open the UI: {_session_url}")
    except Exception as exc:  # noqa: BLE001
        # never let observability break the actual eval run
        print(f"[phoenix] disabled (init failed: {exc})")
        _px = None


def case_span(sl_code: str, scenario: str, commentary: str):
    """Context manager wrapping one case so translate+judge land in one span.
    Returns a (span, span_id) tuple-like helper; degrades to a dummy if off."""
    if not enabled() or _tracer is None:
        return _Dummy()
    return _Span(_tracer, sl_code, scenario, commentary)


def record(span_id: str, sl_code: str, scenario: str, commentary: str,
           gloss: str, scores: dict, notes: str, case_avg: float):
    """Stash one row to be logged to Phoenix as evaluations at the end."""
    if not enabled():
        return
    row = {
        "context.span_id": span_id,
        "sl_code": sl_code,
        "scenario": scenario,
        "case_avg": case_avg,
        "notes": notes,
    }
    row.update({f"score.{k}": v for k, v in scores.items()})
    _rows.append(row)


def flush():
    """Log all collected scores onto their spans and print the UI url."""
    if not enabled() or not _rows:
        return
    try:
        import pandas as pd
        from phoenix.client import Client

        df = pd.DataFrame(_rows).set_index("context.span_id")
        client = Client()

        # one annotation per metric so each shows as its own column in the UI
        score_cols = [c for c in df.columns if c.startswith("score.")]
        for col in score_cols:
            name = col.replace("score.", "")
            eval_df = df[[col]].rename(columns={col: "score"})
            client.spans.log_span_annotations_dataframe(
                dataframe=eval_df, annotation_name=name, annotator_kind="LLM"
            )

        # also log the overall case average
        avg_df = df[["case_avg"]].rename(columns={"case_avg": "score"})
        client.spans.log_span_annotations_dataframe(
            dataframe=avg_df, annotation_name="overall_avg", annotator_kind="LLM"
        )
        print(f"[phoenix] logged {len(_rows)} cases across {len(score_cols)} metrics.")
        if _session_url:
            print(f"[phoenix] explore results: {_session_url}")
    except Exception as exc:  # noqa: BLE001
        print(f"[phoenix] flush failed (non-fatal): {exc}")


def shutdown():
    """Cleanly close the local Phoenix server so its SQLite temp file isn't
    still open when Python's exit-time tempfile cleanup runs (otherwise
    Windows raises a noisy, harmless PermissionError on process exit)."""
    if not enabled():
        return
    try:
        _px.close_app()
    except Exception:  # noqa: BLE001
        pass  # best-effort — never let shutdown break the run


# ---- internal span helpers ----

class _Dummy:
    """No-op span used when Phoenix is off."""
    span_id = ""
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Span:
    def __init__(self, tracer, sl_code, scenario, commentary):
        self._tracer = tracer
        self._attrs = {
            "sl_code": sl_code, "scenario": scenario,
            "input.value": commentary,
        }
        self._cm = None
        self.span_id = ""

    def __enter__(self):
        self._cm = self._tracer.start_as_current_span("translate_and_judge")
        span = self._cm.__enter__()
        for k, v in self._attrs.items():
            span.set_attribute(k, v)
        # capture the span_id so we can attach evals to it later
        ctx = span.get_span_context()
        self.span_id = format(ctx.span_id, "016x")
        self._span = span
        return self

    def set_output(self, gloss: str):
        if hasattr(self, "_span"):
            self._span.set_attribute("output.value", gloss)

    def __exit__(self, *a):
        return self._cm.__exit__(*a)
