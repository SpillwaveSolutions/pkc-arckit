"""Parse native ArcKit Markdown and plan PKC concepts.

Phase 1 reads REQ, ADR, and RISK files. It does not write a journey graph.
It does not call an LLM. A failed document produces no concepts.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ALGORITHM = "1"
PREFIX_KIND = {
    "BR": "business",
    "FR": "functional",
    "NFR": "nonfunctional",
    "INT": "integration",
    "DR": "data",
}
REQ_PREFIX = r"(?:BR|FR|DR|INT|NFR(?:-[A-Z0-9]+)?)"
ITEM_RE = re.compile(rf"^({REQ_PREFIX}|R|UC)-(\d+)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
LABEL_LINE = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")
PLACEHOLDER_RE = re.compile(r"\[[A-Z0-9_ ]+\]|(?:^|\s)TBD(?:\s|$)")
FILENAME_RE = re.compile(
    r"^ARC-(\d{3})-(REQ|ADR|RISK)-v(\d+\.\d+)\.md$", re.IGNORECASE
)
PROJECT_RE = re.compile(r"^\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")

# Labels the stock heading templates declare on the first exemplar of each kind.
# A bullet that bolds an example is not a label. See tests.
REQUIRED_LABELS = {
    "BR": ["Description", "Rationale", "Acceptance Criteria", "Priority"],
    "FR": ["Description", "Rationale", "Acceptance Criteria", "Priority"],
    "NFR": ["Requirement", "Rationale", "Acceptance Criteria", "Priority"],
    "INT": ["Purpose", "Rationale", "Acceptance Criteria", "Priority"],
    "DR": ["Description", "Rationale", "Acceptance Criteria", "Priority"],
    "R": ["Category", "Status"],
}

DIRECTION = {
    # relation -> (source kinds or types, target kinds or types)
    "satisfies": ({"functional", "nonfunctional", "integration", "data"}, {"business"}),
    "decides": ({"DecisionRecord"}, {"Requirement", "Feature"}),
    "mitigates": ({"DecisionRecord"}, {"Risk"}),
    "depends_on": ({"DecisionRecord"}, {"DecisionRecord"}),
    "supersedes": ({"DecisionRecord"}, {"DecisionRecord"}),
    "exposes": ({"Risk"}, {"Requirement", "Feature"}),
}

PRIORITY_MAP = {
    "must": "must",
    "must have": "must",
    "must_have": "must",
    "should": "should",
    "should have": "should",
    "could": "could",
    "could have": "could",
    "won't": "wont",
    "wont": "wont",
    "won't have": "wont",
    "wont have": "wont",
}


@dataclass
class Item:
    item_id: str
    kind: str
    concept_type: str
    title: str
    statement: str
    priority: str | None
    labels: dict[str, str]
    refs: list[tuple[str, str]]  # (relation, target item id)
    placeholder: bool = False


@dataclass
class ParsedDoc:
    path: str
    project: str
    family: str
    document_id: str
    version: str
    profile: str
    signature: dict[str, Any]
    items: list[Item]
    errors: list[dict[str, str]] = field(default_factory=list)
    source_hash: str = ""


@dataclass
class Planned:
    external_id: str
    rel_path: str
    frontmatter: dict[str, Any]
    body: str
    action: str
    reason: str = ""
    edges: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Plan:
    status: str
    documents: list[dict[str, Any]]
    actions: list[Planned]
    proposals: list[dict[str, Any]]
    errors: list[dict[str, str]]
    source_hashes: dict[str, str]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fold_heading(level: str, text: str) -> str:
    if level == "#":
        return "# {H1}"
    text = ITEM_RE.sub("{ID}", text.strip())
    text = re.sub(r"\[[^\]]+\]", "{PH}", text)
    return f"{level} {text}"


def structural_signature(text: str) -> dict[str, Any]:
    """Signature of structure only. Prose and bold examples do not count."""
    headings: list[str] = []
    labels: list[str] = []
    tables: list[str] = []
    kind: str | None = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        heading = HEADING_RE.match(stripped)
        if heading:
            level, title = heading.group(1), heading.group(2)
            headings.append(_fold_heading(level, title))
            match = re.match(rf"^((?:{REQ_PREFIX}|R|UC))-\d+\b", title)
            kind = match.group(1) if match else None
            if kind and kind.startswith("NFR"):
                kind = "NFR"
            continue
        if stripped.startswith("|") and index + 1 < len(lines):
            nxt = lines[index + 1].strip()
            if re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$", nxt):
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                tables.append("|".join(cells))
        if re.match(r"^[-*]\s+", stripped):
            continue
        label = _label_match(stripped)
        if label and kind:
            labels.append(f"{kind}:{label[0]}")
    return {
        "algorithm": ALGORITHM,
        "headings": headings,
        "labels": labels,
        "tables": tables,
    }


def signature_digest(signature: dict[str, Any]) -> str:
    payload = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _label_match(stripped: str) -> tuple[str, str] | None:
    """A field label is **Name**: or **Name:**. Bold text in a bullet is not a label."""
    match = LABEL_LINE.match(stripped)
    if not match:
        return None
    name, rest = match.group(1).strip(), match.group(2).strip()
    if name.endswith(":"):
        return name[:-1].strip(), rest
    if rest.startswith(":"):
        return name, rest[1:].strip()
    return None
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _priority(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip().lower().replace("-", " ")
    return PRIORITY_MAP.get(key)


def _concept_type(prefix: str) -> str:
    if prefix == "R":
        return "Risk"
    return "Requirement"


def _kind_for(prefix: str) -> str:
    if prefix.startswith("NFR"):
        return "nonfunctional"
    if prefix == "R":
        return "risk"
    return PREFIX_KIND[prefix]


def _statement_from(labels: dict[str, str], fallback: str) -> str:
    for key in ("Description", "Requirement", "Purpose"):
        if labels.get(key):
            return labels[key].strip()
    return fallback.strip()


def _refs_from_labels(labels: dict[str, str], source_prefix: str) -> list[tuple[str, str]]:
    raw = labels.get("Relates To", "")
    refs: list[tuple[str, str]] = []
    for token in re.findall(rf"{REQ_PREFIX}-\d+|UC-\d+", raw):
        if token.startswith("UC-"):
            continue
        target_prefix = token.split("-")[0]
        if source_prefix in {"FR", "NFR", "INT", "DR"} or source_prefix.startswith("NFR"):
            if target_prefix == "BR":
                refs.append(("satisfies", token))
        elif source_prefix == "BR" and target_prefix not in {"BR", "UC"}:
            refs.append(("reversed", token))
    satisfied_by = labels.get("Satisfied By", "")
    if source_prefix == "BR" and re.search(rf"{REQ_PREFIX}-\d+", satisfied_by):
        refs.append(("reversed", "direction"))
    return refs


def _placeholder_in_item(item: Item) -> bool:
    blob = " ".join([item.title, item.statement, *item.labels.values()])
    return PLACEHOLDER_RE.search(blob) is not None


def parse_compact_tables(text: str) -> tuple[list[Item], list[dict[str, str]]]:
    items: list[Item] = []
    errors: list[dict[str, str]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("|") and index + 1 < len(lines):
            separator = lines[index + 1].strip()
            if re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$", separator):
                headers = _split_row(stripped)
                if headers[:1] == ["ID"] and headers != ["ID", "Requirement", "Priority"]:
                    errors.append(
                        {
                            "failure_type": "TEMPLATE_MISMATCH",
                            "message": "requirement table columns are not ID, Requirement, Priority",
                        }
                    )
                    return [], errors
                if headers == ["ID", "Requirement", "Priority"]:
                    index += 2
                    while index < len(lines) and lines[index].strip().startswith("|"):
                        cells = _split_row(lines[index])
                        index += 1
                        if len(cells) < 3 or not cells[0]:
                            continue
                        item_id = cells[0]
                        match = re.match(rf"^({REQ_PREFIX})-(\d+)$", item_id)
                        if not match:
                            errors.append(
                                {
                                    "failure_type": "UNKNOWN_PREFIX",
                                    "message": f"unsupported identifier {item_id}",
                                }
                            )
                            continue
                        prefix = match.group(1)
                        if prefix.startswith("NFR"):
                            prefix = "NFR"
                        statement = cells[1]
                        item = Item(
                            item_id=item_id,
                            kind=_kind_for(match.group(1) if not match.group(1).startswith("NFR") else "NFR"),
                            concept_type="Requirement",
                            title=statement,
                            statement=statement,
                            priority=_priority(cells[2]),
                            labels={"Requirement": statement, "Priority": cells[2]},
                            refs=[],
                        )
                        item.placeholder = _placeholder_in_item(item)
                        items.append(item)
                    continue
        index += 1
    return items, errors


def _heading_blocks(text: str) -> list[tuple[str, str, str]]:
    """Return (level, title, body) for every ATX heading."""
    lines = text.splitlines()
    marks: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line.strip())
        if match:
            marks.append((index, match.group(1), match.group(2).strip()))
    blocks: list[tuple[str, str, str]] = []
    for position, (index, level, title) in enumerate(marks):
        end = len(lines)
        for later_index, later_level, _title in marks[position + 1 :]:
            if len(later_level) <= len(level):
                end = later_index
                break
        blocks.append((level, title, "\n".join(lines[index + 1 : end])))
    return blocks


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _labels_in_block(body: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    current: str | None = None
    chunks: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            labels[current] = "\n".join(chunks).strip()
        current = None

    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[-*]\s+", stripped):
            if current:
                chunks.append(stripped)
            continue
        found = _label_match(stripped)
        if found:
            flush()
            current = found[0]
            chunks = [found[1]] if found[1] else []
            continue
        if current:
            chunks.append(stripped)
    flush()
    return labels


def parse_heading_items(text: str, family: str) -> tuple[list[Item], list[dict[str, str]]]:
    items: list[Item] = []
    errors: list[dict[str, str]] = []
    for _level, title, body in _heading_blocks(text):
        match = re.match(rf"^(?:Risk\s+)?((?:{REQ_PREFIX}|R|UC))-(\d+)\b[:\s-]*(.*)$", title)
        if not match:
            continue
        prefix, _number, rest = match.group(1), match.group(2), match.group(3).strip()
        if prefix == "UC" or prefix.startswith("UC"):
            continue
        if family == "REQ" and prefix == "R":
            errors.append({"failure_type": "UNKNOWN_PREFIX", "message": f"risk id in requirements file {prefix}"})
            continue
        if family == "RISK" and prefix != "R":
            continue
        if family == "REQ" and prefix == "R":
            continue
        labels = _labels_in_block(body)
        base = "NFR" if prefix.startswith("NFR") else prefix
        if family == "REQ":
            required = REQUIRED_LABELS.get(base, [])
            missing = [name for name in required if name not in labels]
            if missing:
                errors.append(
                    {
                        "failure_type": "MISSING_LABEL",
                        "message": f"{prefix}-{_number} missing {', '.join(missing)}",
                    }
                )
        if family == "RISK" and prefix == "R":
            missing = [name for name in REQUIRED_LABELS["R"] if name not in labels]
            if missing:
                errors.append(
                    {
                        "failure_type": "MISSING_LABEL",
                        "message": f"R-{_number} missing {', '.join(missing)}",
                    }
                )
        item_id = f"{prefix}-{_number}" if prefix != "R" else f"R-{_number}"
        # prefix already includes the full token such as NFR-SEC
        if prefix == "R":
            item_id = f"R-{_number}"
        else:
            item_id = f"{prefix}-{_number}"
        statement = _statement_from(labels, rest or title)
        heading_title = rest or statement
        item = Item(
            item_id=item_id,
            kind=_kind_for(base if prefix.startswith("NFR") else prefix) if prefix != "R" else "risk",
            concept_type=_concept_type(prefix if prefix != "R" else "R"),
            title=heading_title,
            statement=statement,
            priority=_priority(labels.get("Priority") or labels.get("Status")),
            labels=labels,
            refs=_refs_from_labels(labels, "NFR" if prefix.startswith("NFR") else prefix),
        )
        item.placeholder = _placeholder_in_item(item)
        items.append(item)
    return items, errors


def _family_from_name(name: str) -> tuple[str, str, str] | None:
    match = FILENAME_RE.match(name)
    if not match:
        return None
    return match.group(2).upper(), match.group(1), match.group(3)


def safe_relative(root: Path, path: Path) -> str:
    """Reject traversal and symlink escapes. Return the path relative to root."""
    root_resolved = root.resolve()
    if path.is_symlink():
        raise ValueError("symlink escape")
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("path escapes the ArcKit root") from exc
    if any(part == ".." for part in relative.parts):
        raise ValueError("path traversal")
    return relative.as_posix()


def project_key(relative: str) -> str:
    parent = Path(relative).parent.name
    if not PROJECT_RE.match(parent):
        raise ValueError(f"project identifier is not stable: {parent}")
    return parent


def parse_document(relative: str, text: str, source_hash: str) -> ParsedDoc:
    name = Path(relative).name
    parsed_name = _family_from_name(name)
    errors: list[dict[str, str]] = []
    if parsed_name is None:
        return ParsedDoc(
            path=relative,
            project="",
            family="",
            document_id=name,
            version="",
            profile="",
            signature=structural_signature(text),
            items=[],
            errors=[{"failure_type": "UNKNOWN_PREFIX", "message": f"unsupported file {name}"}],
            source_hash=source_hash,
        )
    family, _project_number, version = parsed_name
    try:
        project = project_key(relative)
    except ValueError as exc:
        errors.append({"failure_type": "UNKNOWN_PREFIX", "message": str(exc)})
        project = ""
    document_id = f"ARC-{_project_number}-{family}-v{version}"
    signature = structural_signature(text)
    if family == "REQ":
        compact_items, compact_errors = parse_compact_tables(text)
        heading_items, heading_errors = parse_heading_items(text, "REQ")
        if compact_items and heading_items:
            errors.append({"failure_type": "TEMPLATE_MISMATCH", "message": "mixed requirement grammars"})
            items: list[Item] = []
            profile = "mixed"
        elif compact_items or (compact_errors and not heading_items):
            items = compact_items
            errors.extend(compact_errors)
            profile = "req-compact"
        else:
            items = heading_items
            errors.extend(heading_errors)
            profile = "req-heading"
    elif family == "ADR":
        items = [
            Item(
                item_id=f"ADR-{_project_number}",
                kind="decision",
                concept_type="DecisionRecord",
                title=_adr_title(text),
                statement=_section_text(text, "Context and Problem Statement") or _adr_title(text),
                priority=None,
                labels={},
                refs=_adr_refs(text),
            )
        ]
        items[0].placeholder = _placeholder_in_item(items[0])
        profile = "adr"
        errors.extend(_adr_status_errors(text))
    else:
        items, risk_errors = parse_heading_items(text, "RISK")
        errors.extend(risk_errors)
        profile = "risk"
        if not items and not errors:
            errors.append({"failure_type": "MISSING_LABEL", "message": "no risk identifiers"})
    if not items and not errors:
        errors.append({"failure_type": "MISSING_LABEL", "message": "no importable identifiers"})
    if any(item.placeholder for item in items):
        errors.append({"failure_type": "PLACEHOLDER", "message": "placeholder text in an imported item"})
    seen: set[str] = set()
    for item in items:
        if item.item_id in seen:
            errors.append({"failure_type": "DUPLICATE_ID", "message": f"duplicate {item.item_id}"})
        seen.add(item.item_id)
    if any(ref[0] == "reversed" for item in items for ref in item.refs):
        errors.append({"failure_type": "REVERSED_EDGE", "message": "relation direction is not allowed"})
    return ParsedDoc(
        path=relative,
        project=project,
        family=family,
        document_id=document_id,
        version=version,
        profile=profile,
        signature=signature,
        items=items,
        errors=errors,
        source_hash=source_hash,
    )


def _adr_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip().removeprefix("Architecture Decision Record:").strip()
    return ""


def _section_text(text: str, heading: str) -> str:
    for _level, title, body in _heading_blocks(text):
        if heading.lower() in title.lower():
            return body.strip()
    return ""


def _adr_refs(text: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    trace = _section_text(text, "Requirements Traceability")
    for token in re.findall(rf"{REQ_PREFIX}-\d+", trace):
        prefix = token.split("-")[0]
        if prefix == "BR" or token.startswith(("FR-", "NFR", "INT-", "DR-")):
            refs.append(("decides", token))
    for token in re.findall(r"ADR-\d+", _section_text(text, "Decisions This ADR Depends On")):
        refs.append(("depends_on", token))
    for token in re.findall(r"ADR-\d+", _section_text(text, "Conflicting Decisions")):
        refs.append(("supersedes", token))
    for token in re.findall(r"R-\d+", _section_text(text, "Risks and Mitigations")):
        refs.append(("mitigates", token))
    return refs


def _adr_status_errors(text: str) -> list[dict[str, str]]:
    # A missing status is allowed. It must not be invented as accepted.
    return []


def wiki_key(project: str, family: str, item_id: str) -> str:
    slug = f"{project}-{family}-{item_id}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return f"arckit-{slug}"


def rel_path_for(concept_type: str, key: str) -> str:
    folder = {"Requirement": "requirements", "DecisionRecord": "decisions", "Risk": "risks"}[concept_type]
    return f"{folder}/{key}.md"


def external_id(project: str, family: str, item_id: str) -> str:
    return f"{project}/{family}/{item_id}"


def _body(title: str, statement: str) -> str:
    return f"# {title}\n\n## Statement\n\n{statement}\n"


def _frontmatter(doc: ParsedDoc, item: Item) -> dict[str, Any]:
    key = wiki_key(doc.project, doc.family, item.item_id)
    fm: dict[str, Any] = {
        "type": item.concept_type,
        "title": item.title,
        "external_system": "arckit",
        "external_id": external_id(doc.project, doc.family, item.item_id),
        "source_document": doc.document_id,
        "source_path": doc.path,
        "source_item_id": item.item_id,
        "template_signature": signature_digest(doc.signature),
        "mapping_version": "1",
        "source_state": "present",
        "generated": True,
        "verified": False,
        "wiki_key": key,
        "imported_statement": item.statement,
        "stable_timestamp": True,
    }
    if item.concept_type == "Requirement":
        fm["kind"] = item.kind
        if item.priority:
            fm["priority"] = item.priority
        else:
            fm["priority_unavailable"] = True
    if item.concept_type == "DecisionRecord":
        fm["status_unavailable"] = True
    return fm


def _load_existing(bundle: Path | None) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    if bundle is None or not bundle.is_dir():
        return found
    for path in bundle.rglob("*.md"):
        if path.name == "index.md":
            continue
        text = path.read_text(encoding="utf-8")
        fm = _read_frontmatter(text)
        if fm.get("external_system") != "arckit" or not fm.get("external_id"):
            continue
        fm["_path"] = str(path.relative_to(bundle))
        fm["_text"] = text
        found.setdefault(str(fm["external_id"]), []).append(fm)
    return found


def _read_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    raw = text[4:end]
    data: dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith(" ") or line.startswith("-"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.lower() == "true":
            parsed: Any = True
        elif value.lower() == "false":
            parsed = False
        else:
            parsed = value.strip('"')
        data[key.strip()] = parsed
    return data


def _canonical(fm: dict[str, Any], body: str) -> str:
    skip = {"timestamp", "stable_timestamp", "author"}
    lines = [f"{key}: {fm[key]}" for key in sorted(fm) if key not in skip]
    return "\n".join(lines) + "\n" + body.strip() + "\n"


def check_signature(doc: ParsedDoc, pinned: dict[str, str]) -> str | None:
    digest = signature_digest(doc.signature)
    expected = pinned.get(doc.profile)
    if expected and digest != expected:
        return digest
    return None


def build_plan(
    documents: list[ParsedDoc],
    *,
    bundle: Path | None = None,
    pinned_signatures: dict[str, str] | None = None,
    accept_missing: bool = False,
) -> Plan:
    pinned_signatures = pinned_signatures or {}
    errors: list[dict[str, str]] = []
    proposals: list[dict[str, Any]] = []
    actions: list[Planned] = []
    doc_reports: list[dict[str, Any]] = []
    existing = _load_existing(bundle)

    identities: dict[str, list[str]] = {}
    for doc in documents:
        for item in doc.items:
            if not doc.project:
                continue
            eid = external_id(doc.project, doc.family, item.item_id)
            identities.setdefault(eid, []).append(doc.path)
    conflicts = {eid for eid, paths in identities.items() if len(set(paths)) > 1}
    if conflicts:
        for eid in sorted(conflicts):
            errors.append(
                {
                    "failure_type": "CONFLICT",
                    "message": f"{eid} claimed by {', '.join(identities[eid])}",
                }
            )
        return Plan(
            status="conflict",
            documents=[],
            actions=[],
            proposals=[],
            errors=errors,
            source_hashes={doc.path: doc.source_hash for doc in documents},
        )

    occupied = {eid for eid, rows in existing.items() if len(rows) > 1}
    for eid in sorted(occupied):
        errors.append({"failure_type": "CONFLICT", "message": f"existing PKC paths already share {eid}"})

    failed_docs: set[str] = set()
    for doc in documents:
        doc_errors = list(doc.errors)
        if pinned_signatures and doc.profile in pinned_signatures:
            mismatch = check_signature(doc, pinned_signatures)
            if mismatch:
                doc_errors.append(
                    {
                        "failure_type": "TEMPLATE_MISMATCH",
                        "message": f"signature {mismatch} does not match profile {doc.profile}",
                    }
                )
        known_ids = {item.item_id for item in doc.items}
        for item in doc.items:
            for relation, target in item.refs:
                if relation == "reversed":
                    continue
                if target not in known_ids and not _known_in_bundle(existing, doc.project, target):
                    doc_errors.append(
                        {
                            "failure_type": "UNRESOLVED_REF",
                            "message": f"{item.item_id} -> {target}",
                        }
                    )
        if doc_errors:
            failed_docs.add(doc.path)
        doc_reports.append(
            {
                "path": doc.path,
                "profile": doc.profile,
                "document_id": doc.document_id,
                "signature": signature_digest(doc.signature),
                "errors": doc_errors,
                "item_ids": [item.item_id for item in doc.items],
            }
        )
        errors.extend({**err, "path": doc.path} for err in doc_errors)

    successful = [doc for doc in documents if doc.path not in failed_docs]
    planned_ids: set[str] = set()
    stems_ok = {_stem(doc.document_id): doc for doc in successful}
    for doc in successful:
        for item in doc.items:
            eid = external_id(doc.project, doc.family, item.item_id)
            planned_ids.add(eid)
            if eid in occupied:
                continue
            rows = existing.get(eid, [])
            key = wiki_key(doc.project, doc.family, item.item_id)
            path = rel_path_for(item.concept_type, key)
            if rows and rows[0]["_path"] != path:
                path = rows[0]["_path"]
            fm = _frontmatter(doc, item)
            body = _body(item.title, item.statement)
            action, reason = _diff(rows, fm, body)
            edges = []
            for relation, target in item.refs:
                if relation == "reversed":
                    continue
                edges.append({"rel": relation, "target_external_id": _target_eid(doc, target)})
            actions.append(
                Planned(
                    external_id=eid,
                    rel_path=path,
                    frontmatter=fm,
                    body=body,
                    action=action,
                    reason=reason,
                    edges=edges,
                )
            )

    for eid, rows in existing.items():
        if eid in planned_ids or eid in occupied or eid.count("/") != 2:
            continue
        row = rows[0]
        stem = _stem(str(row.get("source_document", "")))
        doc = stems_ok.get(stem)
        if doc is None:
            continue
        _project, _family, item_id = eid.split("/", 2)
        if item_id in {item.item_id for item in doc.items}:
            continue
        proposals.append(
            {
                "external_id": eid,
                "path": row["_path"],
                "source_state": "missing",
                "persisted": False,
                "truth_state_unchanged": True,
            }
        )

    if errors and not actions:
        status = "refused"
    elif errors:
        status = "partial"
    elif any(item.action == "refused" for item in actions):
        status = "refused"
    else:
        status = "ok"
    _ = accept_missing
    return Plan(
        status=status,
        documents=doc_reports,
        actions=actions,
        proposals=proposals,
        errors=errors,
        source_hashes={doc.path: doc.source_hash for doc in documents},
    )


def _stem(document_id: str) -> str:
    return re.sub(r"-v\d+\.\d+$", "", document_id)


def _target_eid(doc: ParsedDoc, target: str) -> str:
    if target.startswith("ADR-"):
        family = "ADR"
    elif target.startswith("R-"):
        family = "RISK"
    else:
        family = "REQ"
    return external_id(doc.project, family, target)


def _known_in_bundle(existing: dict[str, list[dict[str, Any]]], project: str, target: str) -> bool:
    if target.startswith("R-"):
        family = "RISK"
    elif target.startswith("ADR-"):
        family = "ADR"
    else:
        family = "REQ"
    return external_id(project, family, target) in existing


def _diff(rows: list[dict[str, Any]], fm: dict[str, Any], body: str) -> tuple[str, str]:
    if not rows:
        return "created", ""
    row = rows[0]
    previous = str(row.get("imported_statement", ""))
    body_text = _body_of(str(row.get("_text", "")))
    source_same = fm.get("imported_statement") == previous
    recorded = _statement_in_body(body_text)
    if previous and recorded != previous:
        return "refused", "local edit" if source_same else "divergence"
    owned = (
        "title",
        "type",
        "external_system",
        "external_id",
        "source_document",
        "source_path",
        "source_item_id",
        "mapping_version",
        "generated",
        "verified",
        "wiki_key",
        "imported_statement",
        "kind",
        "priority",
    )
    for key in owned:
        new_value = fm.get(key)
        if new_value is None:
            continue
        if str(row.get(key)) != str(new_value):
            return "updated", ""
    _ = body
    return "skipped", ""


def _body_of(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            return text[end + 5 :]
    return text


def _statement_in_body(body: str) -> str:
    marker = "## Statement"
    if marker not in body:
        return body.strip()
    return body.split(marker, 1)[1].strip()
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            return text[end + 5 :]
    return text


def load_sources(root: Path, paths: list[Path]) -> list[ParsedDoc]:
    documents: list[ParsedDoc] = []
    for path in paths:
        relative = safe_relative(root, path)
        data = path.read_bytes()
        text = data.decode("utf-8")
        documents.append(parse_document(relative, text, sha256_bytes(data)))
    return documents


def recheck(root: Path, plan: Plan) -> str | None:
    """Return the path whose bytes changed after planning. None if stable."""
    for relative, digest in plan.source_hashes.items():
        path = root / relative
        if sha256_bytes(path.read_bytes()) != digest:
            return relative
    return None


def plan_paths(
    root: Path,
    paths: list[Path],
    *,
    bundle: Path | None = None,
    pinned_signatures: dict[str, str] | None = None,
    accept_missing: bool = False,
) -> Plan:
    documents = load_sources(root, paths)
    plan = build_plan(
        documents,
        bundle=bundle,
        pinned_signatures=pinned_signatures,
        accept_missing=accept_missing,
    )
    changed = recheck(root, plan)
    if changed:
        plan.status = "stale"
        plan.actions = []
        plan.proposals = []
        plan.errors.append({"failure_type": "STALE", "message": changed, "path": changed})
    return plan


def discover(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in sorted(root.rglob("ARC-*-*.md")):
        if not path.is_file() or path.is_symlink():
            continue
        if FILENAME_RE.match(path.name):
            try:
                safe_relative(root, path)
            except ValueError:
                continue
            found.append(path)
    return found


def dump_plan(plan: Plan) -> dict[str, Any]:
    return {
        "status": plan.status,
        "documents": plan.documents,
        "actions": [
            {
                "external_id": item.external_id,
                "path": item.rel_path,
                "action": item.action,
                "reason": item.reason,
                "edges": item.edges,
                "title": item.frontmatter.get("title"),
                "verified": item.frontmatter.get("verified"),
                "generated": item.frontmatter.get("generated"),
            }
            for item in plan.actions
        ],
        "proposals": plan.proposals,
        "errors": plan.errors,
    }
