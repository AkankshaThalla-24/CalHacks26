# AccessStream — Real-time ASL Interpretation Pipeline

Converts any video or audio source into a live ASL sign sequence for Deaf viewers.

```
Audio source (file/URL, or live browser tab capture)
    → audio_extractor.py   (raw PCM bytes)            \_ stt_service.py picks one
    → pipeline_server.py    (live browser audio relay) /
    → stt_service.py       (Deepgram → transcript text, buffered into utterances)
    → gloss_pipeline.py    (Claude → ASL sign/fingerspell steps, verified against WLASL)
    → pipeline_server.py   (WebSocket broadcast + WLASL clips served over HTTP)
    → frontend/            (browser overlay plays the clips, in sync with the video)
```

## Files

- `audio_extractor.py` — pulls audio from any source (local file, HLS, RTMP, HTTP stream), decodes to real-time 16kHz mono PCM, emits bytes via `on_audio`. Used when `stt_service.py` is given a file/URL directly.
- `stream_resolver.py` — resolves YouTube / yt-dlp-supported URLs into something ffmpeg can consume. `download=True` downloads first to avoid truncating the first few words.
- `stt_service.py` — feeds PCM bytes to Deepgram (from `audio_extractor` or, with `--from-browser`, from live browser tab audio via `pipeline_server`), buffers fragments into complete utterances (on `speech_final`), sends each to `gloss_pipeline`, and broadcasts the result over WebSocket.
- `prompt.py` — builds the Claude system prompt. Claude freely picks the simplest common English word per concept; no fixed vocabulary list.
- `validator.py` — validates the shape of Claude's JSON output (well-formed steps), not vocabulary membership.
- `gloss_pipeline.py` — calls Claude to convert a transcript string into sign/fingerspell steps, then checks each "sign" step against `wlasl_lookup` and demotes unmatched ones to fingerspelling.
- `wlasl_lookup.py` — looks up a gloss word directly against a local WLASL dataset (`WLASL_v0.3.json` + `videos/`) on every call. No pre-curation step.
- `pipeline_server.py` — FastAPI/WebSocket bridge. Serves WLASL clips over HTTP at `/clips/<id>.mp4`, broadcasts `{clipUrl, gloss, caption, ts, lang}` events per word to `frontend/` over `/ws`, and (in `--from-browser` mode) receives live PCM from `frontend/audio-capture.js` over `/audio-in`.
- `frontend/` — the browser overlay (see its own section below) that actually displays the sign clips, draggable/resizable on top of the YouTube player.
- `sign_window.py` — standalone native OpenCV window for local testing/debugging without a browser (`python sign_window.py "GOAL TEAM"` or `--file glosses.txt`). Not used by the live `stt_service.py` pipeline anymore — the browser overlay is the real output now.
- `glosses.txt` — a sample word list for testing `sign_window.py --file glosses.txt` directly.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set API keys in `.env`:
   ```
   DEEPGRAM_API_KEY=...
   ANTHROPIC_API_KEY=...
   ```

3. Point `wlasl_lookup.py` at your local WLASL dataset (defaults to `C:\Users\hp\Downloads\wlasl-processed`, override with the `WLASL_DIR` env var):
   ```
   WLASL_DIR=/path/to/wlasl-processed
   ```

4. Run it directly on a file/URL (prints transcripts/gloss; nothing to watch unless you also open `frontend/`):
   ```
   python stt_service.py <file-or-stream-url>
   python stt_service.py "https://www.youtube.com/watch?v=VIDEO_ID" --duration 20 --download
   ```

   Or run it against **live browser audio** (the real demo path — see "Frontend overlay" below):
   ```
   python stt_service.py --from-browser --duration 60
   ```

5. Open the overlay (separate terminal):
   ```
   cd frontend && python -m http.server 5500
   ```
   Go to `http://localhost:5500`, load any YouTube video via the picker, click **Start audio capture**, and pick "This Tab" + check "Share tab audio" in the browser's permission dialog. The overlay plays signs live, matching whatever's actually playing in that tab.

## Next steps

- Pass rolling context (previous utterance) into `gloss_pipeline.process_transcript(context=...)` for better continuity across sentences.
- Add a real fingerspelling clip set (currently fingerspell steps just show a text placeholder, no per-letter clips).

---

# Live Sports · Sign-Language Accessibility (team scope)

Three pieces toward the team's goal — a sign-language layer that live-translates match
commentary for Deaf and hard-of-hearing fans.

| Piece | Folder | What it does |
|---|---|---|
| Validation agent | `validation/` | Auto-generates test commentary for 5 sign languages, runs the translator, grades each output on 5 metrics with Claude-as-judge, writes a report. |
| Frontend overlay | `frontend/` | Web app embedding a YouTube live with a translucent, draggable, resizable sign-language video overlay you can place in any corner; switch among ASL/BSL/LSF/CSL/JSL. |
| Real pipeline | `stt_service.py` + `pipeline_server.py` | The working backend — Deepgram → Claude gloss → WLASL clips, broadcast to the overlay over WebSocket. Replaces the old mock pipeline entirely (ASL only for now; BSL/LSF/CSL/JSL in the dropdown are unimplemented). |

Sign languages: **ASL, BSL, LSF (French), CSL (Chinese), JSL (Japanese)**.

---

## 1. Validation agent

```bash
cd validation
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
# optional: export ANTHROPIC_MODEL=claude-sonnet-4-5
python agent.py            # 1 test case per scenario per language
python agent.py --per 2    # more cases
```

Output: `validation/reports/validation_report.md` — a table of **5 languages × 5 metrics**
(grammatical accuracy, semantic accuracy, completeness, gloss validity, real-time fluency),
overall scores, and the weakest cases flagged.

**Pipeline:** `testgen.py` (writes cases) → `translator.py` (the system under test:
English → SL gloss) → `judge.py` (Claude-as-judge, 1–5 per metric) → `report.py`.

## 2. Frontend overlay

```bash
cd frontend
python -m http.server 5500
# open http://localhost:5500
```

- Change the match: set `window.YT_VIDEO_ID` (in `youtube.js`) to any YouTube video/live id.
- Point at a different pipeline: set `window.PIPELINE_WS` (default `ws://localhost:8000/ws`).
- Drag the overlay by its header, resize from the bottom-right handle, place it in any corner
  with the corner picker, switch sign language with the dropdown.

## 3. Real pipeline (replaces the old mock)

```bash
python stt_service.py --from-browser
```

Starts `pipeline_server.py` automatically (no separate process needed). Emits one
clip event per gloss word:
```json
{ "clipUrl": "http://localhost:8000/clips/24872.mp4", "gloss": "GOAL", "caption": "the team scored a goal", "ts": 0, "lang": "ASL" }
```

## Demo

`demo.md` — a ~2-minute narrated walkthrough.

---

### Quick full-demo run order
1. Terminal A: `python stt_service.py --from-browser` (waits for browser audio; starts `pipeline_server` on port 8000)
2. Terminal B: `cd frontend && python -m http.server 5500`
3. Browser: `http://localhost:5500` → load a video, click **Start audio capture**, share the tab's audio → live signing overlay.
4. (Separately) `cd validation && python agent.py` → show the quality report.

### Notes / known gaps
- Only ASL is implemented (via the WLASL dataset) — BSL/LSF/CSL/JSL exist in the
  language dropdown but have no backing clips or translation yet.
- `gloss_pipeline.py` picks plain English words and verifies them live against
  the local WLASL clip set — no pre-built clip library or Midjourney/Redis step.
