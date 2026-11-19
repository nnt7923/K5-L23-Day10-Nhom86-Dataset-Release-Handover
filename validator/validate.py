#!/usr/bin/env python3
"""Command-line entry point for the group's delivery validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

try:  # Support both direct execution and ``import validator.validate``.
    from .file_metadata import Error, resolve_delivery_path, validate_file_metadata
except ImportError:
    from file_metadata import Error, resolve_delivery_path, validate_file_metadata


def read_json(delivery: Path, filename: str) -> Any:
    """Read one JSON file, refusing paths that escape delivery."""

    path = resolve_delivery_path(delivery, filename)
    if path is None:
        raise ValueError(f"missing or unsafe delivery file: {filename}")
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def read_csv(delivery: Path, filename: str) -> list[dict[str, str]]:
    """Read one header-based CSV file from delivery."""

    path = resolve_delivery_path(delivery, filename)
    if path is None:
        raise ValueError(f"missing or unsafe delivery file: {filename}")
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def read_classes(delivery: Path, filename: str = "classes.txt") -> dict[int, str]:
    """Read ``class_id name`` lines into a mapping."""

    path = resolve_delivery_path(delivery, filename)
    if path is None:
        raise ValueError(f"missing or unsafe delivery file: {filename}")

    classes: dict[int, str] = {}
    with path.open("r", encoding="utf-8") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            line = raw_line.strip()
            if not line:
                continue
            class_id_text, separator, name = line.partition(" ")
            if not separator or not name.strip():
                raise ValueError(f"invalid classes.txt line {line_number}")
            classes[int(class_id_text)] = name.strip()
    return classes


def load_delivery(delivery: Path) -> dict[str, Any]:
    """Load the shared inputs once for all present and future rule modules."""

    root = delivery.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"delivery is not a directory: {delivery}")

    manifest = read_json(root, "manifest.json")
    metadata = read_json(root, "metadata.json")
    panoptic = read_json(root, "panoptic.json")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("items"), dict):
        raise ValueError("manifest.json must contain an items object")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("items"), list):
        raise ValueError("metadata.json must contain an items array")
    if not isinstance(panoptic, dict):
        raise ValueError("panoptic.json must contain a JSON object")

    return {
        "manifest": manifest,
        "metadata": metadata,
        "jobs": read_csv(root, "jobs.csv"),
        "classes": read_classes(root),
        "panoptic": panoptic,
    }


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
    return normalize_errors(findings)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


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
