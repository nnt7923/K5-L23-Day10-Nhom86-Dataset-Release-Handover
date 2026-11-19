"""Rules for panoptic labels: unknown category ids and overstated areas."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from .io_utils import resolve_delivery_path
except ImportError:
    from io_utils import resolve_delivery_path

# scripts/pngutil.py is the standard-library PNG reader the lab allows us to use.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
import pngutil  # noqa: E402


Error = dict[str, str]

# Clean COCO masks match the declared area exactly. An occluded segment loses
# a clear share of its pixels, so require both an absolute and a relative gap.
OVERLAP_MIN_PIXELS = 5
OVERLAP_MIN_RATIO = 0.01


def count_segment_pixels(mask_path: Path) -> Counter:
    """Count pixels per segment id, where id = R + G*256 + B*256^2."""

    _, _, pixels = pngutil.read_rgb(mask_path)
    colors = Counter(zip(pixels[0::3], pixels[1::3], pixels[2::3]))
    counts: Counter = Counter()
    for (red, green, blue), number in colors.items():
        counts[red + green * 256 + blue * 65536] += number
    counts.pop(0, None)  # id 0 is unlabeled background
    return counts


def is_area_overstated(declared_area: object, counted: int) -> bool:
    try:
        area = float(declared_area)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    missing = area - counted
    return missing > OVERLAP_MIN_PIXELS and missing > OVERLAP_MIN_RATIO * area


def validate_panoptic(
    delivery: Path,
    manifest: Mapping[str, Any],
    panoptic: Mapping[str, Any],
) -> Iterable[Error]:
    """Yield ``invalid_category_id`` and ``thing_overlap`` findings.

    Annotations are linked to manifest images through the mask file name.
    At most one finding per image, ``invalid_category_id`` first.
    """

    category_ids = {
        category.get("id")
        for category in panoptic.get("categories", [])
        if isinstance(category, Mapping)
    }
    annotation_by_mask = {
        Path(str(annotation.get("file_name"))).name: annotation
        for annotation in panoptic.get("annotations", [])
        if isinstance(annotation, Mapping)
    }

    items = manifest.get("items", {})
    if not isinstance(items, Mapping):
        return

    for raw_image_id, item in items.items():
        image_id = str(raw_image_id)
        if not isinstance(item, Mapping) or item.get("mask") is None:
            continue
        annotation = annotation_by_mask.get(Path(str(item["mask"])).name)
        if annotation is None:
            continue
        segments = [s for s in annotation.get("segments_info", []) if isinstance(s, Mapping)]

        if any(segment.get("category_id") not in category_ids for segment in segments):
            yield {"type": "invalid_category_id", "target": image_id}
            continue

        mask_path = resolve_delivery_path(delivery, item["mask"])
        if mask_path is None:
            continue
        try:
            counts = count_segment_pixels(mask_path)
        except (ValueError, OSError):
            continue
        if any(is_area_overstated(s.get("area"), counts.get(s.get("id"), 0)) for s in segments):
            yield {"type": "thing_overlap", "target": image_id}
