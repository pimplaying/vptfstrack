"""
Replaces the old manual-coordinate calibration entirely.

Idea: the small corner minimap is just a zoomed-in, fixed-orientation crop
of the same static game map. If we have ONE full screenshot of that map
(captured once via the game's expandable map view), we can, every tick,
search for where the live minimap crop best matches inside that full image
using OpenCV template matching. Wherever it matches best IS your position
on the map — no typed-in coordinates, no drift, self-correcting every tick.

Because the live minimap's zoom level might not exactly match the
resolution the reference map was captured at, we try a range of scale
factors on the crop and keep whichever gives the strongest match.
"""

import numpy as np
import cv2


class MapLocator:
    def __init__(self, reference_map_path: str,
                 scale_min: float = 0.4, scale_max: float = 2.5, scale_steps: int = 14):
        reference_bgr = cv2.imread(reference_map_path, cv2.IMREAD_COLOR)
        if reference_bgr is None:
            raise FileNotFoundError(f"Could not load reference map: {reference_map_path}")
        self.reference_gray = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY)
        self.reference_size = (reference_bgr.shape[1], reference_bgr.shape[0])  # (w, h)
        self._scales = np.linspace(scale_min, scale_max, scale_steps)

    def locate_crop(self, crop_bgr):
        """
        Returns (top_left_x, top_left_y, scale, confidence) for the best
        match of crop_bgr within the reference map, or None if the crop is
        too large at every tested scale (shouldn't normally happen).
        """
        crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        ref_w, ref_h = self.reference_size

        best = None
        for scale in self._scales:
            resized = cv2.resize(crop_gray, None, fx=scale, fy=scale,
                                  interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
            rh, rw = resized.shape[:2]
            if rw >= ref_w or rh >= ref_h or rw < 8 or rh < 8:
                continue

            result = cv2.matchTemplate(self.reference_gray, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if best is None or max_val > best[3]:
                best = (max_loc[0], max_loc[1], scale, max_val)

        return best  # (top_left_x, top_left_y, scale, confidence) or None

    def locate_marker(self, crop_bgr, marker_pixel_xy):
        """
        Combines locate_crop() with a marker's pixel position WITHIN the
        crop (from marker_finder.find_marker_pixel) to compute the marker's
        absolute position on the reference map image.

        Returns (abs_x, abs_y, confidence) or None.
        """
        match = self.locate_crop(crop_bgr)
        if match is None:
            return None

        top_left_x, top_left_y, scale, confidence = match
        marker_px, marker_py = marker_pixel_xy

        abs_x = top_left_x + marker_px * scale
        abs_y = top_left_y + marker_py * scale
        return (abs_x, abs_y, confidence)
