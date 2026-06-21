# AccessStream — Real-time ASL Interpretation Pipeline

Converts any video or audio source into a live ASL sign sequence for Deaf viewers.

```
Audio/Video source
    → audio_extractor.py   (raw PCM bytes)
    → stt_service.py       (Deepgram → transcript text)
    → gloss_pipeline.py    (Claude → ASL sign/fingerspell steps)
    → render clips
```

## Files

- `audio_extractor.py` — pulls audio from any source (local file, HLS, RTMP, HTTP stream), decodes to real-time 16kHz mono PCM, emits bytes via `on_audio`.
- `stream_resolver.py` — resolves YouTube / yt-dlp-supported URLs into something ffmpeg can consume.
- `stt_service.py` — feeds PCM bytes to Deepgram and emits transcript strings in real time.
- `clip_library.py` — the fixed vocabulary of valid ASL sign IDs. Replace with your team's actual recorded clip list.
- `prompt.py` — builds the Claude system prompt constrained to the clip library.
- `validator.py` — validates every sign ID in Claude's output against the clip library. The hard safety gate.
- `gloss_pipeline.py` — calls Claude to convert a transcript string into a JSON sequence of sign/fingerspell steps.

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

3. Run the STT service on any source:
   ```
   python3 stt_service.py <file-or-stream-url>
   python3 stt_service.py "https://www.youtube.com/watch?v=VIDEO_ID"
   ```

## Next steps

- Wire `stt_service.py` transcript output directly into `gloss_pipeline.process_transcript()`.
- Swap `clip_library.py` for the actual recorded clip IDs once they exist.
- Decide fallback on validation failure: drop the step, fingerspell the whole phrase, or show captions-only.
- Pass video context (speaker names, topic) into `gloss_pipeline.process_transcript(context=...)` so Claude knows what to fingerspell vs. map.


# Live Sports · Sign-Language Accessibility (my scope)

Three pieces toward the team's goal — a sign-language layer that live-translates match
commentary for Deaf and hard-of-hearing fans.

| Piece | Folder | What it does |
|---|---|---|
| Validation agent | `validation/` | Auto-generates test commentary for 5 sign languages, runs the translator, grades each output on 5 metrics with Claude-as-judge, writes a report. |
| Frontend overlay | `frontend/` | Web app embedding a YouTube live with a translucent, draggable, resizable sign-language video overlay you can place in any corner; switch among ASL/BSL/LSF/CSL/JSL. |
| Mock pipeline | `mock-pipeline/` | Stands in for Deepgram→Claude→Midjourney→Redis; streams clip events over WebSocket so the overlay demos standalone. |

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

## 3. Mock pipeline (for the demo)

```bash
cd mock-pipeline
pip install -r requirements.txt
uvicorn server:app --port 8000
```

Emits one clip event every few seconds:
```json
{ "clipUrl": "...mp4", "gloss": "TIME 67 MESSI SCORE GOAL", "caption": "GOAL! Messi...", "ts": 0, "lang": "ASL" }
```
The real pipeline emits the **same shape** — swap the WS URL and the overlay needs no changes.

## Demo

`demo.md` — a ~2-minute narrated walkthrough.

---

### Quick full-demo run order
1. Terminal A: `cd mock-pipeline && uvicorn server:app --port 8000`
2. Terminal B: `cd frontend && python -m http.server 5500`
3. Browser: `http://localhost:5500` → live match + signing overlay; switch languages and corners.
4. (Separately) `cd validation && python agent.py` → show the quality report.

### Notes / known swaps for the real system
- `SAMPLE_CLIP` in `mock-pipeline/server.py` is a placeholder MP4 — replace with real
  generated sign clips (or Redis-served media).
- The architecture's Midjourney step emits **images**; the overlay's `<video>` plays MP4.
  Keep the clip library as the source of truth for sign video, or render images to short clips.