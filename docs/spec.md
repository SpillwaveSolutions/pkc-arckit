# pkc-arckit: Deterministic ArcKit-to-PKC Integration

**Status:** Implementation specification 1.0  
**Date:** 2026-10-21  
**Proposed project:** `pkc-arckit`  
**Repository:** `SpillwaveSolutions/pkc-arckit` does not exist yet.

This file is the single contract. It replaces `arckit-okf-adapter-spec.md`.

The adapter owns ingestion. Project Knowledge Capture (PKC) owns domain concepts and writes. The Open Knowledge Format (OKF) plugin owns shared graph operations.

The name `pkc-arckit` does not place this code inside PKC. PKC must not depend on this project.

## 1. Purpose

Create a standalone, deterministic importer for native ArcKit Markdown. Convert governed ArcKit requirements, architecture decision records (ADRs), and risk registers into existing PKC concepts. Preserve source identity and provenance. Resolve only explicitly declared relationships. Trigger synchronization through coding-host hooks without writing from those hooks. Use PKC's public write path and isolated brain-session workflow. Do not require a large language model (LLM) for supported inputs.

The importer does not implement ArcKit document governance. It does not translate the entire ArcKit catalogue. It does not alter PKC, the OKF plugin, the Agent Graph Engineering Runtime (AGER), or generated agent host trees.

## 2. Invariants

1. `pkc-arckit` is an independent project. It depends on a compatible installed PKC. PKC has no dependency on `pkc-arckit`.
2. PKC owns `Requirement`, `DecisionRecord`, `Risk`, and every other PKC concept. Only PKC validates domain schemas and persists knowledge.
3. Use PKC `brain_session.py` to open an isolated second-brain worktree. Use PKC `write_knowledge()` to write concepts and emit write events. Do not copy, fork, or vendor those functions.
4. Do not vendor PKC domain schemas. Load validation through an installed, version-compatible PKC interface. Fail closed if that validator is missing.
5. Do not modify `pkc_adr_import.py`, `pkc-curate.sh`, PKC's global relation registry, the OKF plugin relation registry, or AGER. `pkc_adr_import.py` remains the MADR and adr-tools importer. It keys identity on a title slug and sets `verified: true`. Those behaviors stay out of this importer.
6. Parse native `ARC-*.md` files. Do not ingest ArcKit `/arckit:export-okf` output as structure. That export describes documents, not domain concepts.
7. Only `REQ`, `ADR`, and `RISK` families are in scope. Any other family needs its own reviewed mapping version.
8. Never manufacture a target noun, relation, field, identifier, acceptance result, or approval from prose.
9. Imported concepts always have `generated: true` and `verified: false`. A clean parse, a judge pass, and a resolved link are not human verification.
10. A document is the preflight failure boundary. Parse and validate its full write plan before writing that document. PKC has no multi-file atomic commit.
11. A disappeared source identifier never deletes a PKC concept and never changes `truth_state`.
12. Host hooks enqueue paths only. The dispatcher runs the isolated session and opens one pull request (PR). It never merges that PR.
13. The adapter does not write `Persona`, `UserJourney`, `JourneyStage`, `Scenario`, `UserStory`, `Feature`, `Epic`, or a WikiTicket `Story`. When a later mapping authorizes a journey import, it calls PKC `pkc_capture.py prd`. It does not invent a second writer for those nodes.

## 3. Dependencies and deployment

The dispatcher host needs Python 3, an installed PKC, PKC's supported OKF dependency, a checkout of native ArcKit documents, and an authorized second-brain checkout.

The adapter imports PKC modules or calls documented PKC commands from the installed PKC location. It must not assume a sibling checkout. Configuration supplies the PKC location and the second-brain target. Confirm the installed PKC API before implementation. Private helper signatures are not a public contract.

Do not create a private remote. Use the remote already configured for the second brain. Fail if actor identity, knowledge destination, PKC compatibility, Git authorization, or isolation prerequisites are missing.

### Compatibility baseline

The initial baseline is the PKC v0.10.0 interface, released 21 October 2026 as `v0.10.0` (`project-knowledge-capture` pull request 88).

Confirm these commands against the installed tree before the first write:

```bash
python3 scripts/pkc_capture.py prd --file journey.json
python3 scripts/pkc_capture.py prd --file journey.json --no-backlog
```

`--no-backlog` writes the product plane only. It does not write an Epic or a work `Story`.

Record the second-brain marketplace catalog `0.4.17` and worklog `0.24.12` as the release pins supplied with that PKC release (marketplace pull request 30). They are compatibility inputs. Do not copy those catalogs or schemas into this repo.

The adapter fails closed when the installed PKC is older than this baseline or when `pkc_capture.py prd` is absent. Do not fall back to writing journey nodes by hand.

### Layout

Names below are proposed files. They are not contents of an existing repository.

