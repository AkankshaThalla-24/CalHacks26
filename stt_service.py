import argparse
import os
import queue
import sys
import threading
import time
from dotenv import load_dotenv

# When stdout isn't a real console (piped, redirected to a file), Windows
# falls back to the cp1252 codepage, which can't encode the Unicode arrow
# glyphs used throughout these logs. Force UTF-8 so this script behaves
# the same whether run interactively or redirected.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from deepgram import DeepgramClient
from deepgram.core.events import EventType

from audio_extractor import AudioExtractor
from stream_resolver import resolve_stream_url
from gloss_pipeline import process_transcript
import pipeline_server
import wlasl_lookup

load_dotenv()

parser = argparse.ArgumentParser(description="Real-time Deepgram transcription from any audio source.")
parser.add_argument("source", nargs="?", default=os.getenv("STREAM_SOURCE", "./sample.mp3"), help="Path or URL to the audio source. Ignored with --from-browser.")
parser.add_argument("--duration", type=float, default=None, help="Stop transcription after this many seconds.")
parser.add_argument("--download", action="store_true", help="Download audio locally first (no start truncation; best for demos).")
parser.add_argument("--from-browser", action="store_true", help="Receive live audio captured by frontend/audio-capture.js instead of downloading a source.")
args = parser.parse_args()

if args.from_browser:
    source, info = None, {"is_live": True, "title": "(browser tab capture)"}
    print("Waiting for browser tab audio on ws://localhost:8000/audio-in ...\n")
else:
    try:
        source, info = resolve_stream_url(args.source, download=args.download)
        print(f"Source: {source}")
        print(f"Info: {info}\n")
    except Exception as exc:
        print(f"ERROR resolving source: {exc}")
        sys.exit(1)

api_key = os.getenv("DEEPGRAM_API_KEY")
if not api_key:
    print("ERROR: DEEPGRAM_API_KEY is missing. Set it in .env or the environment.")
    sys.exit(1)

if not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY is missing. Set it in .env or the environment.")
    sys.exit(1)

pipeline_server.start_server()
print("→ [WS] pipeline_server listening on ws://localhost:8000/ws (frontend/ connects here)")

if args.from_browser:
    # Deepgram closes the connection if it gets no audio within ~10-12s of
    # opening. That's far less time than a human needs to switch to the
    # browser tab, click "Start audio capture", and click through Chrome's
    # tab-share permission dialog. So in browser mode we wait HERE — before
    # ever opening the Deepgram connection — until real audio has actually
    # started arriving, removing that race entirely.
    print("→ [AUDIO] waiting for you to click \"Start audio capture\" in the browser...")
    if not pipeline_server.wait_for_browser_audio(timeout=600):
        print("→ [AUDIO] ERROR: no browser audio received within 10 minutes. Exiting.")
        sys.exit(1)
    print("→ [AUDIO] browser audio detected — connecting to Deepgram now.\n")

client = DeepgramClient(api_key=api_key)

# Utterance buffering: Deepgram fires is_final on internal endpointing flushes
# (often mid-sentence fragments), but speech_final marks a true pause. We
# accumulate is_final fragments and send the joined utterance to the gloss
# pipeline once speech_final fires, OR once MAX_BUFFER_SECONDS of buffered
# speech piles up without one (continuous commentary over crowd noise often
# never produces a clean enough pause for Deepgram to call speech_final).
MAX_BUFFER_SECONDS = 6.0
transcript_buffer = []
utterance_duration = {"total": 0.0}  # seconds of actual speech in the buffered utterance
gloss_queue = queue.Queue()
GLOSS_STOP = object()


def gloss_worker():
    """Consumes complete utterances, converts them to ASL gloss steps, and
    broadcasts the resulting words to the browser overlay over WebSocket.
    Spreads the utterance's real spoken duration evenly across its gloss
    words so playback speed roughly tracks how fast the speaker talked,
    instead of every clip playing at a fixed (slow) 1x regardless of pace."""
    while True:
        item = gloss_queue.get()
        if item is GLOSS_STOP:
            break
        text, duration = item
        try:
            steps = process_transcript(text)
        except Exception as e:
            print(f"→ [GLOSS] error converting {text!r}: {e}")
            continue
        if steps is None:
            print(f"→ [GLOSS] no valid gloss for: {text!r}")
            continue

        print(f"→ [GLOSS] {text!r} -> {steps}")
        words = [s["id"] if s["type"] == "sign" else s["text"] for s in steps]
        target_per_word = (duration / len(words)) if words and duration > 0 else None
        for word in words:
            pipeline_server.broadcast_word(word, text, wlasl_lookup.find(word), target_duration=target_per_word)


def on_message(result):
    """Handle Deepgram results - called for each transcription event."""
    event_type = result.type
    if event_type == "Results":
        channel = result.channel
        alt = channel.alternatives[0]
        transcript = alt.transcript
        is_final = result.is_final
        speech_final = result.speech_final

        if transcript:
            marker = "[FINAL]" if is_final else "[interim]"
            print(f"{marker} (t={result.start:.2f}s) {transcript}")

        if is_final and transcript:
            transcript_buffer.append(transcript)
            utterance_duration["total"] += result.duration

        # speech_final relies on Deepgram detecting a clean pause. Continuous
        # commentary over crowd noise often never produces one, so without a
        # fallback the buffer would grow forever and nothing would ever reach
        # the gloss pipeline. Force a flush once enough speech has piled up.
        max_buffer_reached = utterance_duration["total"] >= MAX_BUFFER_SECONDS
        if (speech_final or max_buffer_reached) and transcript_buffer:
            utterance = " ".join(transcript_buffer).strip()
            duration = utterance_duration["total"]
            transcript_buffer.clear()
            utterance_duration["total"] = 0.0
            if utterance:
                reason = "speech_final" if speech_final else "max buffer reached"
                print(f"→ [GLOSS] queuing utterance ({reason}): {utterance!r} (spoken in {duration:.2f}s)")
                gloss_queue.put((utterance, duration))


