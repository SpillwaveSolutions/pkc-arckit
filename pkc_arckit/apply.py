"""Apply a plan. PKC is the production writer. Tests use the file writer."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from pkc_arckit.engine import Plan, Planned


class PkCUnavailable(RuntimeError):
    """Installed Project Knowledge Capture cannot be imported."""


def render_concept(fm: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key, value in fm.items():
        if key == "stable_timestamp":
            continue
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append(body.rstrip())
    lines.append("")
    return "\n".join(lines)


def apply_plan(
    plan: Plan,
    bundle: Path,
    *,
    pkc_root: Path | None = None,
    author: str = "pkc-arckit",
    journal: list[str] | None = None,
    crash_before_event: str | None = None,
    crash_after: int | None = None,
) -> list[str]:
    """Write created and updated concepts. Return the action of each planned row.

    A stale plan, a conflict, and a refused row write nothing for that row.
    skipped writes nothing and records no event.
    """
    if plan.status in {"stale", "conflict"}:
        return []
    bundle.mkdir(parents=True, exist_ok=True)
    results: list[str] = []
    events = journal if journal is not None else []
    written = 0
    for item in plan.actions:
        if item.action in {"skipped", "refused"}:
            results.append(item.action)
            continue
        if item.action not in {"created", "updated"}:
            results.append("refused")
            continue
        if pkc_root is not None:
            _write_via_pkc(pkc_root, bundle, item, author)
        else:
            _write_file(bundle, item)
        if crash_before_event == item.rel_path:
            raise RuntimeError(f"crash before event for {item.rel_path}")
        _append_event(bundle, item)
        events.append(item.rel_path)
        results.append(item.action)
        written += 1
        if crash_after is not None and written >= crash_after:
            raise RuntimeError(f"crash after {written} writes")
    return results


def _write_file(bundle: Path, item: Planned) -> None:
    path = bundle / item.rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_concept(item.frontmatter, item.body), encoding="utf-8")


def _append_event(bundle: Path, item: Planned) -> None:
    folder = bundle / "write-events"
    folder.mkdir(parents=True, exist_ok=True)
    existing = sorted(folder.glob("*.md"))
    name = f"{len(existing) + 1:04d}.md"
    text = (
        "---\n"
        "type: WriteEvent\n"
        f"dest: {item.rel_path}\n"
        f"action: {item.action}\n"
        "---\n\n"
        f"Wrote {item.external_id}.\n"
    )
    (folder / name).write_text(text, encoding="utf-8")


def event_gaps(bundle: Path) -> list[str]:
    """Concepts with no write event. Does not create a concept or an event."""
    if not bundle.is_dir():
        return []
    covered: set[str] = set()
    event_dir = bundle / "write-events"
    if event_dir.is_dir():
        for path in event_dir.glob("*.md"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("dest:"):
                    covered.add(line.split(":", 1)[1].strip())
    gaps: list[str] = []
    for path in sorted(bundle.rglob("*.md")):
        if "write-events" in path.parts or path.name == "index.md":
            continue
        text = path.read_text(encoding="utf-8")
        if "external_system: arckit" not in text:
            continue
        rel = path.relative_to(bundle).as_posix()
        if rel not in covered:
            gaps.append(rel)
    return gaps


def _write_via_pkc(pkc_root: Path, bundle: Path, item: Planned, author: str) -> None:
    scripts = pkc_root / "scripts"
    if not (scripts / "pkc_common.py").is_file():
        raise PkCUnavailable(f"no pkc_common.py under {pkc_root}")
    sys.path.insert(0, str(scripts))
    try:
        import pkc_common  # type: ignore
    except ImportError as exc:
        raise PkCUnavailable(str(exc)) from exc
    frontmatter = {key: value for key, value in item.frontmatter.items()}
    pkc_common.write_knowledge(
        bundle,
        item.rel_path,
        frontmatter,
        item.body,
        author=author,
        host=os.environ.get("SECOND_BRAIN_HOST", "pkc-arckit"),
        emit_event=False,
    )
