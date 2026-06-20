"""
Real-time audio extractor (Python).

Pulls audio from ANY source (local file, HLS .m3u8, RTMP, http stream),
decodes it to raw 16kHz mono signed-16-bit PCM, and hands you the bytes
as they arrive — paced to real time.

It knows NOTHING about Deepgram. It just emits bytes. That's the seam:
later, `on_audio` becomes `dg_connection.send(chunk)` and nothing else changes.
"""

import subprocess
import threading


class AudioExtractor:
    def __init__(
        self,
        source,
        on_audio,            # callable(chunk: bytes) -> None   raw PCM bytes
        on_log=None,         # callable(line: str) -> None      ffmpeg progress
        on_end=None,         # callable() -> None
        on_error=None,       # callable(exc) -> None
        sample_rate=16000,
        channels=1,
        realtime=True,       # pace a file like a live feed; False = full speed
        chunk_size=4096,     # bytes read per loop
    ):
        self.source = source
        self.on_audio = on_audio
        self.on_log = on_log
        self.on_end = on_end
        self.on_error = on_error
        self.sample_rate = sample_rate
        self.channels = channels
        self.realtime = realtime
        self.chunk_size = chunk_size
        self._proc = None
        self._stop = threading.Event()
        self._threads = []

    def _build_args(self):
        args = ["ffmpeg"]
        if self.realtime:
            args += ["-re"]              # read input at native frame rate (real time)
        args += [
            "-i", self.source,
            "-vn",                       # strip video, audio only
            "-ac", str(self.channels),   # mono
            "-ar", str(self.sample_rate),# 16 kHz
            "-f", "s16le",               # raw signed 16-bit little-endian PCM
            "-loglevel", "info",
            "pipe:1",                    # PCM to stdout
        ]
        return args

    def _read_stdout(self):
        try:
            while not self._stop.is_set():
                chunk = self._proc.stdout.read(self.chunk_size)
                if not chunk:
                    break
                self.on_audio(chunk)
        except Exception as exc:        # noqa: BLE001
            if self.on_error:
                self.on_error(exc)

    def _read_stderr(self):
        # ffmpeg writes human-readable progress to stderr (not an error channel)
        for raw in iter(self._proc.stderr.readline, b""):
            if self._stop.is_set():
                break
            if self.on_log:
                self.on_log(raw.decode("utf-8", errors="ignore").rstrip())

    def start(self):
        try:
            self._proc = subprocess.Popen(
                self._build_args(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            # most common: ffmpeg not installed / not on PATH
            if self.on_error:
                self.on_error(exc)
            return self

        t_out = threading.Thread(target=self._read_stdout, daemon=True)
        t_err = threading.Thread(target=self._read_stderr, daemon=True)
        t_out.start()
        t_err.start()
        self._threads = [t_out, t_err]

        # watcher thread fires on_end when ffmpeg exits
        def _wait():
            code = self._proc.wait()
            t_out.join(timeout=2)
            if self._stop.is_set():
                print(f"[AudioExtractor] process stopped by user (code={code})")
                return
            if code in (0, None):
                if self.on_end:
                    print(f"[AudioExtractor] process completed successfully (code={code})")
                    self.on_end()
            elif self.on_error:
                error_msg = f"ffmpeg exited with code {code}"
                print(f"[AudioExtractor] {error_msg}")
                self.on_error(RuntimeError(error_msg))

        t_wait = threading.Thread(target=_wait, daemon=True)
        t_wait.start()
        self._threads.append(t_wait)
        return self

    def stop(self):
        self._stop.set()
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:           # noqa: BLE001
                pass
