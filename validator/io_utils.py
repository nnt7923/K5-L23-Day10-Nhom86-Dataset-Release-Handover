"""Shared, path-safe input and output helpers for validator modules."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def resolve_delivery_path(delivery: Path, relative_path: object) -> Path | None:
    """Return an existing file contained by delivery, or None.

    Resolving before opening also prevents manifest paths and symlinks from
    making the validator read a file outside the supplied delivery directory.
    """

    try:
        root = delivery.resolve(strict=True)
        raw_path = Path(relative_path)  # type: ignore[arg-type]
        if raw_path.is_absolute():
            return None
        candidate = (root / raw_path).resolve(strict=True)
        candidate.relative_to(root)
    except (OSError, TypeError, ValueError):
        return None

    return candidate if candidate.is_file() else None


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


def write_json(path: Path, payload: object) -> None:
    """Write a consistently formatted UTF-8 JSON document."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
