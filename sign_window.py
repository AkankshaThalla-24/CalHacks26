"""
Small native window that plays ASL sign clips back-to-back as words are
enqueued — no server, no browser. Looks each word up live via
wlasl_lookup.find(); words with no match get a brief text placeholder
instead of a clip.
"""

import queue
import threading
import time

import cv2

import wlasl_lookup

WINDOW_NAME = "ASL Sign Player"
PLACEHOLDER_MS = 600
PLACEHOLDER_SIZE = (480, 360)


class SignWindow:
    def __init__(self):
        self._queue = queue.Queue()
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def enqueue(self, text: str):
        """Split on whitespace and queue each word for playback, in order."""
        for word in str(text).split():
            self._queue.put(word)

    def wait_until_idle(self, timeout=None):
        """Blocks until every enqueued word has finished playing."""
        start = time.monotonic()
        while not self._queue.empty():
            if timeout is not None and time.monotonic() - start > timeout:
                return False
            time.sleep(0.1)
        return True

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_NAME, *PLACEHOLDER_SIZE)
        try:
            while not self._stop.is_set():
                try:
                    word = self._queue.get(timeout=0.1)
                except queue.Empty:
                    cv2.waitKey(1)
                    continue

                path = wlasl_lookup.find(word)
                if path:
                    self._play_clip(path, word)
                else:
                    self._show_placeholder(word)
        finally:
            cv2.destroyWindow(WINDOW_NAME)

    def _play_clip(self, path, label):
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        delay_ms = max(1, int(1000 / fps))
        while not self._stop.is_set():
            ok, frame = cap.read()
            if not ok:
                break
            cv2.putText(frame, label.upper(), (12, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (79, 195, 161), 2, cv2.LINE_AA)
            cv2.imshow(WINDOW_NAME, frame)
            cv2.waitKey(delay_ms)
        cap.release()

    def _show_placeholder(self, word):
        import numpy as np
        frame = np.zeros((PLACEHOLDER_SIZE[1], PLACEHOLDER_SIZE[0], 3), dtype="uint8")
        cv2.putText(frame, word.upper(), (16, PLACEHOLDER_SIZE[1] // 2), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (224, 164, 88), 2, cv2.LINE_AA)
        cv2.putText(frame, "(no clip - fingerspell)", (16, PLACEHOLDER_SIZE[1] // 2 + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (139, 152, 168), 1, cv2.LINE_AA)
        cv2.imshow(WINDOW_NAME, frame)
        cv2.waitKey(PLACEHOLDER_MS)


if __name__ == "__main__":
    import sys

    win = SignWindow().start()
    if sys.argv[1:2] == ["--file"]:
        with open(sys.argv[2]) as fh:
            text = " ".join(line.strip() for line in fh if line.strip())
    else:
        text = " ".join(sys.argv[1:]) or "FOOTBALL TEAM PLAY GOAL WIN"
    win.enqueue(text)
    win.wait_until_idle()
    win.stop()
