"""Rules that validate per-image metadata against scenes and jobs."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence


Error = dict[str, str]


def validate_scene_leak(metadata: Mapping[str, Any]) -> Iterable[Error]:
    """Yield one finding for each scene containing both train and val images."""

    items = metadata.get("items", [])
    if not isinstance(items, list):
        return

    splits_by_scene: dict[str, set[str]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            continue
        scene_id = item.get("scene_id")
        split = item.get("split")
        if scene_id is None or split not in {"train", "val"}:
            continue
        splits_by_scene.setdefault(str(scene_id), set()).add(str(split))

    for scene_id, splits in splits_by_scene.items():
        if {"train", "val"}.issubset(splits):
            yield {"type": "scene_leak", "target": scene_id}


def validate_guideline_mismatch(
    metadata: Mapping[str, Any],
    jobs: Sequence[Mapping[str, Any]],
) -> Iterable[Error]:
    """Compare every image guideline with the guideline declared by its job."""

    guideline_by_job: dict[str, object] = {}
    for job in jobs:
        if not isinstance(job, Mapping):
            continue
        job_id = job.get("job_id")
        if job_id is not None and "guideline" in job:
            guideline_by_job[str(job_id)] = job["guideline"]

    items = metadata.get("items", [])
    if not isinstance(items, list):
        return

    reported_images: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            continue
        image_id = item.get("image")
        job_id = item.get("job_id")
        if image_id is None or job_id is None or "guideline_version" not in item:
            continue
        job_key = str(job_id)
        if job_key not in guideline_by_job:
            continue
        target = str(image_id)
        if item["guideline_version"] != guideline_by_job[job_key] and target not in reported_images:
            reported_images.add(target)
            yield {"type": "guideline_mismatch", "target": target}


def validate_metadata(
    metadata: Mapping[str, Any],
    jobs: Sequence[Mapping[str, Any]],
) -> Iterable[Error]:
    """Yield findings from all metadata rules."""

    yield from validate_scene_leak(metadata)
    yield from validate_guideline_mismatch(metadata, jobs)
