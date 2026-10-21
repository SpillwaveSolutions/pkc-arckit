"""Command line for the Phase 1 importer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pkc_arckit import __version__
from pkc_arckit.apply import PkCUnavailable, apply_plan
from pkc_arckit.engine import discover, dump_plan, plan_paths


def _pinned(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in data.get("signatures", {}).items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pkc-arckit", description="Import native ArcKit Markdown into PKC.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    plan = sub.add_parser("plan", help="Parse and validate. The default writes nothing.")
    plan.add_argument("root", type=Path)
    plan.add_argument("paths", nargs="*", type=Path)
    plan.add_argument("--bundle", type=Path, default=None)
    plan.add_argument("--signatures", type=Path, default=None)
    plan.add_argument("--write", action="store_true", help="Write via an installed PKC checkout.")
    plan.add_argument("--pkc-root", type=Path, default=None)
    plan.add_argument("--author", default="pkc-arckit")

    args = parser.parse_args(argv)
    root = args.root.resolve()
    paths = args.paths or discover(root)
    if args.paths:
        paths = [path if path.is_absolute() else root / path for path in args.paths]
    result = plan_paths(root, list(paths), bundle=args.bundle, pinned_signatures=_pinned(args.signatures))
    payload = dump_plan(result)
    if args.write:
        if args.pkc_root is None or args.bundle is None:
            print("refusing write: --pkc-root and --bundle are required", file=sys.stderr)
            return 2
        try:
            payload["applied"] = apply_plan(result, args.bundle, pkc_root=args.pkc_root, author=args.author)
        except PkCUnavailable as exc:
            print(f"refusing write: {exc}", file=sys.stderr)
            return 2
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    if result.status in {"conflict", "refused", "stale"}:
        return 1
    if result.status == "partial":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
