"""Phase 1 acceptance tests. Upstream bytes are pinned. Derived files are labeled."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pkc_arckit.apply import apply_plan, event_gaps
from pkc_arckit.engine import (
    parse_document,
    plan_paths,
    recheck,
    structural_signature,
)
from pkc_arckit.hook import coalesce, handle_event

UPSTREAM = Path(__file__).parent / "fixtures" / "upstream"
HASHES = {
    "requirements-template.md": "2ab72a432d85984b48a519e21515011df7793935f0349168415b2f48f3b7862e",
    "adr-template.md": "ad422c96d509324fab882a2b76e638600e7da242ed23564ea636a5626e74bb1b",
    "risk-register-template.md": "2f080a80af3cc8ad6a35d4e3bde2ebcb857604b261cef99bbad1d31fb8aef716",
    "ARC-001-REQ-v1.0.md": "8e908f6bac08a5a2943c041e4312f58f056366169f2dd4f9b19dc0e28d8c734b",
}
IDS = ["BR-001", "BR-002", "FR-001", "FR-002", "DR-001", "DR-002"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_upstream_bytes_match_pinned_hashes():
    for name, digest in HASHES.items():
        assert _sha(UPSTREAM / name) == digest


def _stage(tmp: Path, name: str = "ARC-001-REQ-v1.0.md", text: str | None = None) -> tuple[Path, Path]:
    project = tmp / "projects" / "001-benefits-portal"
    project.mkdir(parents=True)
    dest = project / name
    if text is None:
        dest.write_bytes((UPSTREAM / "ARC-001-REQ-v1.0.md").read_bytes())
    else:
        dest.write_text(text, encoding="utf-8")
    return tmp, dest


def _actions(tmp: Path, bundle: Path | None = None, name: str = "ARC-001-REQ-v1.0.md"):
    root, path = _stage(tmp, name)
    plan = plan_paths(root, [path], bundle=bundle)
    return plan


def test_compact_fixture_creates_six_requirements(tmp_path: Path):
    plan = _actions(tmp_path)
    assert plan.status == "ok"
    assert plan.errors == []
    by_id = {item.frontmatter["source_item_id"]: item for item in plan.actions}
    assert set(by_id) == set(IDS)
    assert all(item.action == "created" for item in plan.actions)
    assert all(item.frontmatter["verified"] is False for item in plan.actions)
    assert all(item.frontmatter["generated"] is True for item in plan.actions)
    br = by_id["BR-001"]
    assert br.frontmatter["external_id"] == "001-benefits-portal/REQ/BR-001"
    assert br.rel_path == "requirements/arckit-001-benefits-portal-req-br-001.md"
    assert "Citizens MUST be able to submit a housing-benefit claim online" in br.body
    assert br.frontmatter["priority"] == "must"
    assert by_id["FR-002"].frontmatter["priority"] == "should"


def test_second_import_is_skipped_and_writes_no_event(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    first = plan_paths(root, [path], bundle=bundle)
    apply_plan(first, bundle)
    assert len(list((bundle / "write-events").glob("*.md"))) == 6
    second = plan_paths(root, [path], bundle=bundle)
    assert {item.action for item in second.actions} == {"skipped"}
    apply_plan(second, bundle)
    assert len(list((bundle / "write-events").glob("*.md"))) == 6


def test_one_priority_change_updates_only_that_concept(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    apply_plan(plan_paths(root, [path], bundle=bundle), bundle)
    text = path.read_text(encoding="utf-8").replace(
        "| BR-001 | Citizens MUST be able to submit a housing-benefit claim online without visiting an office. | Must |",
        "| BR-001 | Citizens MUST be able to submit a housing-benefit claim online without visiting an office. | Should |",
    )
    path.write_text(text, encoding="utf-8")
    plan = plan_paths(root, [path], bundle=bundle)
    by_id = {item.frontmatter["source_item_id"]: item.action for item in plan.actions}
    assert by_id["BR-001"] == "updated"
    assert all(action == "skipped" for item_id, action in by_id.items() if item_id != "BR-001")
    before = len(list((bundle / "write-events").glob("*.md")))
    apply_plan(plan, bundle)
    assert len(list((bundle / "write-events").glob("*.md"))) == before + 1


def test_title_change_keeps_the_same_path(tmp_path: Path):
    text = """# Requirements: Derived

