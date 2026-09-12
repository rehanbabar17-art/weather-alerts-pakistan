"""
Locations loader for weather monitoring.

Locations are resolved in this order:
1. LOCATIONS_JSON env var (JSON list) - used in CI / automation
2. locations/config.local.py - your private, git-ignored list
3. Bundled example locations (public fallback)

Never commit your real coordinates to the repository.
"""
import json
import os

_EXAMPLE_LOCATIONS = [
    {
        "name": "Central Park",
        "city": "New York",
        "country": "USA",
        "lat": 40.7851,
        "lon": -73.9683
    },
    {
        "name": "Trafalgar Square",
        "city": "London",
        "country": "UK",
        "lat": 51.5080,
        "lon": -0.1281
    }
]


def _load_locations():
    raw = os.getenv("LOCATIONS_JSON")
    if raw:
        return json.loads(raw)

    local_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.local.py")
    if os.path.exists(local_file):
        namespace = {}
        with open(local_file, "r", encoding="utf-8") as f:
            exec(f.read(), namespace)
        return namespace["LOCATIONS"]

    return _EXAMPLE_LOCATIONS


LOCATIONS = _load_locations()