```text
pkc-arckit/
  README.md
  pyproject.toml
  plugin.json
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  .cursor-plugin/plugin.json
  .grok-plugin/marketplace.json
  hooks/hooks.json
  hooks/codex-hooks.json
  hooks/cursor-hooks.json
  scripts/arckit_hook.py
  scripts/arckit_dispatch.py
  scripts/pkc_arckit_import.py
  scripts/arckit_signature.py
  scripts/arckit_doctor.py
  mappings/arckit-pkc-v1.json
  schemas/recovery-request.schema.json
  schemas/recovery-result.schema.json
  schemas/judge-result.schema.json
  agents/pkc-arckit-recovery.md
  agents/pkc-arckit-judge.md
  hosts/cursor/SKILL.md
  hosts/deep-agents/SKILL.md
  hosts/grok-bot/SKILL.md
  skills/pkc-arckit-import/SKILL.md
  skills/pkc-arckit-sync/SKILL.md
  skills/pkc-arckit-doctor/SKILL.md
  skills/pkc-arckit-recover/SKILL.md
  tests/test_parser.py
  tests/test_mapping.py
  tests/test_identity.py
  tests/test_dispatch.py
  tests/test_recovery.py
  tests/test_host_hooks.py
  tests/test_pkc_contract.py
  tests/fixtures/arckit/
  docs/compatibility.md
  docs/operations.md
  docs/fixture-provenance.md
```

Root `plugin.json` uses `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`.

Declare a dependency on installed `project-knowledge-capture` and `okf-graph-eng`. Do not copy their scripts into this repo.

`pkc_arckit_import.py` is the deterministic core. Do not split it into extra layers until a test shows the need. The recovery schemas and role files are required because recovery is part of this contract.

## 4. Source contract and fixtures

Supported files live under `projects/**/` and match one family:

* `ARC-*-REQ-*.md`
* `ARC-*-ADR-*.md`
* `ARC-*-RISK-*.md`

Match the path relative to the configured ArcKit project root. Reject path traversal, symlink escapes, and files outside that root.

Resolve project identity from the stable ArcKit project identifier, such as `001-benefits-portal`. Do not infer it from a document title.

Vendor these four files from `tractorjuice/arc-kit`. SHA-256 is of the file bytes as retrieved on 21 October 2026. Re-hash at test time. Record the upstream commit when vendoring. Drift fails the test.

| Upstream path | Role | SHA-256 |
| --- | --- | --- |
| `plugins/arckit-claude/templates/requirements-template.md` | Heading grammar. Contains placeholders. Not an import. | `2ab72a432d85984b48a519e21515011df7793935f0349168415b2f48f3b7862e` |
| `plugins/arckit-claude/evals/fixtures/benefits-portal/projects/001-benefits-portal/ARC-001-REQ-v1.0.md` | Filled compact-table requirements fixture. The only positive conversion input. | `8e908f6bac08a5a2943c041e4312f58f056366169f2dd4f9b19dc0e28d8c734b` |
| `plugins/arckit-claude/templates/adr-template.md` | ADR structure. Contains placeholders. | `ad422c96d509324fab882a2b76e638600e7da242ed23564ea636a5626e74bb1b` |
| `plugins/arckit-claude/templates/risk-register-template.md` | Risk structure. Contains placeholders. | `2f080a80af3cc8ad6a35d4e3bde2ebcb857604b261cef99bbad1d31fb8aef716` |

Do not present an invented file as an upstream filled ADR or risk artefact. Negative tests may mutate copies. Label those copies as derived tests.

The requirements fixture is a positive conversion. ADR and risk template tests cover recognition, placeholders, and failure. Do not claim positive ADR or risk conversion until a real populated source exists.

## 5. Grammars

The parser accepts the profiles in this section. It rejects every other shape. It does not guess. It does not call an LLM.

### 5.1 Requirements heading grammar

Read a recognized heading such as `#### FR-001`, `#### BR-001`, `#### NFR-SEC-001`, `#### INT-001`, `#### DR-001`, or `#### UC-1`. The mapping declares permitted prefixes and their identifier expressions.

A field declaration is a line that begins with `**Name**:` or `**Name:**`. Bold text inside a bullet is content. This line does not declare a field:

```text
- **Multi-Factor Authentication (MFA)** improves account security.
```

Support a multiline value only when the boundary is unambiguous. Preserve statement bytes. Do not replace a missing section with an excerpt of the body.

Label sets differ by kind. Do not force one set onto every nonfunctional requirement. Exemplar labels from the stock templates:

| Kind | Field labels on the first exemplar |
| --- | --- |
| `BR` | Description, Rationale, Acceptance Criteria, Priority, Stakeholder |
| `FR` | Description, Relates To, Rationale, Acceptance Criteria, Data Requirements, Inputs, Outputs, Validations, Priority, Complexity, Dependencies, Assumptions |
| `NFR-P` | Requirement, Measurement Method, Load Conditions, Rationale, Acceptance Criteria, Priority |
| `NFR` shared | Requirement, Rationale, Acceptance Criteria, Priority |
| `INT` | Purpose, Integration Type, Data Exchanged, Integration Pattern, Authentication, Error Handling, SLA, Owner, Rationale, Acceptance Criteria, Priority |

