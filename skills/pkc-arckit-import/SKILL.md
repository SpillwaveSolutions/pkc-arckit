---
name: pkc-arckit-import
description: Plan a deterministic import of native ArcKit REQ, ADR, and RISK Markdown into Project Knowledge Capture. Use when an ArcKit document should become Requirement, DecisionRecord, or Risk concepts. Do not use for journeys, backlogs, or ArcKit OKF exports.
---

# Import ArcKit into PKC

Run the planner. Do not write knowledge unless the user names a PKC checkout and a bundle.

```bash
python3 -m pkc_arckit.cli plan <arckit-root>
```

Refuse the write when `--pkc-root` is absent. Do not invent concepts for headings that failed. Do not delete a concept that disappeared from the source. Leave `verified` false.

Phase 2 journey import is a separate command, `product`. It validates a backlog and stops. It does not call `pkc_capture.py prd`.