#### BR-001: Pay the claimant

**Description**: The council MUST pay the claimant.
**Rationale**: Statute.
**Acceptance Criteria**:
- The claimant is paid.
**Priority**: Must
**Stakeholder**: Council
"""
    root, path = _stage(tmp_path, text=text)
    bundle = tmp_path / "knowledge"
    first = plan_paths(root, [path], bundle=bundle)
    assert first.actions[0].rel_path.endswith("req-br-001.md")
    apply_plan(first, bundle)
    path.write_text(text.replace("Pay the claimant", "Pay the citizen"), encoding="utf-8")
    second = plan_paths(root, [path], bundle=bundle)
    assert second.actions[0].action == "updated"
    assert second.actions[0].rel_path == first.actions[0].rel_path
    assert second.actions[0].frontmatter["external_id"] == "001-benefits-portal/REQ/BR-001"
    assert second.actions[0].frontmatter["title"] == "Pay the citizen"


def test_version_rename_updates_provenance_not_identity(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    apply_plan(plan_paths(root, [path], bundle=bundle), bundle)
    renamed = path.with_name("ARC-001-REQ-v1.1.md")
    path.rename(renamed)
    plan = plan_paths(root, [renamed], bundle=bundle)
    assert {item.action for item in plan.actions} == {"updated"}
    assert {item.frontmatter["external_id"] for item in plan.actions} == {
        f"001-benefits-portal/REQ/{item_id}" for item_id in IDS
    }
    assert {item.frontmatter["source_document"] for item in plan.actions} == {"ARC-001-REQ-v1.1"}


def test_bold_example_inside_a_bullet_is_not_a_field_label():
    text = """#### FR-001: Sign in

**Description**: The portal MUST sign the citizen in.
**Rationale**: Access.
**Acceptance Criteria**:
- The session starts.
**Priority**: Must

- **Multi-Factor Authentication (MFA)** improves account security.
"""
    signature = structural_signature(text)
    assert "FR:Multi-Factor Authentication (MFA)" not in signature["labels"]
    assert "FR:Description" in signature["labels"]
    doc = parse_document("projects/001-benefits-portal/ARC-001-REQ-v1.0.md", text, "abc")
    assert "Multi-Factor Authentication (MFA)" not in doc.items[0].labels


def test_satisfies_edge_uses_business_requirement_target(tmp_path: Path):
    text = """# Requirements: Derived

#### BR-001: Pay

**Description**: The council MUST pay.
**Rationale**: Statute.
**Acceptance Criteria**:
- Paid.
**Priority**: Must

#### FR-001: Record the payment

**Description**: The portal MUST record the payment.
**Relates To**: BR-001
**Rationale**: Audit.
**Acceptance Criteria**:
- Recorded.
**Priority**: Must
"""
    root, path = _stage(tmp_path, text=text)
    plan = plan_paths(root, [path])
    fr = next(item for item in plan.actions if item.frontmatter["source_item_id"] == "FR-001")
    assert fr.edges == [{"rel": "satisfies", "target_external_id": "001-benefits-portal/REQ/BR-001"}]


def test_duplicate_identity_across_files_writes_nothing(tmp_path: Path):
    root, first = _stage(tmp_path)
    other = first.parent / "ARC-002-REQ-v1.0.md"
    other.write_bytes(first.read_bytes())
    plan = plan_paths(root, [first, other])
    assert plan.status == "conflict"
    assert plan.actions == []
    assert any(err["failure_type"] == "CONFLICT" for err in plan.errors)


def test_unknown_prefix_writes_nothing(tmp_path: Path):
    root, path = _stage(tmp_path)
    text = path.read_text(encoding="utf-8").replace("BR-001", "XX-001")
    path.write_text(text, encoding="utf-8")
    plan = plan_paths(root, [path])
    assert plan.actions == []
    assert any(err["failure_type"] == "UNKNOWN_PREFIX" for err in plan.errors)


def test_missing_label_writes_nothing(tmp_path: Path):
    text = """# Requirements: Derived

