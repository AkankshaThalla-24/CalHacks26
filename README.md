# AccessStream — Real-time STT Pipeline (Python)

## Phase 1: Audio Extraction (DONE, verified)
`audio_extractor.py` — pulls audio from any source, decodes to real-time
16kHz mono PCM, emits bytes via `on_audio`. Knows nothing about Deepgram.

Test it:
    python3 test_extractor.py <file-or-stream-url>
Expect ~32 KB/s and "real-time, correct format".

Requires: Python 3.9+, ffmpeg on PATH.

## Phase 2: Deepgram (scaffolded in stt_service.py)
The seam is one line:
    on_audio = lambda chunk: dg.send(chunk)
Then:
    pip install -r requirements.txt
    cp .env.example .env   # add your DEEPGRAM_API_KEY
    python3 stt_service.py <source>

## Testing with YouTube
yt-dlp resolves YouTube URLs into a direct audio stream ffmpeg can read.
    pip install yt-dlp
    python3 test_youtube.py "https://www.youtube.com/watch?v=VIDEO_ID"   # uploaded video, paced 1x
    python3 test_youtube.py "https://www.youtube.com/watch?v=LIVE_ID"    # live stream, true real-time
Auto-detects live vs uploaded. ffmpeg must be on PATH.
