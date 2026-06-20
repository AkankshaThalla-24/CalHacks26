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
