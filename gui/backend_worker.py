"""
Runs the actual capture -> detect -> transform -> webhook loop on a
background thread, so the GUI stays responsive. Reuses the existing
backend code in src/ rather than duplicating it.
"""

import os
import sys
import time

from PyQt6.QtCore import QThread, pyqtSignal

# Make src/ importable — it lives one level up from gui/, alongside it.
SRC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"
)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import config          # noqa: E402  (src/config.py — must exist, see README)
import webhook         # noqa: E402
import broadcast_server  # noqa: E402
from geometry import CoordinateTransform   # noqa: E402
from marker_finder import find_marker_pixel  # noqa: E402

CALIBRATION_PATH = os.path.join(SRC_DIR, "calibration.json")


class TrackerWorker(QThread):
    log = pyqtSignal(str)
    position = pyqtSignal(float, float)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = False

    def run(self):
        import mss
        import cv2
        import numpy as np

        try:
            transform = CoordinateTransform.load(CALIBRATION_PATH)
        except FileNotFoundError:
            self.error.emit(
                "No calibration.json found. Run calibrate.py from src/ first."
            )
            return

        self._running = True
        self.log.emit("Tracker started.")

        with mss.mss() as sct:
            while self._running:
                shot = sct.grab(config.MINIMAP_REGION)
                frame = cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)
                marker_px = find_marker_pixel(frame)

                if marker_px is None:
                    self.log.emit("Marker not found this frame.")
                else:
                    px, py = marker_px
                    gx, gy = transform.pixel_to_game(px, py)
                    self.position.emit(gx, gy)

                    webhook.post_position(gx, gy)
                    broadcast_server.broadcast({
                        "callsign": config.CALLSIGN,
                        "x": gx,
                        "y": gy,
                        "timestamp": time.time(),
                    })

                time.sleep(config.POLL_INTERVAL_SECONDS)

        self.log.emit("Tracker stopped.")

    def stop(self):
        self._running = False