A missing required identifier or a missing required label fails the document. Placeholder tokens (`[PROJECT_NAME]`, `TBD`, `[VERSION]`) make the file a structural fixture, not an import.

`UC` headings stay in the body in version 1. Do not convert them into `Persona`, `UserJourney`, `JourneyStage`, `Scenario`, or `UserStory`. An ArcKit use-case heading does not carry the PKC journey contract (persona, goal, stage outcome, success metric, and story acceptance). Section 7.1 says when a later mapping may call PKC.

### 5.2 Requirements compact-table grammar

Accept the header `ID | Requirement | Priority`. Each data row is one requirement. The identifier must match a supported prefix. Preserve the statement verbatim.

The mapping declares a separate compact profile and its minimum fields. The compact fixture has no per-item acceptance criteria and no rationale. Record those fields as unavailable. Do not invent them.

Normalize documented MoSCoW values only. `Must` and `MUST_HAVE` become `must`. Reject an unknown column under a strict mapping.

Parse a document-control table or a traceability table only with its own header profile. Do not treat those rows as requirements.

### 5.3 ADR grammar

One native ADR file is one `DecisionRecord`. Parse the declared identifier, title, status, and explicit reference lists. Preserve Context, Decision, Consequences, and Alternatives in the body.

Do not invent a decision from the first 500 characters. Do not default a missing status to `accepted`.

ADR option labels on the stock template: Description, Implementation approach, Wardley Evolution Stage.

ADR trace groups: Business Requirements, Functional Requirements, Non-Functional Requirements.

### 5.4 Risk grammar

Each recognized risk section, such as `R-001`, is one `Risk`.

Header labels on the stock template: Category, Status, Risk Owner, Action Owner.

Scores are table rows under `Assessment | Rating | Justification`. They are not bold labels. Read likelihood, impact, and score from those rows when the header matches. Reject the block when the header does not match. Reject an unknown scoring scale. Do not guess a scale.

Preserve root cause, triggers, and mitigations as narrative.

### 5.5 Rejected grammar

A prose block with no identifier, an unknown required label, an unknown column, a malformed table, or an unrecognized layout fails the document. Do not call an LLM. A person may request recovery under Section 14.

## 6. Mapping and signatures

`mappings/arckit-pkc-v1.json` defines the mapping version, document families, structural profiles, identifier patterns, prefix-to-type mappings, field transforms, relation permissions, minimum fields, and expected signature digests.

This file is an adapter contract. It does not amend the PKC relation registry.

A signature is:

* the ordered heading skeleton, with identifier instances folded to subtype patterns
* declaration labels detected only at field boundaries
* exact table header rows

Exclude paragraph text. Exclude bold emphasis inside prose or bullets. Keep a separate signature for each subtype label set. Record the algorithm version with each digest.

A statement edit does not break the signature. A new label or a new column does. The document then fails until a reviewed mapping update and a regression fixture exist.

`/arckit:customize` can change a template. Do not apply the stock map to an unknown layout. Do not compute a digest at runtime and trust it. A map revision pins the reviewed structure.

## 7. Output model

One requirements file may emit many `Requirement` concepts. One risk register may emit many `Risk` concepts. One ADR file emits one `DecisionRecord`.

A traceability row may become an edge. It does not become a matrix node. Version 1 does not create Data Engineering Knowledge Capture nodes, System Architecture Capture nodes, test artefacts, or acceptance nodes.

Illustrative concept. The compact fixture does not contain every field shown here.

```yaml
type: Requirement
title: Save incomplete benefit claims
kind: functional
priority: must
external_system: arckit
external_id: 001-benefits-portal/REQ/FR-001
source_document: ARC-001-REQ-v1.1
source_path: projects/001-benefits-portal/ARC-001-REQ-v1.1.md
source_item_id: FR-001
template_signature: "<reviewed-signature>"
mapping_version: "1"
source_state: present
generated: true
verified: false
wiki_key: arckit-001-benefits-portal-req-fr-001
```

Copy the source statement verbatim. Do not paraphrase it.

`wiki_key` and the concept path come from `external_id`, not from the title. Confirm the directory prefix against the installed PKC layout before the first write. The sample path is not a frozen PKC path.

### 7.1 Product plane stays in PKC

PKC v0.10.0 already stores a PRD journey as a graph. The skill is `pkc-capture-prd`. The script is `scripts/pkc_capture.py prd`. A journey section is not free-form notes on a Feature.

