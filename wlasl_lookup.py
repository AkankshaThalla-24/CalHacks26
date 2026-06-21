"""
Looks up a gloss word directly against the WLASL dataset on disk —
no pre-curation step, no renamed copies. Point it at the dataset
once (WLASL_DIR) and call find(gloss) per word, live.
"""

import json
import os

WLASL_DIR = os.getenv("WLASL_DIR", r"C:\Users\hp\Downloads\wlasl-processed")

_gloss_map = None   # {gloss: [video_id, ...]}
_videos_dir = None


def _load_index():
    json_path = None
    for root, _, files in os.walk(WLASL_DIR):
        for f in files:
            if f.lower().startswith("wlasl") and f.lower().endswith(".json"):
                json_path = os.path.join(root, f)
                break
        if json_path:
            break
    if not json_path:
        raise RuntimeError(f"Could not find WLASL_*.json under {WLASL_DIR}")

    with open(json_path) as fh:
        data = json.load(fh)

    gloss_map = {}
    for entry in data:
        gloss = entry["gloss"].lower().strip()
        gloss_map[gloss] = [inst["video_id"] for inst in entry.get("instances", [])]
    return gloss_map


def _find_videos_dir():
    best, best_count = None, 0
    for root, _, files in os.walk(WLASL_DIR):
        mp4s = sum(1 for f in files if f.endswith(".mp4"))
        if mp4s > best_count:
            best, best_count = root, mp4s
    if not best:
        raise RuntimeError(f"No .mp4 files found under {WLASL_DIR}")
    return best


def _ensure_loaded():
    global _gloss_map, _videos_dir
    if _gloss_map is None:
        _gloss_map = _load_index()
        _videos_dir = _find_videos_dir()


def find(gloss: str) -> str | None:
    """Returns the absolute path to a video for this gloss, or None if no match."""
    _ensure_loaded()
    g = gloss.lower().strip()
    for video_id in _gloss_map.get(g, []):
        candidate = os.path.join(_videos_dir, f"{video_id}.mp4")
        if os.path.exists(candidate):
            return candidate
    return None
