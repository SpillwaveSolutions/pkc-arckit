# Fixture provenance

Copied from `tractorjuice/arc-kit` commit `d8f1cd75a3d8ad4db5d27d9ff27838394a73ae1d` on 20 October 2026.

| File in this repo | Upstream path | SHA-256 |
| --- | --- | --- |
| `tests/fixtures/upstream/requirements-template.md` | `plugins/arckit-claude/templates/requirements-template.md` | `2ab72a432d85984b48a519e21515011df7793935f0349168415b2f48f3b7862e` |
| `tests/fixtures/upstream/ARC-001-REQ-v1.0.md` | `plugins/arckit-claude/evals/fixtures/benefits-portal/projects/001-benefits-portal/ARC-001-REQ-v1.0.md` | `8e908f6bac08a5a2943c041e4312f58f056366169f2dd4f9b19dc0e28d8c734b` |
| `tests/fixtures/upstream/adr-template.md` | `plugins/arckit-claude/templates/adr-template.md` | `ad422c96d509324fab882a2b76e638600e7da242ed23564ea636a5626e74bb1b` |
| `tests/fixtures/upstream/risk-register-template.md` | `plugins/arckit-claude/templates/risk-register-template.md` | `2f080a80af3cc8ad6a35d4e3bde2ebcb857604b261cef99bbad1d31fb8aef716` |

| `tests/fixtures/upstream/ARC-001-STKE-v1.0.md` | `plugins/arckit-claude/evals/fixtures/benefits-portal-stakeholders/projects/001-benefits-portal/ARC-001-STKE-v1.0.md` | `d53673a3d792a2888ffe88ec06210f5b9d906f692b88419cdc1dc1025f300db2` |

No `ARC-*-BKLG-*.json` file is in that commit. Phase 2 tests that need a backlog use derived JSON in the test module. That JSON is not an upstream artefact.
