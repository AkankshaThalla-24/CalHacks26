"""
Resolves a YouTube (or other yt-dlp-supported) URL into something ffmpeg can
consume — with TWO modes:

  resolve_stream_url(url)                -> streams the remote URL (fast start,
                                            but TRUNCATES the first ~1-4 words
                                            because ffmpeg connects mid-stream)

  resolve_stream_url(url, download=True) -> downloads audio to a local file
                                            first, then returns that path. NO
                                            truncation — every word from t=0.
                                            Best for demos and uploaded videos.
"""

import subprocess
import json
import shutil
import os
import tempfile


def is_web_url(source: str) -> bool:
    s = source.lower()
    if s.startswith(("http://", "https://")):
        if s.split("?")[0].endswith((".m3u8", ".mp3", ".mp4", ".aac", ".wav", ".ts")):
            return False
        return True
    return False


def _get_info(source: str) -> dict:
    meta = subprocess.run(
        ["yt-dlp", "-q", "--no-warnings", "--dump-json",
         "-f", "bestaudio/best", source],
        capture_output=True, text=True,
    )
    if meta.returncode != 0:
        raise RuntimeError(f"yt-dlp could not read the URL:\n{meta.stderr.strip()}")
    return json.loads(meta.stdout.splitlines()[0])


def resolve_stream_url(source: str, download: bool = False, dest_dir: str = None):
    """
    Returns (path_or_url, info).
      download=False : remote stream URL (fast, truncates start)
      download=True  : downloads audio locally first (no truncation)
    Non-web sources are returned unchanged.
    """
    if not is_web_url(source):
        return source, {"is_live": False, "title": source, "mode": "local"}

    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlp is not installed. Install with: pip install yt-dlp")

    info = _get_info(source)
    is_live = bool(info.get("is_live"))

    if is_live and download:
        print("⚠ source is LIVE — download mode ignored; streaming from now.")
        download = False

    if download:
        dest_dir = dest_dir or tempfile.gettempdir()
        out_tmpl = os.path.join(dest_dir, "accessstream_%(id)s.%(ext)s")
        dl = subprocess.run(
            ["yt-dlp", "-q", "--no-warnings",
             "-f", "bestaudio/best",
             "-o", out_tmpl,
             "--print", "after_move:filepath",
             source],
            capture_output=True, text=True,
        )
        if dl.returncode != 0 or not dl.stdout.strip():
            raise RuntimeError(f"yt-dlp download failed:\n{dl.stderr.strip()}")
        local_path = dl.stdout.strip().splitlines()[-1]
        return local_path, {
            "is_live": False,
            "title": info.get("title", "unknown"),
            "ext": info.get("ext"),
            "mode": "downloaded",
            "path": local_path,
        }

    got = subprocess.run(
        ["yt-dlp", "-q", "--no-warnings",
         "-f", "bestaudio/best", "--get-url", source],
        capture_output=True, text=True,
    )
    if got.returncode != 0 or not got.stdout.strip():
        raise RuntimeError(f"yt-dlp could not get a stream URL:\n{got.stderr.strip()}")

    return got.stdout.strip().splitlines()[0], {
        "is_live": is_live,
        "title": info.get("title", "unknown"),
        "ext": info.get("ext"),
        "mode": "streamed",
    }