| Concept or operation | Owner | Adapter |
| --- | --- | --- |
| `Requirement`, `DecisionRecord`, `Risk` | PKC | Version 1 import |
| `Persona`, `UserJourney`, `JourneyStage` | PKC | Do not write. Call PKC when a reviewed journey mapping exists |
| `Scenario`, `UserStory` | PKC | Same |
| `Feature` and Epic from a stage | PKC | Same. `--no-backlog` skips Epic and work `Story` |
| WikiTicket `Story` | WikiTicket through PKC | Never create a second work item |
| Context pack | PKC and OKF | Read it. Do not reimplement packing |

PKC writes these edges. The adapter must not emit them itself:

| Relation | From | To |
| --- | --- | --- |
| `for_persona` | `UserJourney`, `JourneyStage`, or `UserStory` | `Persona` |
| `covers` | `UserJourney` | `JourneyStage` |
| `stage_of` | `JourneyStage` | `UserJourney` |
| `realized_by` | `JourneyStage` | `Feature` |
| `realized_by` | `Scenario` | `UserStory` |
| `derived_from` | `Feature` or Epic | `JourneyStage` |
| `illustrates` | `Scenario` | `JourneyStage` |
| `has_scenario` | `UserJourney` | `Scenario` |
| `implements_step` | `UserStory` | `JourneyStage` |
| `traces_to` | `UserStory` | `Requirement` |
| `maps_to` | `UserStory` | work `Story` |
| `child_of` | work `Story` | Epic |
| `implements` | work `Story` | `Feature` |
| `golden_thread_for` | `UserJourney` | `Release` |

Version 1 does not call `pkc_capture.py prd`.

A later optional phase may translate an ArcKit source into PKC's `journey.json` shape and then call that command. The translator fills only fields the ArcKit source states. If persona, goal, stage outcome, or story acceptance is absent, it does not call PKC and it does not invent those fields. It passes `--no-backlog` when the caller asks for the product plane only.

That phase is specified in Section 21. It is not version 1. ArcKit use-case headings and backlog stories are not, by themselves, a PKC journey.

## 8. Identity, paths, and collisions

Stable identity is `external_system: arckit` plus `external_id: {project}/{family}/{item_id}`.

Example: `001-benefits-portal/REQ/BR-001`.

`source_document` holds the versioned ArcKit name, such as `ARC-001-REQ-v1.1`. `source_path` holds the native path. Neither value is part of identity. A title edit does not change identity, `wiki_key`, or output path. A rename from `ARC-001-REQ-v1.0` to `ARC-001-REQ-v1.1` updates provenance. It does not add a concept.

Before any write, scan the selected input set. Two sources that claim the same `external_id` are a conflict.

* A full import fails the run before any write when any conflict exists.
* An incremental import blocks writes for the conflicting identity and for any edge that targets it. It does not declare uniqueness from the changed file alone. It checks on-disk siblings or a complete validated inventory.

Index existing PKC concepts by `external_system` and `external_id`.

* Reuse the existing path.
* If that identity already occupies two PKC paths, fail closed. Write nothing for that identity.
* For a new identity, derive the path from a stable encoding of project, family, and item id. Do not use a title slug. Check that the candidate path is empty, or already holds this same identity, before writing.

On rerun, look up the identity before using the planned path. If the identity lives at another path, update that path. Do not create a twin.

Idempotence compares canonical content and preserves PKC timestamps. Account for PKC author stamping and merge behavior. If an imported concept was edited locally after import, do not overwrite it. Report divergence and require review.

## 9. Relationships

The adapter owns this direction table inside the versioned map. PKC lists relation names. PKC does not enforce these endpoint pairs.

| Relation | From | To |
| --- | --- | --- |
| `satisfies` | Functional, nonfunctional, integration, or data `Requirement` | Business `Requirement` |
| `related_to` | `Requirement` | `Scenario` |
| `decides` | `DecisionRecord` | `Requirement` or `Feature` |
| `mitigates` | `DecisionRecord` | `Risk` |
| `depends_on` | `DecisionRecord` | `DecisionRecord` |
| `supersedes` | `DecisionRecord` | `DecisionRecord` |
| `exposes` | `Risk` | `Requirement` or `Feature` |

Version 1 does not emit `related_to`. PKC v0.10.0 has a `Scenario` type. An ArcKit `UC` heading is still not that type. Do not point `related_to` at a Scenario the adapter invented.

Emit an edge only in the owning direction. A reversed edge fails the document.

A target must already exist in the PKC bundle or be in a plan that has passed preflight. Do not create a node to satisfy an edge. An unknown or ambiguous target fails the document.

A cross-document edge may resolve against the in-memory batch. Do not write the edge until the target's source document has also passed preflight. If the two documents cannot be committed in the same batch, refuse the dependent write. Do not leave an edge aimed at a concept that will not be committed.

Other PKC uses of `satisfies`, including Feature to Requirement, stay as they are. Do not reverse an edge to match a different convention.

## 10. Source state

