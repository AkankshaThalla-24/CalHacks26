import argparse
import os
import sys
import threading
import time
from dotenv import load_dotenv

from deepgram import DeepgramClient
from deepgram.core.events import EventType

from audio_extractor import AudioExtractor
from stream_resolver import resolve_stream_url

load_dotenv()

parser = argparse.ArgumentParser(description="Real-time Deepgram transcription from any audio source.")
parser.add_argument("source", nargs="?", default=os.getenv("STREAM_SOURCE", "./sample.mp3"), help="Path or URL to the audio source.")
parser.add_argument("--duration", type=float, default=None, help="Stop transcription after this many seconds.")
args = parser.parse_args()

try:
    source, info = resolve_stream_url(args.source)
    print(f"Source: {source}")
    print(f"Info: {info}\n")
except Exception as exc:
    print(f"ERROR resolving source: {exc}")
    sys.exit(1)

api_key = os.getenv("DEEPGRAM_API_KEY")
if not api_key:
    print("ERROR: DEEPGRAM_API_KEY is missing. Set it in .env or the environment.")
    sys.exit(1)

client = DeepgramClient(api_key=api_key)


def on_message(result):
    """Handle Deepgram results - called for each transcription event."""
    event_type = result.type
    if event_type == "Results":
        channel = result.channel
        alt = channel.alternatives[0]
        transcript = alt.transcript
        is_final = result.is_final

        if transcript:
            marker = "[FINAL]" if is_final else "[interim]"
            print(f"{marker} (t={result.start:.2f}s) {transcript}")


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

    def feed_audio():
        """Feed audio chunks from the extractor to Deepgram."""
        print("→ [AUDIO] thread started, waiting for OPEN event...")
        if not ready.wait(timeout=5):
            print("→ [AUDIO] ERROR: OPEN event never fired (timeout)")
            return
        
        print("→ [AUDIO] OPEN event received, starting extractor...\n")

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
        print("→ [AUDIO] stop_event received, stopping extractor and calling send_close_stream()")
        
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
