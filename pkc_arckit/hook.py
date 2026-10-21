"""Host events enqueue native ArcKit paths. They do not write knowledge."""

from __future__ import annotations

import re
from pathlib import Path

FAMILY = re.compile(r"(^|/)ARC-[^/]*-(REQ|ADR|RISK)-[^/]*\.md$")


def accept_path(path: str) -> bool:
    normal = path.replace("\\", "/")
    if ".." in Path(normal).parts:
        return False
    if not normal.startswith("projects/") and "/projects/" not in f"/{normal}":
        # Allow a path that contains projects/ as a prefix segment.
        parts = normal.split("/")
        if "projects" not in parts:
            return False
    if any(segment in {"okf", "knowledge", "write-events"} for segment in normal.split("/")):
        return False
    return FAMILY.search(normal) is not None


def handle_event(event: dict) -> str | None:
    """Return the path to enqueue, or None when the event is ignored."""
    path = ""
    tool_input = event.get("tool_input") or {}
    if isinstance(tool_input, dict):
        path = str(tool_input.get("file_path") or tool_input.get("path") or "")
    path = path or str(event.get("path") or event.get("file_path") or "")
    if not path or not accept_path(path):
        return None
    return path


def coalesce(paths: list[str]) -> list[str]:
    seen: list[str] = []
    for path in paths:
        if path not in seen:
            seen.append(path)
    return seen
