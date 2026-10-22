"""Phase 2 stops before PKC prd. Derived backlog JSON is not an upstream fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pkc_arckit.phase2 import plan_product

STKE = Path(__file__).parent / "fixtures" / "upstream" / "ARC-001-STKE-v1.0.md"
STKE_SHA = "d53673a3d792a2888ffe88ec06210f5b9d906f692b88419cdc1dc1025f300db2"

REQ = """# Requirements: Derived

#### Persona 1: Citizen claimant

- **Role**: Claimant
- **Goals**: Submit a claim
- **Pain Points**: Paper forms
- **Technical Proficiency**: Low

#### BR-001: Submit

**Description**: Citizens MUST submit a claim online.
**Rationale**: Access.
**Acceptance Criteria**:
- Submitted.
**Priority**: Must

#### FR-001: Save the claim

**Description**: The portal MUST save a partial claim.
**Relates To**: BR-001
**Rationale**: Resume.
**Acceptance Criteria**:
- Saved.
**Priority**: Must
"""


def _backlog(**overrides):
    story = {
        "id": "STORY-001",
        "epic": "EPIC-001",
        "title": "Save a claim",
        "as_a": "Citizen claimant",
        "i_want": "to save a partial claim",
        "so_that": "I can resume it later",
        "acceptance_criteria": ["The draft is stored"],
        "priority": "Must Have",
        "story_points": 3,
        "sprint": 1,
        "requirements": ["FR-001"],
    }
    story.update(overrides.pop("story", {}))
    data = {
        "summary": {
            "total_stories": 1,
            "total_epics": 1,
            "total_points": 3,
            "must_have_points": 3,
            "should_have_points": 0,
            "could_have_points": 0,
            "wont_have_points": 0,
            "total_requirements": 1,
        },
        "epics": [
            {
                "id": "EPIC-001",
                "title": "Claims",
                "business_requirement": "BR-001",
                "points": 3,
                "stories": ["STORY-001"],
            }
        ],
        "stories": [story],
        "sprints": [{"number": 1, "stories": ["STORY-001"]}],
        "traceability": [{"requirement": "FR-001", "stories": ["STORY-001"]}],
    }
    data.update(overrides)
    return data


def test_stakeholder_fixture_hash_and_not_personas():
    assert hashlib.sha256(STKE.read_bytes()).hexdigest() == STKE_SHA
    plan = plan_product(backlog=_backlog(), requirements_text=REQ, stakeholder_text=STKE.read_text(encoding="utf-8"))
    assert plan.personas == [
        {
            "title": "Citizen claimant",
            "role": "Claimant",
            "goals": "Submit a claim",
            "pain_points": "Paper forms",
            "context": "Low",
        }
    ]
    assert all(row["promoted"] == "no" for row in plan.ignored)
    assert any(row["id"] == "SD-1" and row["kind"] == "driver" for row in plan.ignored)
    assert any(row["id"] == "G-1" for row in plan.ignored)
    assert any(row["id"] == "O-1" for row in plan.ignored)
    assert not any(row["title"] == "Daniel Quist" for row in plan.personas)


def test_official_shape_has_no_stage_and_does_not_call_prd():
    plan = plan_product(backlog=_backlog(), requirements_text=REQ)
    assert plan.status == "missing stage"
    assert plan.stop_reason == "missing stage"
    assert plan.journey is None
    assert plan.prd_called is False
    assert plan.held[0]["capability"] == "to save a partial claim"
    assert "story_points" not in plan.held[0]


def test_generic_persona_is_not_accepted():
    plan = plan_product(backlog=_backlog(story={"as_a": "user"}), requirements_text=REQ)
    assert "missing persona" in plan.held[0]["reasons"]
    assert plan.prd_called is False


def test_inferred_outcome_is_not_copied():
    plan = plan_product(backlog=_backlog(story={"so_that_inferred": True}), requirements_text=REQ)
    assert plan.held[0]["outcome"] is None
    assert "missing outcome" in plan.held[0]["reasons"]


def test_bad_totals_write_nothing():
    data = _backlog()
    data["summary"]["total_points"] = 99
    plan = plan_product(backlog=data, requirements_text=REQ)
    assert plan.status == "refused"
    assert plan.held == []
    assert plan.journey is None
    assert any(err["failure_type"] == "BACKLOG_INVALID" for err in plan.errors)


def test_sprint_zero_is_refused():
    plan = plan_product(backlog=_backlog(story={"sprint": 0}), requirements_text=REQ)
    assert plan.status == "refused"
    assert any("sprint" in err["message"] for err in plan.errors)


def test_unknown_requirement_is_unresolved():
    plan = plan_product(backlog=_backlog(story={"requirements": ["FR-999"]}), requirements_text=REQ)
    assert plan.status == "refused"
    assert any(err["failure_type"] == "UNRESOLVED_REF" for err in plan.errors)


def test_explicit_stage_still_does_not_call_prd_or_emit_feature():
    data = _backlog(story={"stage": "Submit the claim"})
    data["journey"] = {
        "title": "Claim housing benefit",
        "goal": "A citizen submits a complete claim",
        "persona": "Citizen claimant",
    }
    plan = plan_product(backlog=data, requirements_text=REQ)
    assert plan.status == "stopped"
    assert plan.prd_called is False
    assert "Feature" in plan.stop_reason
    encoded = json.dumps(plan.journey)
    assert '"feature"' not in encoded
    assert '"requirement"' not in encoded
    assert "requirement_ids" in encoded
    assert plan.journey["journeys"][0]["stages"][0]["title"] == "Submit the claim"


def test_placeholder_persona_is_ignored():
    text = REQ.replace("Citizen claimant", "[Persona Name]", 1)
    plan = plan_product(backlog=_backlog(), requirements_text=text)
    assert plan.personas == []
    assert "missing persona" in plan.held[0]["reasons"]
