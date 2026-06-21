# AccessStream — Real-time ASL Interpretation Pipeline

Converts any video or audio source into a live ASL sign sequence for Deaf viewers.

```
Audio/Video source
    → audio_extractor.py   (raw PCM bytes)
    → stt_service.py       (Deepgram → transcript text, buffered into utterances)
    → gloss_pipeline.py    (Claude → ASL sign/fingerspell steps, verified against WLASL)
    → sign_window.py       (native window, plays clips back-to-back)
```

## Files

- `audio_extractor.py` — pulls audio from any source (local file, HLS, RTMP, HTTP stream), decodes to real-time 16kHz mono PCM, emits bytes via `on_audio`.
- `stream_resolver.py` — resolves YouTube / yt-dlp-supported URLs into something ffmpeg can consume. `download=True` downloads first to avoid truncating the first few words.
- `stt_service.py` — feeds PCM bytes to Deepgram, buffers fragments into complete utterances (on `speech_final`), sends each to `gloss_pipeline`, and streams the result into `sign_window`.
- `prompt.py` — builds the Claude system prompt. Claude freely picks the simplest common English word per concept; no fixed vocabulary list.
- `validator.py` — validates the shape of Claude's JSON output (well-formed steps), not vocabulary membership.
- `gloss_pipeline.py` — calls Claude to convert a transcript string into sign/fingerspell steps, then checks each "sign" step against `wlasl_lookup` and demotes unmatched ones to fingerspelling.
- `wlasl_lookup.py` — looks up a gloss word directly against a local WLASL dataset (`WLASL_v0.3.json` + `videos/`) on every call. No pre-curation step.
- `sign_window.py` — small native OpenCV window that plays clips back-to-back as words are enqueued (`SignWindow.enqueue(text)`); words with no clip get a brief on-screen placeholder.
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

4. Run the full pipeline on any source:
   ```
   python stt_service.py <file-or-stream-url>
   python stt_service.py "https://www.youtube.com/watch?v=VIDEO_ID" --duration 20 --download
   ```

## Next steps

- Pass rolling context (previous utterance) into `gloss_pipeline.process_transcript(context=...)` for better continuity across sentences.
- Add a real fingerspelling clip set (currently fingerspell steps just show a text placeholder, no per-letter clips).
