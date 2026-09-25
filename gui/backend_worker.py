"""
Runs the actual capture -> locate -> webhook loop on a background thread,
so the GUI stays responsive. Reuses the existing backend code in src/
rather than duplicating it.

Position is now found via map_locator.MapLocator (template matching against
a saved reference map image) instead of the old manual coordinate
calibration - no typed-in coordinates needed.
"""

import os
import sys
import time

from PyQt6.QtCore import QThread, pyqtSignal

SRC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"
)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import config          # noqa: E402
import webhook         # noqa: E402
import broadcast_server  # noqa: E402
from marker_finder import find_marker_pixel  # noqa: E402
from map_locator import MapLocator  # noqa: E402

REFERENCE_MAP_PATH = os.path.join(SRC_DIR, "reference_map.png")

# Matches below this confidence are treated as "no reliable fix" and skipped
# rather than sent out - avoids spamming garbage positions on a bad frame.
MIN_CONFIDENCE = getattr(config, "MIN_MATCH_CONFIDENCE", 0.35)


class TrackerWorker(QThread):
    log = pyqtSignal(str)
    position = pyqtSignal(float, float)
    error = pyqtSignal(str)

    def __init__(self, callsign: str, aircraft_type: str):
        super().__init__()
        self._running = False
        self.callsign = callsign
        self.aircraft_type = aircraft_type

    def run(self):
        import mss
        import cv2
        import numpy as np

        if not os.path.exists(REFERENCE_MAP_PATH):
            self.error.emit(
                "No reference map found. Click 'Set Reference Map' first."
            )
            return

        try:
            locator = MapLocator(REFERENCE_MAP_PATH)
        except Exception as e:
            self.error.emit(f"Failed to load reference map: {e}")
            return

        self._running = True
        self.log.emit(
            f"Tracker started for {self.callsign} ({self.aircraft_type})."
        )

        with mss.mss() as sct:
            while self._running:
                shot = sct.grab(config.MINIMAP_REGION)
                frame = cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)
                marker_px = find_marker_pixel(frame)

                if marker_px is None:
                    self.log.emit("Marker not found this frame.")
                else:
                    result = locator.locate_marker(frame, marker_px)
                    if result is None:
                        self.log.emit("Could not match minimap to reference map.")
                    else:
                        abs_x, abs_y, confidence = result
                        if confidence < MIN_CONFIDENCE:
                            self.log.emit(
                                f"Low-confidence match ({confidence:.2f}), skipping."
                            )
                        else:
                            self.position.emit(abs_x, abs_y)
                            webhook.post_position(
                                abs_x, abs_y,
                                callsign=self.callsign,
                                aircraft_type=self.aircraft_type,
                            )
                            broadcast_server.broadcast({
                                "callsign": self.callsign,
                                "aircraft_type": self.aircraft_type,
                                "x": abs_x,
                                "y": abs_y,
                                "confidence": confidence,
                                "timestamp": time.time(),
                            })

                time.sleep(config.POLL_INTERVAL_SECONDS)

        self.log.emit("Tracker stopped.")

    def stop(self):
        self._running = False
