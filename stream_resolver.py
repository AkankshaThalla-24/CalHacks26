"""
Resolves a YouTube (or other yt-dlp-supported) URL into a direct audio stream
URL that ffmpeg can consume.

Why this is needed: a youtube.com/watch?v=... link is a web page, not a media
file. yt-dlp does the work of finding the real, signed audio stream URL behind it.

Works for BOTH:
  - regular uploaded videos (ffmpeg -re paces them at 1x = simulated real-time)
  - actual live streams (yt-dlp returns the live HLS manifest = true real-time)
"""

import subprocess
import json
import shutil


def is_web_url(source: str) -> bool:
    """Heuristic: does this look like a page URL yt-dlp should resolve,
    rather than a direct media file/stream ffmpeg can already open?"""
    s = source.lower()
    if s.startswith(("http://", "https://")):
        # direct media containers / manifests — let ffmpeg handle these directly
        if s.split("?")[0].endswith((".m3u8", ".mp3", ".mp4", ".aac", ".wav", ".ts")):
            return False
        return True
    return False


def resolve_stream_url(source: str):
    """
    Returns (stream_url, info) where stream_url is a direct URL ffmpeg can read.
    For non-web sources, returns the source unchanged.
    """
    if not is_web_url(source):
        return source, {"is_live": False, "title": source}

    if shutil.which("yt-dlp") is None:
        raise RuntimeError(
            "yt-dlp is not installed. Install with: pip install yt-dlp"
        )

    # First, grab metadata (title + whether it's currently live).
    meta_cmd = [
        "yt-dlp", "-q", "--no-warnings",
        "--dump-json",
        "-f", "bestaudio/best",
        source,
    ]
    meta = subprocess.run(meta_cmd, capture_output=True, text=True)
    if meta.returncode != 0:
        raise RuntimeError(f"yt-dlp could not read the URL:\n{meta.stderr.strip()}")

    info = json.loads(meta.stdout.splitlines()[0])

    # Then get the direct stream URL for the best audio-only track.
    url_cmd = [
        "yt-dlp", "-q", "--no-warnings",
        "-f", "bestaudio/best",
        "--get-url",
        source,
    ]
    got = subprocess.run(url_cmd, capture_output=True, text=True)
    if got.returncode != 0 or not got.stdout.strip():
        raise RuntimeError(f"yt-dlp could not get a stream URL:\n{got.stderr.strip()}")

    stream_url = got.stdout.strip().splitlines()[0]

    return stream_url, {
        "is_live": bool(info.get("is_live")),
        "title": info.get("title", "unknown"),
        "ext": info.get("ext"),
    }
