"""Phase 2 product-plane gate.

ArcKit backlog JSON is validated here. This module does not write Persona,
UserJourney, JourneyStage, Scenario, UserStory, Feature, Epic, or Story nodes.
It does not call pkc_capture.py. PKC's capture_prd still creates a Feature from
the stage title, so a journey file is not handed to PKC.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pkc_arckit.engine import parse_document, safe_relative, sha256_bytes

GENERIC_PERSONAS = {
    "user",
    "a user",
    "the user",
    "new user",
    "system",
    "the system",
    "administrator",
    "admin",
}
PERSONA_LABELS = ("Role", "Goals", "Pain Points", "Technical Proficiency")
PLACEHOLDER = re.compile(r"\[[^\]\n]+\]|(?:^|\s)TBD(?:\s|$)")
DRIVER_RE = re.compile(r"^###\s+(?:Goal\s+|Outcome\s+)?((?:SD|G|O)-\d+)\s*:")
PRIORITY = {
    "must": "must",
    "must have": "must",
    "should": "should",
    "should have": "should",
    "could": "could",
    "could have": "could",
    "won't": "wont",
    "won't have": "wont",
    "wont": "wont",
    "wont have": "wont",
}


@dataclass
class ProductPlan:
    status: str
    errors: list[dict[str, str]] = field(default_factory=list)
    held: list[dict[str, Any]] = field(default_factory=list)
    personas: list[dict[str, Any]] = field(default_factory=list)
    ignored: list[dict[str, str]] = field(default_factory=list)
    journey: dict[str, Any] | None = None
    prd_called: bool = False
    stop_reason: str = ""


def _priority(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return PRIORITY.get(value.strip().lower())


def _points(story: dict[str, Any]) -> int:
    value = story.get("story_points", 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{story.get('id')} story_points is not an integer")
    return value


def validate_backlog(data: dict[str, Any]) -> list[str]:
    """Recompute the totals ArcKit's backlog hook checks. Do not trust the file."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["backlog is not an object"]
    stories = data.get("stories")
    epics = data.get("epics")
    if not isinstance(stories, list) or not isinstance(epics, list):
        return ["stories and epics must be arrays"]
    summary = data.get("summary")
    if not isinstance(summary, dict):
        return ["summary is missing"]
    try:
        points = [_points(story) for story in stories]
    except ValueError as exc:
        return [str(exc)]
    if summary.get("total_stories") != len(stories):
        errors.append("total_stories does not match the stories array")
    if summary.get("total_points") != sum(points):
        errors.append("total_points does not match the stories")
    if summary.get("total_epics") != len(epics):
        errors.append("total_epics does not match the epics array")
    buckets = {"must": 0, "should": 0, "could": 0, "wont": 0}
    for story, score in zip(stories, points):
        kind = _priority(story.get("priority"))
        if kind is None:
            errors.append(f"{story.get('id')} has no MoSCoW priority")
            continue
        buckets[kind] += score
        sprint = story.get("sprint", None)
        if sprint is None:
            continue
        if isinstance(sprint, bool) or not isinstance(sprint, int) or sprint < 1:
            errors.append(f"{story.get('id')} sprint must be null or at least 1")
    for key, field_name in (
        ("must", "must_have_points"),
        ("should", "should_have_points"),
        ("could", "could_have_points"),
        ("wont", "wont_have_points"),
    ):
        if field_name in summary and summary[field_name] != buckets[key]:
            errors.append(f"{field_name} does not match the stories")
    epic_ids = []
    for epic in epics:
        epic_id = epic.get("id")
        epic_ids.append(epic_id)
        members = [story.get("id") for story in stories if story.get("epic") == epic_id]
        listed = list(epic.get("stories") or [])
        if sorted(map(str, listed)) != sorted(map(str, members)):
            errors.append(f"{epic_id} stories list does not match the items")
        member_points = sum(
            _points(story) for story in stories if story.get("epic") == epic_id
        )
        if epic.get("points") != member_points:
            errors.append(f"{epic_id} points do not match its stories")
    for story in stories:
        if story.get("epic") not in epic_ids:
            errors.append(f"{story.get('id')} names an unknown epic")
    sprints = data.get("sprints") or []
    if not isinstance(sprints, list):
        errors.append("sprints must be an array")
        sprints = []
    for sprint in sprints:
        number = sprint.get("number")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            errors.append("sprint number must be at least 1")
            continue
        actual = [story.get("id") for story in stories if story.get("sprint") == number]
        listed = list(sprint.get("stories") or [])
        if sorted(map(str, listed)) != sorted(map(str, actual)):
            errors.append(f"sprint {number} stories do not match the items")
    trace = data.get("traceability")
    if "total_requirements" in summary:
        if not isinstance(trace, list) or summary["total_requirements"] != len(trace):
            errors.append("total_requirements does not match the traceability rows")
    return errors