def on_error(error):
    """Handle errors."""
    print(f"→ [EVENT] ERROR: {error}")


def on_close(_=None):
    """Handle connection close."""
    print("→ [EVENT] CLOSE - connection closed by server")



with client.listen.v1.connect(
    model="nova-3",
    language="en",
    encoding="linear16",
    sample_rate=16000,
    channels=1,
) as connection:
    ready = threading.Event()
    stop_event = threading.Event()
    
    send_stats = {"bytes": 0, "chunks": 0, "start": None, "last_log": 0}

    # Register event handlers
    connection.on(EventType.OPEN, lambda _: (print("→ [EVENT] OPEN - connection is ready"), ready.set()))
    connection.on(EventType.MESSAGE, on_message)
    connection.on(EventType.ERROR, on_error)
    connection.on(EventType.CLOSE, on_close)

    # Worker processes gloss conversion off the Deepgram socket thread so a
    # slow Claude call never stalls reading the next transcription frame.
    gloss_thread = threading.Thread(target=gloss_worker, daemon=True)
    gloss_thread.start()

    def feed_audio():
        """Feed audio chunks to Deepgram, from either ffmpeg (AudioExtractor)
        or live browser tab-capture (pipeline_server), depending on mode."""
        print("→ [AUDIO] thread started, waiting for OPEN event...")
        if not ready.wait(timeout=5):
            print("→ [AUDIO] ERROR: OPEN event never fired (timeout)")
            return

        print("→ [AUDIO] OPEN event received, starting audio source...\n")

        def on_audio_chunk(chunk):
            now = time.monotonic()
            if send_stats["start"] is None:
                send_stats["start"] = now
                send_stats["last_log"] = now
                print(f"→ [SEND] first chunk received, starting transmission")

            send_stats["bytes"] += len(chunk)
            send_stats["chunks"] += 1
            connection.send_media(chunk)

            # Log progress every second
            if now - send_stats["last_log"] >= 1.0:
                elapsed = now - send_stats["start"]
                print(f"→ [SEND] {send_stats['chunks']} chunks, {send_stats['bytes']/1024:.1f}KB sent, {elapsed:.1f}s")
                send_stats["last_log"] = now

        extractor = None
        if args.from_browser:
            pipeline_server.start_audio_relay(on_audio_chunk, stop_event)
        else:
            extractor = AudioExtractor(
                source=source,
                on_audio=on_audio_chunk,
                on_end=lambda: print("→ [EXTRACTOR] audio stream ended"),
                on_error=lambda e: print(f"→ [EXTRACTOR] error: {e}"),
                realtime=not info.get("is_live", False),
            ).start()

        # Wait for stop signal from timer or user input
        print("→ [AUDIO] waiting for stop_event...")
        stop_event.wait()
        print("→ [AUDIO] stop_event received, stopping audio source and calling send_close_stream()")

        if extractor is not None:
            extractor.stop()

        if send_stats["start"] is not None:
            elapsed = time.monotonic() - send_stats["start"]
            print(f"→ [AUDIO] stopped: {send_stats['chunks']} chunks, {send_stats['bytes']/1024:.1f}KB total, {elapsed:.1f}s")

        # NOW signal to Deepgram that we're done sending audio
        print("→ [AUDIO] calling connection.send_close_stream() to signal end of audio")
        try:
            connection.send_close_stream()
            print("→ [AUDIO] connection.send_close_stream() returned successfully")
        except Exception as e:
            print(f"→ [AUDIO] send_close_stream() failed: {e}")

    # Start audio feed in background thread
    audio_thread = threading.Thread(target=feed_audio, daemon=True)
    audio_thread.start()

    # Set up stop mechanism (either timer or user input)
    if args.duration is not None:
        def stop_after_duration():
            print(f"→ [TIMER] sleeping for {args.duration}s...")
            time.sleep(args.duration)
            if not stop_event.is_set():
                print(f"→ [TIMER] {args.duration}s duration reached, setting stop_event")
                stop_event.set()
            else:
                print(f"→ [TIMER] stop_event already set")

        stop_thread = threading.Thread(target=stop_after_duration, daemon=True)
        stop_thread.start()
    else:
        def stop_on_user_input():
            input("\n→ [INPUT] Press Enter to stop transcription.\n")
            stop_event.set()

        input_thread = threading.Thread(target=stop_on_user_input, daemon=True)
        input_thread.start()

    # Block on start_listening() until connection.send_close_stream() is called
    print("→ [MAIN] Calling connection.start_listening() (blocks until send_close_stream() is called)...\n")
    try:
        connection.start_listening()
    except Exception as e:
        print(f"→ [MAIN] start_listening() raised exception: {e}")

    print("\n→ [MAIN] connection.start_listening() returned. Transcription complete.")

    # No more on_message calls will fire past this point (single-threaded
    # read loop already exited), so it's safe to flush any trailing
    # fragment that never got a speech_final boundary.
    if transcript_buffer:
        leftover = " ".join(transcript_buffer).strip()
        leftover_duration = utterance_duration["total"]
        transcript_buffer.clear()
        if leftover:
            print(f"→ [GLOSS] queuing trailing utterance: {leftover!r}")
            gloss_queue.put((leftover, leftover_duration))

    print("→ [MAIN] waiting for gloss queue to drain...")
    gloss_queue.put(GLOSS_STOP)
    gloss_thread.join(timeout=30)
    print("→ [MAIN] gloss processing complete.")