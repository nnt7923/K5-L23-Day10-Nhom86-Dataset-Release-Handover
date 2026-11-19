"""Rules for files and their hashes in a delivery directory."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

try:  # Re-export the helper for compatibility with existing imports.
    from .io_utils import resolve_delivery_path
except ImportError:
    from io_utils import resolve_delivery_path


Error = dict[str, str]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate a SHA256 digest from the file's binary contents."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file_metadata(
    delivery: Path,
    manifest: Mapping[str, Any],
) -> Iterable[Error]:
    """Yield ``missing_image`` and ``wrong_hash`` findings.

    Hashes are checked for every existing manifest artifact (image, label and
    mask) that has its corresponding ``*_sha256`` field. At most one
    ``wrong_hash`` is emitted per image ID.
    """

    items = manifest.get("items", {})
    if not isinstance(items, Mapping):
        return

    for raw_image_id, raw_item in items.items():
        image_id = str(raw_image_id)
        if not isinstance(raw_item, Mapping):
            continue

        image_path = resolve_delivery_path(delivery, raw_item.get("image"))
        if image_path is None:
            yield {"type": "missing_image", "target": image_id}
            # A missing image has no bytes to hash and must not also become a
            # wrong_hash finding, even if other artifacts disagree.
            continue

        artifact_paths = (
            ("image", "image_sha256", image_path),
            ("label", "label_sha256", None),
            ("mask", "mask_sha256", None),
        )
        for path_field, hash_field, known_path in artifact_paths:
            if hash_field not in raw_item:
                continue
            path = known_path or resolve_delivery_path(delivery, raw_item.get(path_field))
            if path is None:
                continue
            expected = raw_item[hash_field]
            if not isinstance(expected, str) or sha256_file(path).lower() != expected.lower():
                yield {"type": "wrong_hash", "target": image_id}
                break