def _label_in_bullet(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("- "):
        return None
    body = stripped[2:].strip()
    match = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", body)
    if not match:
        return None
    name, rest = match.group(1).strip(), match.group(2).strip()
    if name.endswith(":"):
        return name[:-1].strip(), rest
    if rest.startswith(":"):
        return name, rest[1:].strip()
    return None


def personas_from_requirements(text: str) -> list[dict[str, str]]:
    """Copy a persona only when the four template labels are filled in."""
    found: list[dict[str, str]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = re.match(r"^#{2,6}\s+Persona\b[^:]*:\s*(.*)$", lines[index].strip())
        if not match:
            index += 1
            continue
        title = match.group(1).strip()
        index += 1
        labels: dict[str, str] = {}
        while index < len(lines) and not lines[index].startswith("#"):
            pair = _label_in_bullet(lines[index])
            if pair:
                labels[pair[0]] = pair[1].strip()
            index += 1
        if any(name not in labels or not labels[name] for name in PERSONA_LABELS):
            continue
        blob = " ".join([title, *labels.values()])
        if PLACEHOLDER.search(blob) or not title:
            continue
        found.append(
            {
                "title": title,
                "role": labels["Role"],
                "goals": labels["Goals"],
                "pain_points": labels["Pain Points"],
                "context": labels["Technical Proficiency"],
            }
        )
    return found


def ignored_stakeholder_ids(text: str) -> list[dict[str, str]]:
    """Stakeholder drivers, goals, and outcomes are not personas."""
    rows = []
    for line in text.splitlines():
        match = DRIVER_RE.match(line.strip())
        if match:
            kind = {"SD": "driver", "G": "goal", "O": "outcome"}[match.group(1).split("-")[0]]
            rows.append({"id": match.group(1), "kind": kind, "promoted": "no"})
    return rows


def _known_requirements(req_text: str, relative: str, bundle: Path | None) -> set[str]:
    known: set[str] = set()
    if req_text:
        doc = parse_document(relative, req_text, sha256_bytes(req_text.encode("utf-8")))
        if doc.errors:
            raise ValueError(doc.errors[0]["message"])
        known.update(item.item_id for item in doc.items)
    if bundle and bundle.is_dir():
        for path in bundle.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            if "external_system: arckit" not in text or "type: Requirement" not in text:
                continue
            for line in text.splitlines():
                if line.startswith("source_item_id:"):
                    known.add(line.split(":", 1)[1].strip())
    return known


def _story_record(story: dict[str, Any], persona_titles: set[str]) -> dict[str, Any]:
    reasons: list[str] = []
    as_a = str(story.get("as_a") or "").strip()
    if as_a.lower() in GENERIC_PERSONAS or as_a not in persona_titles:
        reasons.append("missing persona")
    so_that = str(story.get("so_that") or "").strip()
    if not so_that or story.get("so_that_inferred") is True or story.get("inferred") is True:
        reasons.append("missing outcome")
    acceptance = story.get("acceptance_criteria")
    if not isinstance(acceptance, list) or not acceptance:
        reasons.append("missing acceptance")
    stage = story.get("stage")
    if not isinstance(stage, str) or not stage.strip():
        reasons.append("missing stage")
    capability = str(story.get("i_want") or "").strip()
    if not capability:
        reasons.append("missing capability")
    return {
        "id": story.get("id"),
        "title": story.get("title"),
        "persona": as_a if "missing persona" not in reasons else None,
        "capability": capability or None,
        "outcome": so_that if "missing outcome" not in reasons else None,
        "acceptance": acceptance if "missing acceptance" not in reasons else None,
        "stage": stage.strip() if isinstance(stage, str) else None,
        "requirement_ids": [str(item) for item in story.get("requirements") or []],
        "reasons": reasons,
    }


def plan_product(
    *,
    backlog: dict[str, Any],
    requirements_text: str = "",
    requirements_relative: str = "projects/001-benefits-portal/ARC-001-REQ-v1.0.md",
    stakeholder_text: str = "",
    bundle: Path | None = None,
) -> ProductPlan:
    plan = ProductPlan(status="refused")
    plan.ignored = ignored_stakeholder_ids(stakeholder_text)
    errors = validate_backlog(backlog)
    if errors:
        plan.errors = [{"failure_type": "BACKLOG_INVALID", "message": item} for item in errors]
        return plan
    try:
        known = _known_requirements(requirements_text, requirements_relative, bundle)
    except ValueError as exc:
        plan.errors = [{"failure_type": "REQ_INVALID", "message": str(exc)}]
        return plan
    plan.personas = personas_from_requirements(requirements_text)
    titles = {row["title"] for row in plan.personas}
    for story in backlog.get("stories") or []:
        for requirement_id in story.get("requirements") or []:
            if str(requirement_id) not in known:
                plan.errors.append(
                    {
                        "failure_type": "UNRESOLVED_REF",
                        "message": f"{story.get('id')} -> {requirement_id}",
                    }
                )
    if plan.errors:
        plan.status = "refused"
        return plan
    records = [_story_record(story, titles) for story in backlog.get("stories") or []]
    plan.held = records
    journey = backlog.get("journey")
    stages_named = all("missing stage" not in row["reasons"] for row in records) and bool(records)
    journey_ok = isinstance(journey, dict) and str(journey.get("title") or "").strip() and str(journey.get("goal") or "").strip()
    if not stages_named or not journey_ok:
        plan.status = "missing stage"
        plan.stop_reason = "missing stage"
        plan.journey = None
        return plan
    if any(row["reasons"] for row in records):
        plan.status = "held"
        plan.stop_reason = "story fields are incomplete"
        return plan
    # Candidate only. feature and requirement are omitted on purpose.
    # capture_prd would mint a Feature from the stage title.
    by_stage: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        by_stage.setdefault(row["stage"], []).append(
            {
                "title": row["title"],
                "persona": row["persona"],
                "capability": row["capability"],
                "outcome": row["outcome"],
                "acceptance": row["acceptance"],
                "requirement_ids": row["requirement_ids"],
                "priority": "must",
            }
        )
    plan.journey = {
        "personas": plan.personas,
        "journeys": [
            {
                "title": journey["title"].strip(),
                "goal": journey["goal"].strip(),
                "persona": journey.get("persona") or plan.personas[0]["title"],
                "stages": [
                    {"title": stage, "outcome": stage, "stories": stories}
                    for stage, stories in by_stage.items()
                ],
            }
        ],
    }
    plan.status = "stopped"
    plan.stop_reason = "unresolved identity: PKC capture_prd creates a Feature from the stage title"
    plan.prd_called = False
    return plan


def load_backlog(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("backlog is not an object")
    return data


def product_from_files(
    root: Path,
    backlog_path: Path,
    *,
    requirements: Path | None = None,
    stakeholders: Path | None = None,
    bundle: Path | None = None,
) -> ProductPlan:
    relative_backlog = safe_relative(root, backlog_path)
    if Path(relative_backlog).name.upper().find("BKLG") < 0 and not backlog_path.name.endswith(".json"):
        raise ValueError("product input must be a backlog json file")
    req_text = ""
    req_rel = "projects/001-benefits-portal/ARC-001-REQ-v1.0.md"
    if requirements is not None:
        req_rel = safe_relative(root, requirements)
        req_text = requirements.read_text(encoding="utf-8")
    stke = ""
    if stakeholders is not None:
        safe_relative(root, stakeholders)
        stke = stakeholders.read_text(encoding="utf-8")
    return plan_product(
        backlog=load_backlog(backlog_path),
        requirements_text=req_text,
        requirements_relative=req_rel,
        stakeholder_text=stke,
        bundle=bundle,
    )