| State | Definition | Action |
| --- | --- | --- |
| `present` | The identifier is in a valid current source | Create or update through PKC |
| `missing` | A previously imported identifier is absent from a source that passed preflight | Proposed update only. A person must accept it |
| `conflict` | More than one current source claims the identity | Block writes for that identity |

Mark `missing` only after the replacement source parses, the signature matches, references validate, and the source inventory is complete. A malformed file marks nothing missing.

Compare only concepts whose provenance names the same stable project and document family. Do not mark unrelated concepts. For a renamed or versioned file, match project and family. Do not require the old basename to equal the new basename.

The proposal keeps the concept file, keeps `truth_state`, and keeps `verified: false`. It does not delete the concept. It records the previous source and the new inventory.

Do not persist `source_state: missing` as a silent update. Put the proposal in the report. Include it in the knowledge PR only after a person authorizes that change.

## 11. Import lifecycle

Stages: discover, inventory identities, parse, check signature, map, resolve relations, PKC preflight, plan, gated write.

1. Discover native sources inside the configured root.
2. Build the identity inventory. Stop before any write on a full-import conflict.
3. Parse each document with one grammar profile.
4. Check the structural signature and required fields.
5. Resolve explicit links against existing PKC concepts and plans that passed preflight.
6. Check direction against the versioned map.
7. Validate planned frontmatter with the installed PKC validator. If PKC only validates a bundle, stage an isolated bundle and validate it before promotion. Do not check `type` alone.
8. Record each action as `created`, `updated`, `skipped`, or `refused`. `missing` and `conflict` are proposals or blocks, not silent writes.
9. Stop before the first write for a document that failed. Do not emit a partial document.
10. Open the dispatcher brain session. Call `write_knowledge()` for the accepted plan. Refresh the catalog through PKC.
11. Close the session. Open one knowledge PR for the coalesced batch. Do not merge it.

A power loss can leave a prefix of files or a missing write event. A rerun uses the same identity and path. PR review is the publication boundary.

A document with an unresolved relationship is not synchronized.

## 12. Hosts

Every host calls `scripts/arckit_hook.py`. The hook translates the event, finds a native source path, and enqueues it. It does not parse. It does not write knowledge. It does not open a brain session.

The dispatcher reads a durable queue, coalesces repeated edits of the same document, and owns the session and the PR.

