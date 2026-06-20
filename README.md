# ASL gloss mapping — Deepgram text to sign sequence

Converts cleaned commentary text into a sequence of real sign clip IDs
(or fingerspell instructions) using Claude, constrained to a fixed
clip vocabulary so it can never invent a sign that doesn't exist.

## Files

- `clip_library.py` — the fixed list of valid sign IDs. Replace this
  with your team's real recorded clip list as soon as it exists.
- `prompt.py` — builds the system prompt that constrains Claude to
  the clip library.
- `validator.py` — checks Claude's JSON output against the clip
  library before it's allowed downstream. This is the safety net.
- `test_commentary.json` — sample commentary lines to test against.
- `run_test.py` — calls the real Claude API on each test line and
  validates the output. **This is the one you run.**
- `simulated_outputs.json` / `validate_simulated.py` — a hand-built
  dry run used before a real API key was available. Not needed once
  `run_test.py` works, kept for reference.

## Setup

1. Install the SDK:
   ```
   pip install anthropic
   ```

2. Set your API key as an environment variable:
   ```
   export ANTHROPIC_API_KEY=sk-ant-...
   ```
   Get a key from https://console.anthropic.com if you don't have one.

3. Run it:
   ```
   python3 run_test.py
   ```

This prints each test line, the gloss output Claude produced, and
whether it passed validation. Results also get written to
`results.json`.

## Next steps to wire this into the real pipeline

- Swap `clip_library.py` for the actual recorded clip IDs.
- Swap `test_commentary.json` for live Deepgram output (or keep using
  it as a regression test as you change the prompt).
- On validation failure, decide your fallback now: drop the invalid
  step and continue (simplest), fall back to fingerspelling the whole
  phrase, or show captions-only for that utterance.
- If you add Browserbase match context (player names, team names),
  pass it into `run_test.py`'s user message alongside the transcript
  so Claude knows which words are names to fingerspell vs. unknown
  words to map or drop.