#### FR-001: Save

**Description**: The portal MUST save.
**Priority**: Must
"""
    root, path = _stage(tmp_path, text=text)
    plan = plan_paths(root, [path])
    assert plan.actions == []
    assert any(err["failure_type"] == "MISSING_LABEL" for err in plan.errors)


def test_unknown_column_is_a_template_mismatch(tmp_path: Path):
    root, path = _stage(tmp_path)
    text = path.read_text(encoding="utf-8").replace(
        "| ID | Requirement | Priority |",
        "| ID | Requirement | Priority | Notes |",
    )
    text = text.replace("|----|-------------|----------|", "|----|-------------|----------|-------|")
    path.write_text(text, encoding="utf-8")
    plan = plan_paths(root, [path])
    assert plan.actions == []
    assert any(err["failure_type"] == "TEMPLATE_MISMATCH" for err in plan.errors)


def test_unresolved_target_writes_nothing(tmp_path: Path):
    text = """# Requirements: Derived

#### FR-001: Save

**Description**: The portal MUST save.
**Relates To**: BR-999
**Rationale**: Resume.
**Acceptance Criteria**:
- Saved.
**Priority**: Must
"""
    root, path = _stage(tmp_path, text=text)
    plan = plan_paths(root, [path])
    assert plan.actions == []
    assert any(err["failure_type"] == "UNRESOLVED_REF" for err in plan.errors)


def test_reversed_edge_writes_nothing(tmp_path: Path):
    text = """# Requirements: Derived

#### BR-001: Pay

**Description**: The council MUST pay.
**Rationale**: Statute.
**Acceptance Criteria**:
- Paid.
**Priority**: Must
**Satisfied By**: FR-001

#### FR-001: Record

