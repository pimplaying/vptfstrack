"""
Posts position updates to a Discord webhook as a formatted embed.
"""

import time
import requests

import config

_last_post_time = 0.0


def post_position(game_x, game_y, callsign=None, aircraft_type=None):
    """
    Posts to Discord, throttled to DISCORD_POST_MIN_INTERVAL_SECONDS so
    you don't spam the webhook on every tracking tick.

    callsign / aircraft_type: passed in from the GUI (the user enters these
    before connecting). Falls back to config.CALLSIGN if not provided, and
    leaves aircraft type blank if none was given.
    """
    global _last_post_time
    now = time.time()
    if now - _last_post_time < config.DISCORD_POST_MIN_INTERVAL_SECONDS:
        return

    callsign = callsign or getattr(config, "CALLSIGN", "UNKNOWN")
    aircraft_type = aircraft_type or "-"

    payload = {
        "embeds": [
            {
                "title": f"{callsign} - position update",
                "fields": [
                    {"name": "Aircraft", "value": aircraft_type, "inline": True},
                    {"name": "X", "value": f"{game_x:.1f}", "inline": True},
                    {"name": "Y", "value": f"{game_y:.1f}", "inline": True},
                ],
                "color": 0x3498DB,
            }
        ]
    }

    try:
        resp = requests.post(config.DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if resp.status_code >= 300:
            print(f"[webhook] Discord returned {resp.status_code}: {resp.text}")
    except requests.RequestException as e:
        print(f"[webhook] Failed to post to Discord: {e}")

    _last_post_time = now
