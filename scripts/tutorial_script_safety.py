"""Avoid waits on Leaflet pane wrappers that have no visible box."""

from __future__ import annotations

import re


LEAFLET_PANE_WAIT = re.compile(
    r"(?P<locator>\.locator\(\s*(?P<quote>['\"])[^'\"]*?"
    r"\.leaflet-overlay-pane(?P=quote)\s*\))"
    r"(?P<wait>\.waitFor\([^)]*\))"
)


def prepare_recording_script(script: str) -> str:
    """Wait for a visible Leaflet polygon instead of its zero-sized pane."""
    return LEAFLET_PANE_WAIT.sub(
        lambda match: (
            match.group("locator").replace(
                ".leaflet-overlay-pane", ".leaflet-interactive"
            )
            + ".first()"
            + match.group("wait")
        ),
        script,
    )