| Host | Manifest | Trigger |
| --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json`, `hooks/hooks.json` | `PostToolUse` on `Write`, `Edit`, `MultiEdit` |
| Codex | `.codex-plugin/plugin.json`, `hooks/codex-hooks.json` | `PostToolUse`. No `ExitPlanMode` |
| Cursor | `.cursor-plugin/plugin.json`, `hooks/cursor-hooks.json` | `afterFileEdit` and `postToolUse` |
| Grok Build | `.grok-plugin/marketplace.json` | Claude-compatible layout. Do not invent a Grok event name |
| Agent Plugins 1.0 | root `plugin.json` | Skill or command. No file hook |
| Deep Agents and Grok Bot | `hosts/<host>/SKILL.md` | Explicit invocation |
| Continuous integration | documented reconcile command | Changes the hooks never saw |

Ignore a missing path and an unrelated tool event. Do not enqueue them.

Deduplicate Cursor's two events by normalized path and source revision.

Accept only the three filename families under `projects/**/`. Ignore `okf/**`, `knowledge/**`, catalogs, write events, and staging files. A PKC write must not start an ArcKit import.

The dispatcher waits until the file snapshot is stable. It hashes the source bytes before planning and checks the hash again before the first write. If the bytes changed, it plans again. It does not write the stale plan.

The queue stores paths and fingerprints. It does not store source bodies. Queue metadata is not knowledge.

Do not install this importer as the WikiTicket `pre-commit` hook. Do not change `pkc-curate.sh`.

## 13. Dispatch and isolation

Coalesce repeated edits. Group a bounded set of valid changes into one brain session and one knowledge PR.

Support `--dry-run`, `--sync`, and `--reconcile`. A dry run writes no concept, no write event, no catalog, and no PR.

```text
read shared brain
  -> brain_session.py open
  -> deterministic preflight
  -> write_knowledge()
  -> PKC catalog refresh
  -> brain_session.py close
  -> one PR
  -> a person merges
```

The hook does not write the ArcKit tree and does not amend the ArcKit commit.

If PR creation fails, keep the isolated branch and report its location. Do not write to `main`.

If a queued path disappears, reconcile the source inventory before any missing proposal. A missing path is not a deletion.

## 14. Agent-assisted recovery

A person must request recovery. A parser failure does not start an LLM. The hook writes a recovery request and returns nonzero. It reports recovery as pending. It does not report success.

After authorization, use this loop. The cap is three attempts. Stop early when the proposal does not change.

1. The recovery role reads the ArcKit document, the failure report, the approved map, and the direction table.
2. It proposes a mapping change or a staged concept set. It writes nothing to the brain.
3. The judge role reads the ArcKit document and the candidate. It does not read the recovery role's notes.
4. The judge returns `PASS`, `REVISE`, or `BLOCK`.
5. On `REVISE`, return the structured findings to the recovery role.
6. On `PASS`, run the deterministic gate on the candidate.
7. Write only if that gate passes.

A judge pass does not override a failed gate. A judge pass does not set `verified: true`.

The judge checks completeness, fidelity, identity, relationships, and provenance. It builds its own item inventory from the source and compares that inventory to the candidate.

The recovery role must not invent requirements, acceptance criteria, identifiers, or targets. It must not change an `external_id`. It must not weaken the gate.

Schemas:

* `schemas/recovery-request.schema.json`
* `schemas/recovery-result.schema.json`
* `schemas/judge-result.schema.json`

Failure types: `TEMPLATE_MISMATCH`, `MISSING_LABEL`, `UNKNOWN_PREFIX`, `DUPLICATE_ID`, `REVERSED_EDGE`, `UNRESOLVED_REF`, `CONFLICT`, `PLACEHOLDER`.

A repair that should apply later becomes a proposal: a versioned map that is not active, a copy of the source as a regression fixture, and the file SHA-256. A person merges it. Until that merge, the importer keeps rejecting that shape.

Do not send source content to a model without that human authorization.

## 15. Crash recovery and write events

`write_knowledge()` emits a write event only for `created` and `updated`. `skipped` emits no event.

A crash after the concept bytes land and before the event does not get repaired by a later `skipped` run.

* A rerun uses the same identity and path. It does not add a twin.
* An identical retry returns `skipped` and adds no event.
* A changed concept may return `updated` and add one event.
* `arckit_doctor.py` reports a concept with no matching event. It does not write a synthetic event and it does not add a concept to force one.
* Reports separate import completion, event completeness, and PR publication.

Do not claim exactly-once event delivery. PKC does not guarantee it.

## 16. Security

Treat ArcKit Markdown as untrusted data. Do not execute embedded scripts, shell commands, or links. Reject path traversal and symlink escapes. Scrub secrets from diagnostics. Follow PKC author-identity rules. Preserve requirement statements under the organization's handling policy.

Source fields named `verified`, `truth_state`, `author`, or approval do not override PKC state. A document-control signature is provenance, not an approval.

Run with least privilege. Use the existing brain remote. Do not embed credentials.

## 17. Reporting

Emit JSON and a short summary. Include source path, source hash, grammar, map version, signature, document result, planned paths, counts for `created`, `updated`, `skipped`, and `refused`, conflicts, rejected blocks with locations, unresolved targets, direction failures, missing proposals, session id, PR reference when one exists, and write-event gaps.

Separate parse outcome from publication outcome.

Exit nonzero for a deterministic failure, a missing validator, an identity conflict, missing write authority, or a failed PR when publication was requested.

## 18. Tests

### Positive

1. Import the pinned benefits-portal requirements fixture. One concept per supported `BR`, `FR`, and `DR` row. The statement matches the source. Those rows are `BR-001`, `BR-002`, `FR-001`, `FR-002`, `DR-001`, and `DR-002`.
2. Repeat the import. Every target is `skipped`. No new concept. No new write event.
3. Change one priority. That identity is `updated`. The others are `skipped`. One new write event.
4. Change one title. `external_id`, `wiki_key`, and path stay the same.
5. Rename `ARC-001-REQ-v1.0` to `ARC-001-REQ-v1.1`. Identities stay. Provenance updates. No twin.
6. A bold phrase inside a bullet is not a field label.
7. A cross-document reference resolves only to an existing PKC concept or to a plan that passed preflight.
8. Repeated host events for one source become one queue entry and at most one PR.

### Negative

1. Two files claim one `external_id`. The conflict is found before any write.
2. Unknown prefix, missing identifier, missing required field, or unknown column. No writes.
3. A changed signature or a new nonfunctional label set fails until a reviewed map exists.
4. An unresolved target fails the document. The target is not created.
5. A reversed relation fails the document.
6. A malformed replacement marks nothing `missing`.
7. A valid replacement omits an old identifier. The result is a proposal. `truth_state` is unchanged. The concept is not deleted. `source_state: missing` is not persisted until a person accepts it.
8. Two PKC paths already share one identity. Further writes for that identity are refused.
9. A local edit to an imported concept is not overwritten.
10. A path outside `projects/**`, or an unsupported family, is ignored.
11. The hook does not call `write_knowledge()`, `brain_session.py`, or `git push`. The dispatcher does.
12. A missing PKC validator blocks writes.
13. Source bytes that change during preflight cause a replan. The stale plan is not written.
14. A crash before any write leaves no concepts.
15. A crash between writes leaves only canonical paths. The rerun finishes those paths and does not add twins.
16. A crash after the file write and before the event: the rerun skips the identical concept, adds no event, and the doctor reports the gap.
17. A judge `PASS` with a failed deterministic gate writes nothing.
18. Recovery does not start unless a person requests it.
19. A scripted `REVISE` then `PASS`, then a green gate, allows the write. `verified` stays `false`. The fourth attempt does not run.
20. A promoted map is a proposal file. The active map is unchanged.
21. A dry run does not mutate the filesystem or the remote.
22. A failed PR keeps the isolated branch and reports the failure. The dispatcher does not merge.
23. An edge whose target document failed preflight is not written.

### Retrieval, after a journey mapping exists

These tests do not run in version 1. They run only after the optional phase in Section 7.1 has called `pkc_capture.py prd` for a source that already contains the required journey fields.

1. A `UserStory` produced by PKC `traces_to` the imported `Requirement` whose id the journey JSON named. The adapter did not write the `UserStory`.
2. A 2-hop pack of the Feature includes the journey neighborhood when `max_nodes` is high enough. On the sample auth feature that budget is 60. Assert the hops, not the default budget.
3. With the default budget, the stage and the user story may appear while the journey, persona, or scenario is clipped. That clip is PKC ranking. It is not an import failure.
4. `--no-backlog` leaves no Epic and no work `Story`. The product-plane nodes still exist.

### Release gate

Release only when the applicable tests pass against the pinned fixtures and the installed PKC version.

Do not claim positive ADR or risk conversion from placeholder templates. Release notes state which shapes are verified and which are template-level only. Document the PKC compatibility range and the host-hook matrix that was actually run.

## 19. Exclusions

No ArcKit document generation. No import of ArcKit's full document catalogue. No compliance, procurement, Wardley, or governance-register migration. No changes to DEKC, SAC, AGER, WikiTicket, `pkc_adr_import.py`, or `pkc-curate.sh`. No second datastore. No bidirectional edit of ArcKit from PKC. No automatic deletion. No implicit human verification. No automatic PR merge. No invented filled ADR or risk fixture. No adapter-owned journey parser. No direct writes of `Persona`, `UserJourney`, `JourneyStage`, `Scenario`, `UserStory`, `Feature`, Epic, or WikiTicket `Story`.

## 20. Implementation sequence

1. Create `SpillwaveSolutions/pkc-arckit`. Pin the four upstream files and record the upstream commit.
2. Test the installed PKC contract: validation, identity lookup, session open and close, writes, events, and catalog refresh.
3. Implement discovery, signatures, both requirements grammars, and duplicate detection. No writes yet.
4. Add ADR and risk parsers as strict template profiles. Do not claim positive coverage.
5. Implement mapping, target resolution, direction checks, snapshot recheck, and the preflight plan.
6. Implement idempotent writes, missing proposals, divergence detection, and failure injection.
7. Add the shared hook, the durable queue, the dispatcher, and PR lifecycle.
8. Add the human-authorized recovery loop, the three schemas, both role files, and doctor diagnostics.
9. Add security tests, the host matrix, and the docs in `docs/`.
10. Only after version 1 is green: a reviewed journey mapping that emits PKC's `journey.json` and calls `pkc_capture.py prd`. Do not start that work by parsing ArcKit `UC` headings.

Do not start at the hook. The parser and the gate come first. Do not start the journey phase before the requirements importer. Section 21 is the Phase 2 contract. Do not implement it inside Phase 1.

## 21. Phase 2, after inspection

Phase 1 stays the acceptance gate in Section 12 and the tests in Section 18. Phase 2 does not weaken it.

ArcKit covers more of the product lifecycle than Phase 1 imports. That is not the same as a typed journey graph. Three levels:

| Level | What ArcKit has | Adapter rule |
| --- | --- | --- |
| Concepts in prose | Personas, goals, use-case flows, stakeholder drivers | Candidate inputs only |
| Documents and JSON | `ARC-*-REQ-*`, `ARC-*-STKE-*`, `ARC-*-BKLG-*.json`, sequence diagrams | Parse a supported structure or refuse |
| Typed journey | Explicit journey, stage, step, and the edges between them | Not in the backlog JSON. Do not invent it |

### 21.1 What was inspected

Sources: `plugins/arckit-claude/commands/backlog.md` section 13.4, `plugins/arckit-claude/hooks/validate-backlog-totals.mjs`, `.arckit/templates/stakeholder-drivers-template.md`, and the requirements template use-case section. No filled `ARC-*-BKLG-*.json` is in the ArcKit tree. The JSON below is the command's example, not a JSON Schema file and not a vendored artefact.

The backlog command writes JSON before Markdown. A Claude Code `PreToolUse` hook on `ARC-*-BKLG-*.json` recomputes totals, epic membership, sprint numbers, and MoSCoW drift against the requirements file. Other hosts do not run that hook. The adapter must not trust the hook as a cross-host validator. It checks the same invariants itself or refuses the file.

A story object has `id`, `epic`, `title`, `as_a`, `i_want`, `so_that`, `acceptance_criteria`, `priority`, `story_points`, `sprint`, `status`, `requirements`, `component`, `dependencies`, and `tasks`.

An epic object has `id`, `title`, `business_requirement`, `priority`, `points`, `sprints`, and `stories`.

A traceability row has `requirement`, `type`, `stories`, `sprint`, `status`, and an optional `priority_change` string.

There is no `journey`, `stage`, or `scenario` field.

The stakeholder template maps Stakeholder to Driver to Goal to Outcome (`SD-1`, `G-1`, `O-1`). It does not define a persona journey.

The requirements template defines `Persona` (Role, Goals, Pain Points, Technical Proficiency) and `UC-1` (Actor, Preconditions, Main Flow, Postconditions, Alternative Flows, Exception Flows, Business Rules, Priority). A functional requirement may name a use case in `Relates To`.

`/arckit:diagram` can emit a sequence diagram. `/arckit:dfd` is a data-flow diagram. Neither is a journey record.

The backlog command tells the model to invent a generic persona and to infer "so that" when the requirement does not state them. Those strings are not source facts.

### 21.2 What Phase 2 may translate

Phase 2 reads native files and the backlog JSON. It still does not write `Persona`, `UserJourney`, `JourneyStage`, `Scenario`, `UserStory`, `Feature`, Epic, or a work `Story`. It builds PKC's `journey.json` and calls `pkc_capture.py prd`, or it stops.

| ArcKit field | PKC `journey.json` field | Rule |
| --- | --- | --- |
| Requirements persona block, all four labels present | `personas[]` | Copy role, goals, and pain points. Skip a block that is still a placeholder. |
| Stakeholder `SD` / `G` / `O` | none | Not a persona. Leave it out. |
| `UC-1` Main Flow | none by default | A numbered flow is not a stage list. A later mapping version may say otherwise. This one does not. |
| Story `as_a` | persona name | Use it only when it equals a parsed persona title. `user`, `system`, and `administrator` as generic fallbacks do not match. Report `missing persona`. |
| Story `i_want` | `capability` | Copy the string. |
| Story `so_that` | `outcome` | Copy the string only if the command did not mark it inferred. If the file does not say, report `missing outcome`. |
| `acceptance_criteria` | `acceptance` | Copy the list. Do not rewrite "It's done when" into Given/When/Then. |
| `traceability[].requirement` and `stories` | `requirement_ids` | This is the deterministic link from a story to a requirement id such as `FR-001`. |
| Epic `business_requirement` | provenance | Record `BR-001`. Do not create the Epic in the adapter. |
| `sprint`, `story_points`, `velocity`, `tasks`, `component` | none | Delivery planning. Out of the product plane. |

### 21.3 The stage gap

PKC's capture requires a stage on every user story. ArcKit's backlog JSON does not name one. A sprint theme, a sequence-diagram title, or the epic title is not a stage.

If the source does not name the journey and the stage, Phase 2 writes a report and does not call `pkc_capture.py prd`. It does not invent the graph.

### 21.4 Do not mint a second Requirement or Feature

PKC `capture_user_story` links `traces_to` by requirement title. `_ensure_named` creates a thin Requirement when that title's path is missing. `capture_journey_stage` does the same for a Feature.

Phase 1 paths come from `external_id`, not from the title slug. A call that passes the ArcKit title will not find the imported Requirement. PKC will create a second one.

Phase 2 must not pass `requirement` or `feature` into `journey.json` until the installed PKC resolves an existing concept by `external_system` and `external_id`. Until that lookup exists, Phase 2 stops after the report. Adding that lookup is a PKC change. It is not an adapter writer.

`--no-backlog` remains the default for any call that does run. A person must ask for the Epic and the work `Story`.

### 21.5 Phase 2 gate

1. Phase 1 has already imported the requirements, or this run imports them first under Section 12.
2. The backlog JSON parses. Totals match the items. Every story's epic exists. Sprint numbers are null or at least 1.
3. Every `requirements` id and every traceability requirement id exists as an imported `Requirement`.
4. Persona, capability, outcome, and acceptance are copied, not inferred.
5. Journey and stage are present in the source, or the run stops with `missing stage`.
6. The PKC build can attach `traces_to` and `realized_by` to the existing phase-1 nodes. If it cannot, the run stops with `unresolved identity`.
7. Only then call `pkc_capture.py prd`. A person must pass `--with-backlog` to drop `--no-backlog`.
8. `generated` stays `true` and `verified` stays `false` on every node PKC writes from that call.

The retrieval tests in Section 18 stay in this phase. They do not run in Phase 1.

No filled backlog file is pinned yet. Do not claim Phase 2 coverage from the command example. The first fixture must be a real `ARC-*-BKLG-*.json` plus its requirements file, hashed like the Phase 1 fixtures.
