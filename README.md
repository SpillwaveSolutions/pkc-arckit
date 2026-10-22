# pkc-arckit

Deterministic importer from native ArcKit Markdown into [Project Knowledge Capture](https://github.com/SpillwaveSolutions/project-knowledge-capture) (PKC).

Version 0.2.0 keeps the Phase 1 importer and adds a Phase 2 product gate. Phase 1 reads requirements, architecture decision records, and risk registers. It does not import ArcKit's OKF export.

PKC owns the concepts and the write. This repository does not modify PKC.

Phase 2 validates an ArcKit backlog JSON file. Stakeholder drivers, goals, and outcomes are read and then ignored. They are not personas. The command does not call `pkc_capture.py prd`.

PKC's journey capture creates a Feature from the stage title. ArcKit's backlog stories do not name a journey stage. Until a story names a stage and PKC can attach that stage to an existing node, this command stops:

```bash
python3 -m pkc_arckit.cli product /path/to/arckit-root --backlog projects/001-example/ARC-001-BKLG-v1.0.json
```

A stopped plan can include a candidate journey object. That object has no `feature` field and no `requirement` field. It is not written.

## What Phase 1 does

- Parses the compact requirements table (`ID`, `Requirement`, `Priority`) and the heading grammar (`**Name**:` or `**Name:**`).
- Plans one `Requirement` per `BR`, `FR`, `NFR`, `INT`, and `DR` row or heading.
- Recognizes one `DecisionRecord` per ADR file and one `Risk` per `R-NNN` section.
- Refuses placeholders, unknown prefixes, missing required labels, reversed edges, unresolved targets, mixed grammars, and identity conflicts.
- Keeps identity at `{project}/{family}/{item-id}`. A version rename does not create a second concept.
- Leaves a disappeared identifier as a proposal. It does not delete the concept and it does not change `truth_state`.
- Ignores use-case headings. Bold text inside a bullet is not a field.

The plan command writes nothing.

```bash
python3 -m pkc_arckit.cli plan /path/to/arckit-root
```

A write requires an installed PKC checkout. The command refuses to write without it.

```bash
python3 -m pkc_arckit.cli plan /path/to/arckit-root \
  --bundle /path/to/knowledge \
  --pkc-root /path/to/project-knowledge-capture \
  --author you \
  --write
```

`verified` stays false. A clean parse is not human verification.

## Tests

```bash
python3 -m pytest
```

The four files under `tests/fixtures/upstream/` are byte copies from `tractorjuice/arc-kit` commit `d8f1cd75a3d8ad4db5d27d9ff27838394a73ae1d` (20 October 2026). Tests re-hash them. The requirements table fixture is the only filled positive input. The ADR and risk templates are refusal fixtures. They are not evidence of a filled ADR or risk import.

## Out of this release

Phase 2 (personas, journeys, backlog JSON, `pkc_capture.py prd`) is specified in [docs/spec.md](docs/spec.md) and is not implemented. Host hooks enqueue nothing in this release. The `pkc_arckit.hook` helpers only filter and coalesce paths. They do not open a brain session and they do not push.

## Layout

| Path | Role |
| --- | --- |
| `pkc_arckit/engine.py` | Parse, signature, identity, plan |
| `pkc_arckit/apply.py` | Apply a plan. Production calls PKC `write_knowledge` |
| `pkc_arckit/cli.py` | `plan` and optional `--write` |
| `docs/spec.md` | Implementation contract |
| `skills/pkc-arckit-import/SKILL.md` | Agent skill for the plan command |
