# Agents

This repository is the ArcKit adapter. It is not part of Project Knowledge Capture (PKC).

## Rules

- Phase 2 may validate backlog JSON and report a candidate journey. It must not call `pkc_capture.py prd` while that command creates a Feature from the stage title.
- Do not treat a stakeholder driver, goal, or outcome as a persona.
- Parse native `ARC-*.md`. Do not parse ArcKit's OKF export.
- Do not write `Persona`, `UserJourney`, `JourneyStage`, `Scenario`, `UserStory`, `Feature`, Epic, or a WikiTicket `Story`.
- Do not infer a persona, a goal, or a journey stage.
- Do not delete a concept. A missing identifier is a proposal.
- Do not set `verified: true`.
- Do not modify `pkc_adr_import.py`, `pkc-curate.sh`, the PKC relation registry, or the Agent Graph Engineering Runtime.
- Production writes go through PKC `write_knowledge`. If PKC is not installed, do not write.
- Keep `external_id` as `{project}/{family}/{item-id}`. The ArcKit document version is provenance, not identity.
- A field label is `**Name**:` or `**Name:**`. Bold text inside a bullet is content.
- Tests must keep the four upstream fixture hashes. Do not replace them with invented filled ADR or risk files.
- Derived fixtures belong under `tests/fixtures/derived/` and must say they are derived.

## Checks

Run `python3 -m pytest` before a release. A failing placeholder, conflict, or unresolved-reference test means the change is not ready.

The contract is `docs/spec.md`. If code and the spec disagree, fix the code or change the spec in the same commit and say which section moved.
