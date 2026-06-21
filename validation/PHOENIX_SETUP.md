# Adding Arize Phoenix (optional eval dashboard)

Your LLM-as-judge harness is unchanged. Phoenix is a thin observability layer
on top: it traces each translate→judge cycle and logs your 5 metric scores so
you get a live UI — score distributions, per-language breakdown, and click-into
any failing translation to see its gloss + the judge's note.

## Run WITHOUT Phoenix (default, unchanged)
    python agent.py --per 2

## Run WITH Phoenix
    pip install arize-phoenix arize-phoenix-otel openinference-instrumentation-anthropic pandas
    export USE_PHOENIX=1
    python agent.py --per 2
Then open the UI url it prints (default http://localhost:6006).

## What judges see
- every translation traced as a span (commentary in, gloss out)
- 5 metric scores attached to each span as evaluations
- overall_avg column to sort worst-first
- filter by language, click a low scorer, read the judge's failure note

## How it's wired (so you can explain it)
- observability.py: all Phoenix logic, no-ops if USE_PHOENIX!=1 or not installed
- agent.py: wraps the translate+judge cycle in obs.case_span(), calls
  obs.record() per case and obs.flush() at the end
- your judge.py / metrics.py / rubric are untouched — Phoenix logs YOUR scores,
  it does not replace your judge
