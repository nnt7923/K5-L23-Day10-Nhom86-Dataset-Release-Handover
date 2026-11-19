"""Rules for YOLO detection labels: class ids, box bounds and duplicate boxes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from .io_utils import resolve_delivery_path
except ImportError:
    from io_utils import resolve_delivery_path


Error = dict[str, str]

NUM_CLASSES = 80
# Labels are written with 6 decimals, so an edge exactly on the border can be
# off by about 1e-6 after rounding. Anything beyond this tolerance is outside.
BOUNDS_TOLERANCE = 1e-4
# A duplicated box keeps the same width/height and is shifted by 1-2 pixels.
# Natural COCO pairs that overlap a lot almost never have the same size.
DUPLICATE_SIZE_TOLERANCE_PX = 1.0
DUPLICATE_CENTER_TOLERANCE_PX = 4.0

Box = tuple[int, float, float, float, float]  # class_id, xc, yc, w, h (normalized)


def image_sizes(panoptic: Mapping[str, Any]) -> dict[str, tuple[int, int]]:
    """Map image file stem to ``(width, height)`` using panoptic.json images."""

    sizes: dict[str, tuple[int, int]] = {}
    for image in panoptic.get("images", []):
        if not isinstance(image, Mapping):
            continue
        try:
            stem = Path(str(image["file_name"])).stem
            sizes[stem] = (int(image["width"]), int(image["height"]))
        except (KeyError, TypeError, ValueError):
            continue
    return sizes


def parse_label_lines(text: str) -> tuple[list[Box], bool]:
    """Parse YOLO lines. Return valid boxes and whether a bad class was seen.

    A line whose class id is not an integer in 0..79 counts as an invalid
    class; such lines are not returned as boxes.
    """

    boxes: list[Box] = []
    bad_class = False
    for raw_line in text.splitlines():
        parts = raw_line.split()
        if not parts:
            continue
        try:
            class_id = int(parts[0])
        except ValueError:
            bad_class = True
            continue
        if not 0 <= class_id < NUM_CLASSES:
            bad_class = True
            continue
        if len(parts) != 5:
            continue
        try:
            xc, yc, w, h = (float(value) for value in parts[1:])
        except ValueError:
            continue
        boxes.append((class_id, xc, yc, w, h))
    return boxes, bad_class


def is_out_of_bounds(box: Box) -> bool:
    """True when any edge of a normalized box leaves the [0, 1] image."""

    _, xc, yc, w, h = box
    tol = BOUNDS_TOLERANCE
    return (
        xc - w / 2 < -tol
        or yc - h / 2 < -tol
        or xc + w / 2 > 1 + tol
        or yc + h / 2 > 1 + tol
    )


def has_duplicate(boxes: list[Box], width: int, height: int) -> bool:
    """True when two boxes share class and size and sit 0-4 px apart."""

    pixel_boxes = [
        (class_id, xc * width, yc * height, w * width, h * height)
        for class_id, xc, yc, w, h in boxes
    ]
    for i, first in enumerate(pixel_boxes):
        for second in pixel_boxes[i + 1 :]:
            if first[0] != second[0]:
                continue
            if abs(first[3] - second[3]) > DUPLICATE_SIZE_TOLERANCE_PX:
                continue
            if abs(first[4] - second[4]) > DUPLICATE_SIZE_TOLERANCE_PX:
                continue
            if (
                abs(first[1] - second[1]) <= DUPLICATE_CENTER_TOLERANCE_PX
                and abs(first[2] - second[2]) <= DUPLICATE_CENTER_TOLERANCE_PX
            ):
                return True
    return False


def validate_labels(
    delivery: Path,
    manifest: Mapping[str, Any],
    panoptic: Mapping[str, Any],
) -> Iterable[Error]:
    """Yield ``invalid_class``, ``bbox_out_of_bounds`` and ``duplicate_box``.

    At most one finding per image, checked in that order.
    """

    items = manifest.get("items", {})
    if not isinstance(items, Mapping):
        return
    sizes = image_sizes(panoptic)

    for raw_image_id, item in items.items():
        image_id = str(raw_image_id)
        if not isinstance(item, Mapping):
            continue
        label_path = resolve_delivery_path(delivery, item.get("label"))
        if label_path is None:
            continue
        boxes, bad_class = parse_label_lines(label_path.read_text(encoding="utf-8"))

        if bad_class:
            yield {"type": "invalid_class", "target": image_id}
            continue
        if any(is_out_of_bounds(box) for box in boxes):
            yield {"type": "bbox_out_of_bounds", "target": image_id}
            continue

        image_stem = Path(str(item.get("image", image_id))).stem
        size = sizes.get(image_stem) or sizes.get(image_id)
        if size is not None and has_duplicate(boxes, *size):
            yield {"type": "duplicate_box", "target": image_id}