**Description**: The portal MUST record the payment.
**Rationale**: Audit.
**Acceptance Criteria**:
- Recorded.
**Priority**: Must
"""
    root, path = _stage(tmp_path, text=text)
    plan = plan_paths(root, [path])
    assert plan.actions == []
    assert any(err["failure_type"] == "REVERSED_EDGE" for err in plan.errors)


def test_placeholder_template_is_not_an_import(tmp_path: Path):
    project = tmp_path / "projects" / "001-benefits-portal"
    project.mkdir(parents=True)
    for src, name in (
        ("requirements-template.md", "ARC-001-REQ-v1.0.md"),
        ("adr-template.md", "ARC-001-ADR-v1.0.md"),
        ("risk-register-template.md", "ARC-001-RISK-v1.0.md"),
    ):
        dest = project / name
        dest.write_bytes((UPSTREAM / src).read_bytes())
        plan = plan_paths(tmp_path, [dest])
        assert plan.actions == [], name
        assert any(err["failure_type"] == "PLACEHOLDER" for err in plan.errors)


def test_malformed_file_does_not_mark_missing(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    apply_plan(plan_paths(root, [path], bundle=bundle), bundle)
    path.write_text("# broken\n\nnot a requirement table\n", encoding="utf-8")
    plan = plan_paths(root, [path], bundle=bundle)
    assert plan.proposals == []
    assert plan.actions == []


def test_omitted_identifier_is_a_proposal_not_a_delete(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    apply_plan(plan_paths(root, [path], bundle=bundle), bundle)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "| FR-002 | The portal MUST let a caseworker request further evidence against a claim. | Should |\n",
        "",
    )
    path.write_text(text, encoding="utf-8")
    kept = bundle / "requirements" / "arckit-001-benefits-portal-req-fr-002.md"
    before = kept.read_text(encoding="utf-8")
    plan = plan_paths(root, [path], bundle=bundle)
    assert any(item["external_id"].endswith("/FR-002") and item["persisted"] is False for item in plan.proposals)
    assert kept.read_text(encoding="utf-8") == before
    assert "truth_state" not in before


def test_two_existing_paths_for_one_identity_are_refused(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    apply_plan(plan_paths(root, [path], bundle=bundle), bundle)
    twin = bundle / "requirements" / "twin-br-001.md"
    original = (bundle / "requirements" / "arckit-001-benefits-portal-req-br-001.md").read_text(encoding="utf-8")
    twin.write_text(original, encoding="utf-8")
    plan = plan_paths(root, [path], bundle=bundle)
    assert any("BR-001" in err["message"] for err in plan.errors)
    br = [item for item in plan.actions if item.external_id.endswith("/BR-001")]
    assert br == []


def test_local_edit_is_not_overwritten(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    apply_plan(plan_paths(root, [path], bundle=bundle), bundle)
    concept = bundle / "requirements" / "arckit-001-benefits-portal-req-br-001.md"
    concept.write_text(
        concept.read_text(encoding="utf-8").replace(
            "## Statement\n\nCitizens MUST",
            "## Statement\n\nPeople MUST",
            1,
        ),
        encoding="utf-8",
    )
    plan = plan_paths(root, [path], bundle=bundle)
    match = next(item for item in plan.actions if item.external_id.endswith("/BR-001"))
    assert match.action == "refused"
    apply_plan(plan, bundle)
    assert "People MUST" in concept.read_text(encoding="utf-8")


def test_path_escape_is_rejected(tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    rogue = outside / "ARC-001-REQ-v1.0.md"
    rogue.write_text("nope", encoding="utf-8")
    link = tmp_path / "projects"
    link.mkdir()
    alias = link / "ARC-001-REQ-v1.0.md"
    alias.symlink_to(rogue)
    with pytest.raises(ValueError):
        plan_paths(tmp_path, [alias])


def test_source_change_during_preflight_drops_the_plan(tmp_path: Path):
    root, path = _stage(tmp_path)
    plan = plan_paths(root, [path])
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert recheck(root, plan) == "projects/001-benefits-portal/ARC-001-REQ-v1.0.md"


def test_crash_after_some_writes_does_not_create_twins(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    plan = plan_paths(root, [path], bundle=bundle)
    with pytest.raises(RuntimeError):
        apply_plan(plan, bundle, crash_after=2)
    assert len(list((bundle / "requirements").glob("arckit-*.md"))) == 2
    again = plan_paths(root, [path], bundle=bundle)
    assert {item.action for item in again.actions} == {"skipped", "created"}
    apply_plan(again, bundle)
    assert len(list((bundle / "requirements").glob("arckit-*.md"))) == 6


def test_crash_before_event_is_reported_and_not_repaired_with_a_twin(tmp_path: Path):
    root, path = _stage(tmp_path)
    bundle = tmp_path / "knowledge"
    plan = plan_paths(root, [path], bundle=bundle)
    target = plan.actions[0].rel_path
    with pytest.raises(RuntimeError):
        apply_plan(plan, bundle, crash_before_event=target)
    assert event_gaps(bundle) == [target]
    # Finish the rest without inventing a second file for the first concept.
    rest = plan_paths(root, [path], bundle=bundle)
    assert next(item.action for item in rest.actions if item.rel_path == target) == "skipped"
    apply_plan(rest, bundle)
    assert len(list((bundle / "requirements").glob(Path(target).name))) == 1
    assert target in event_gaps(bundle)


def test_hook_ignores_non_arckit_paths_and_coalesces():
    assert handle_event({"path": "knowledge/requirements/arckit-x.md"}) is None
    assert handle_event({"path": "README.md"}) is None
    queued = handle_event({"path": "projects/001-benefits-portal/ARC-001-REQ-v1.0.md"})
    assert queued.endswith("ARC-001-REQ-v1.0.md")
    assert coalesce([queued, queued, queued]) == [queued]


def test_use_case_heading_is_not_a_requirement(tmp_path: Path):
    text = """# Requirements: Derived

#### UC-1: Submit a claim

**Actor**: Citizen

#### BR-001: Submit

**Description**: Citizens MUST submit a claim.
**Rationale**: Access.
**Acceptance Criteria**:
- Submitted.
**Priority**: Must
"""
    root, path = _stage(tmp_path, text=text)
    plan = plan_paths(root, [path])
    assert [item.frontmatter["source_item_id"] for item in plan.actions] == ["BR-001"]
