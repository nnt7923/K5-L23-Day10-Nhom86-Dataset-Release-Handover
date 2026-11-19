#!/usr/bin/env python3
"""Command-line entry point for the group's delivery validator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

try:  # Support both direct execution and ``import validator.validate``.
    from .file_metadata import Error, validate_file_metadata
    from .io_utils import load_delivery, write_json
    from .label_rules import validate_labels
    from .metadata_rules import validate_metadata
except ImportError:
    from file_metadata import Error, validate_file_metadata
    from io_utils import load_delivery, write_json
    from label_rules import validate_labels
    from metadata_rules import validate_metadata


def normalize_errors(findings: Iterable[Error]) -> list[Error]:
    """Normalize findings and remove duplicate ``(type, target)`` pairs."""

    normalized: list[Error] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        error_type = str(finding["type"])
        target = str(finding["target"])
        key = (error_type, target)
        if key not in seen:
            seen.add(key)
            normalized.append({"type": error_type, "target": target})
    return normalized


def collect_errors(delivery: Path, data: dict[str, Any]) -> list[Error]:
    """Run registered rule modules.

    Validator B can add another iterable here while keeping deduplication and
    output formatting centralized in ``normalize_errors``.
    """

    findings: list[Error] = []
    findings.extend(validate_file_metadata(delivery, data["manifest"]))
    findings.extend(validate_metadata(data["metadata"], data["jobs"]))
    findings.extend(validate_labels(delivery, data["manifest"], data["panoptic"]))
    return normalize_errors(findings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a dataset delivery")
    parser.add_argument("delivery", type=Path, help="delivery directory to validate")
    parser.add_argument("--out", type=Path, required=True, help="output errors.json")
    parser.add_argument(
        "--candidates",
        type=Path,
        help="optional candidate output (P2 placeholder in this phase)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        data = load_delivery(args.delivery)
        errors = collect_errors(args.delivery.resolve(), data)
        write_json(args.out, {"errors": errors})
        if args.candidates is not None:
            write_json(args.candidates, {"candidates": []})
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
