"""
Bridges stt_service.py's gloss pipeline to the browser overlay in frontend/.

Emits the WebSocket event shape frontend/stream-client.js expects, so the
two were built to need zero changes against each other:

    { clipUrl, gloss, caption, ts, lang }

One event is emitted per word (sign or fingerspell), matching how
overlay.js's playback queue advances one clip at a time. clipUrl points at
a WLASL clip served locally over HTTP (browsers can't load file:// paths);
words with no clip get clipUrl: null, which overlay.js already handles by
just showing the caption/gloss text briefly with no video.

We only have ASL data, so every event is tagged lang: "ASL" — if a viewer
picks another language in the dropdown, stream-client.js's own filter will
correctly go quiet rather than us faking translations we don't have.

Also accepts the reverse direction: /audio-in receives raw 16kHz mono
s16le PCM chunks captured live from the browser's tab audio (see
frontend/audio-capture.js) and queues them for stt_service.py to forward
to Deepgram — this is what makes "load any video in the browser" actually
transcribe that exact video, with no separate yt-dlp download needed.

Run standalone for testing:
    python pipeline_server.py
"""

import asyncio
import os
import queue
import threading
import time

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import wlasl_lookup

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_clients = set()
_loop = None
_loop_ready = threading.Event()
_audio_queue = queue.Queue()
_first_audio_received = threading.Event()


@app.on_event("startup")
async def _on_startup():
    global _loop
    _loop = asyncio.get_running_loop()
    app.mount("/clips", StaticFiles(directory=wlasl_lookup.videos_dir()), name="clips")
    _loop_ready.set()


@app.get("/")
def health():
    return {"status": "ok", "clients": len(_clients)}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _clients.add(websocket)
    try:
        while True:
            # We don't act on set_lang server-side (ASL only), but keep
            # draining incoming messages so the socket stays healthy.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)


@app.websocket("/audio-in")
async def audio_in_endpoint(websocket: WebSocket):
    """Receives raw 16kHz mono s16le PCM chunks captured from the browser's
    tab audio and queues them for stt_service.py to forward to Deepgram."""
    await websocket.accept()
    print("→ [WS] browser audio capture connected")
    try:
        while True:
            chunk = await websocket.receive_bytes()
            _audio_queue.put(chunk)
            _first_audio_received.set()
    except WebSocketDisconnect:
        print("→ [WS] browser audio capture disconnected")


def wait_for_browser_audio(timeout=None):
    """Blocks (on a plain thread) until the first real chunk of browser
    audio arrives. Lets stt_service.py delay opening the Deepgram
    connection until then, so Deepgram's own no-audio timeout never races
    against the human-paced steps of clicking the capture button and
    clicking through the browser's tab-share permission dialog."""
    return _first_audio_received.wait(timeout=timeout)


async def _broadcast(event: dict):
    dead = []
    for ws in _clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.discard(ws)


def broadcast_word(
    word: str,
    caption: str,
    clip_path: str | None,
    base_url: str = "http://localhost:8000",
    target_duration: float | None = None,
):
    """Thread-safe: call from gloss_worker (a plain Python thread), one call per word.
    target_duration is how many seconds the speaker actually took to say this
    word (roughly) — the frontend uses it to speed up playback so signing
    pace tracks speech pace instead of every clip playing at a fixed 1x."""
    if _loop is None:
        return
    clip_url = f"{base_url}/clips/{os.path.basename(clip_path)}" if clip_path else None
    event = {
        "clipUrl": clip_url,
        "gloss": word.upper(),
        "caption": caption,
        "ts": time.time(),
        "lang": "ASL",
        "targetDuration": target_duration,
    }
    asyncio.run_coroutine_threadsafe(_broadcast(event), _loop)


def start_audio_relay(on_audio, stop_event):
    """Runs on its own plain thread: pulls browser-captured PCM chunks off
    the queue and forwards each to on_audio(chunk), mirroring
    AudioExtractor's callback shape so stt_service.py's existing feed_audio
    logic (stats tracking, connection.send_media) needs no other changes."""
    def _relay():
        while not stop_event.is_set():
            try:
                chunk = _audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            on_audio(chunk)

    thread = threading.Thread(target=_relay, daemon=True)
    thread.start()
    return thread


def start_server(host="0.0.0.0", port=8000):
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    if not _loop_ready.wait(timeout=10):
        raise RuntimeError("pipeline_server failed to start within 10s")
    return server


if __name__ == "__main__":
    start_server()
    print("pipeline_server running on ws://localhost:8000/ws (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
