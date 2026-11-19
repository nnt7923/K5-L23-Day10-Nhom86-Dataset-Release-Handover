#!/usr/bin/env python3
"""Module đối chiếu Detection ↔ Panoptic (Phần Đối chiếu B - Người 5)
Phát hiện ứng viên:
- missing_box: Segment thing lớn (bỏ iscrowd) nhưng không có box detection bao phủ.
- instance_merge: Một segment thing có pixel nằm trong từ 2 box detection cùng lớp trở lên.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pngutil  # noqa: E402
from cross_check import (  # noqa: E402
    bbox_iou,
    get_mask_segment_coverage,
    load_panoptic_metadata,
    parse_classes,
    parse_yolo_boxes,
)


def find_missing_and_merge_candidates(
    delivery_dir: Path,
    min_area_px: int = 1200,          # Diện tích tối thiểu của segment để xét missing_box
    min_area_rel: float = 0.005,      # Tỉ lệ diện tích tối thiểu so với toàn ảnh (0.5%)
    max_cover_missing: float = 0.25,  # Độ phủ box cao nhất < 25% -> nghi ngờ missing_box
    min_merge_cov: float = 0.20,      # Mỗi box phải chứa >= 20% pixel của segment
    min_merge_fill: float = 0.25,     # Pixel segment phải chiếm >= 25% diện tích mỗi box
) -> list[dict]:
    """Tìm ứng viên missing_box và instance_merge."""
    delivery_dir = Path(delivery_dir)
    classes_file = delivery_dir / "classes.txt"
    panoptic_file = delivery_dir / "panoptic.json"
    labels_dir = delivery_dir / "labels"
    masks_dir = delivery_dir / "masks"

    class_id_to_name = parse_classes(classes_file)
    cat_by_id, _, thing_cats, images, anns_by_stem = load_panoptic_metadata(panoptic_file)

    candidates = []

    for _, im_info in sorted(images.items()):
        stem = Path(im_info["file_name"]).stem
        lbl_path = labels_dir / f"{stem}.txt"
        mask_path = masks_dir / f"{stem}.png"

        w_img = im_info["width"]
        h_img = im_info["height"]
        img_area = w_img * h_img

        det_boxes = parse_yolo_boxes(lbl_path, w_img, h_img, class_id_to_name)
        ann = anns_by_stem.get(stem)
        if not ann:
            continue

        # Lọc segment thing và bỏ qua iscrowd
        thing_segs = []
        for s in ann.get("segments_info", []):
            cid = s.get("category_id")
            if cid in thing_cats and not s.get("iscrowd", 0):
                sx, sy, sw, sh = s["bbox"]
                thing_segs.append({
                    "id": s["id"],
                    "category_id": cid,
                    "class_name": cat_by_id.get(cid, f"cat_{cid}"),
                    "bbox_px": [sx, sy, sx + sw, sy + sh],
                    "raw_bbox": s["bbox"],
                    "area": s.get("area", sw * sh),
                })

        mask_data = None  # Lazy load mask PNG

        for ps in thing_segs:
            seg_area = ps["area"]
            seg_cls = ps["class_name"]

            # ---------------------------------------------------------
            # 1. TÌM ỨNG VIÊN MISSING_BOX
            # Segment thing lớn nhưng không có box detection bao phủ
            # ---------------------------------------------------------
            if seg_area >= min_area_px and (seg_area / max(img_area, 1)) >= min_area_rel:
                best_cov = 0.0
                best_iou = 0.0

                for db in det_boxes:
                    if db["class_id"] not in class_id_to_name:
                        continue
                    iou = bbox_iou(db["bbox"], ps["bbox_px"])
                    if iou > best_iou:
                        best_iou = iou

                    # Chỉ đọc mask PNG nếu box có giao cắt với khung segment
                    if iou > 0.0:
                        if mask_data is None and mask_path.is_file():
                            mask_data = pngutil.read_rgb(mask_path)
                        if mask_data:
                            mw, mh, mpixels = mask_data
                            _, _, cov = get_mask_segment_coverage(
                                mpixels, mw, mh, ps["raw_bbox"], ps["id"], db["bbox"]
                            )
                        else:
                            cov = iou

                        if cov > best_cov:
                            best_cov = cov

                if best_cov < max_cover_missing and best_iou < max_cover_missing:
                    candidates.append({
                        "image": stem,
                        "type": "missing_box",
                        "det_class": None,
                        "pan_class": seg_cls,
                        "iou": round(best_iou, 3),
                        "pixel_coverage": round(best_cov, 3),
                        "det_bbox": None,
                        "pan_bbox": ps["raw_bbox"],
                        "segment_id": ps["id"],
                        "note": f"segment '{seg_cls}' lớn (area={seg_area}px) nhưng thiếu box (max_cov={best_cov:.2f})",
                    })

            # ---------------------------------------------------------
            # 2. TÌM ỨNG VIÊN INSTANCE_MERGE
            # Một segment thing có pixel nằm trong >= 2 box cùng lớp
            # ---------------------------------------------------------
            same_cls_boxes = [
                db for db in det_boxes
                if db["class_id"] in class_id_to_name and db["class_name"] == seg_cls
            ]
            if len(same_cls_boxes) >= 2 and seg_area >= 400:
                if mask_data is None and mask_path.is_file():
                    mask_data = pngutil.read_rgb(mask_path)

                matched_boxes = []
                for db in same_cls_boxes:
                    if bbox_iou(db["bbox"], ps["bbox_px"]) <= 0.0:
                        continue
                    if mask_data:
                        mw, mh, mpixels = mask_data
                        _, in_bx, cov = get_mask_segment_coverage(
                            mpixels, mw, mh, ps["raw_bbox"], ps["id"], db["bbox"]
                        )
                        box_fill = in_bx / max(db["area_px"], 1.0)
                    else:
                        cov = bbox_iou(db["bbox"], ps["bbox_px"])
                        box_fill = cov

                    if cov >= min_merge_cov and box_fill >= min_merge_fill:
                        matched_boxes.append((db, cov))

                # Loại trường hợp 2 box trùng nhau (duplicate_box)
                if len(matched_boxes) >= 2:
                    valid_pair = False
                    for idx1 in range(len(matched_boxes)):
                        for idx2 in range(idx1 + 1, len(matched_boxes)):
                            if bbox_iou(matched_boxes[idx1][0]["bbox"], matched_boxes[idx2][0]["bbox"]) < 0.70:
                                valid_pair = True
                                break
                        if valid_pair:
                            break

                    if valid_pair:
                        cov_str = ", ".join(f"{c:.2f}" for _, c in matched_boxes)
                        candidates.append({
                            "image": stem,
                            "type": "instance_merge",
                            "det_class": seg_cls,
                            "pan_class": seg_cls,
                            "iou": round(max(bbox_iou(b["bbox"], ps["bbox_px"]) for b, _ in matched_boxes), 3),
                            "pixel_coverage": round(sum(c for _, c in matched_boxes), 3),
                            "det_bbox": [round(x, 1) for x in matched_boxes[0][0]["bbox"]],
                            "det_bboxes": [[round(x, 1) for x in b["bbox"]] for b, _ in matched_boxes],
                            "pan_bbox": ps["raw_bbox"],
                            "segment_id": ps["id"],
                            "note": f"1 segment '{seg_cls}' phủ {len(matched_boxes)} box cùng lớp (cov=[{cov_str}])",
                        })

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Đối chiếu B: Tìm ứng viên missing_box và instance_merge")
    parser.add_argument("delivery", help="Đường dẫn thư mục delivery")
    parser.add_argument("--out", default=None, help="File JSON xuất ứng viên")
    parser.add_argument("--min-area", type=int, default=1200, help="Diện tích pixel tối thiểu cho missing_box")
    parser.add_argument("--min-rel", type=float, default=0.005, help="Tỉ lệ diện tích tối thiểu cho missing_box")
    parser.add_argument("--max-cov", type=float, default=0.25, help="Ngưỡng coverage tối đa cho missing_box")
    parser.add_argument("--merge-cov", type=float, default=0.20, help="Ngưỡng coverage mỗi box cho instance_merge")
    parser.add_argument("--merge-fill", type=float, default=0.25, help="Ngưỡng lấp đầy box cho instance_merge")
    args = parser.parse_args()

    candidates = find_missing_and_merge_candidates(
        Path(args.delivery),
        min_area_px=args.min_area,
        min_area_rel=args.min_rel,
        max_cover_missing=args.max_cov,
        min_merge_cov=args.merge_cov,
        min_merge_fill=args.merge_fill,
    )
    print(f"[+] Tìm thấy {len(candidates)} ứng viên (missing_box + instance_merge):")
    for i, c in enumerate(candidates, 1):
        print(f"  {i:2d}. [{c['type']}] Ảnh {c['image']}: {c['note']}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"candidates": candidates}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()