"""
Copy this file to config.py and fill in your real values.
config.py is git-ignored so your webhook URL never gets committed.
"""

# --- Screen capture ---
# The pixel box on YOUR screen where the PTFS minimap is drawn.
# (left, top, width, height). Use a screenshot tool to find these values.
MINIMAP_REGION = {
    "left": 20,
    "top": 20,
    "width": 300,
    "height": 300,
}

# --- Marker detection ---
# Simplest approach: your player marker is a distinct solid color (many
# Roblox minimaps use a bright color like white/blue/red for "you").
# Give an RGB color and a tolerance. If that's not reliable, switch
# marker_finder.py to template matching instead (see comments there).
MARKER_COLOR_RGB = (255, 255, 255)   # placeholder — sample your actual marker
MARKER_COLOR_TOLERANCE = 30          # per-channel +/- tolerance
MARKER_MIN_PIXEL_AREA = 4            # ignore tiny noise blobs smaller than this

# --- Tracking loop ---
POLL_INTERVAL_SECONDS = 1.0   # how often to capture + process a frame

# --- Discord ---
DISCORD_WEBHOOK_URL = ""
DISCORD_POST_MIN_INTERVAL_SECONDS = 5  # avoid spamming the webhook every tick

# --- Local broadcast server (for the web map) ---
BROADCAST_HOST = "localhost"
BROADCAST_PORT = 8765

# --- Identity (shown in Discord + on the map) ---
CALLSIGN = "YOURCALLSIGN"
