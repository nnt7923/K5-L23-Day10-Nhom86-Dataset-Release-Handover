#!/usr/bin/env python3
"""Module đối chiếu Detection (YOLO) ↔ Panoptic Segmentation (COCO)
Dành cho vai trò Đối chiếu A (Người 4 - Nguyễn Quốc Hưng).

Chức năng:
1. Chuyển đổi bounding box YOLO (chuẩn hoá) sang toạ độ pixel thực.
2. Ánh xạ danh mục lớp giữa classes.txt và panoptic.json theo tên lớp.
3. Đối chiếu pixel mask (scripts/pngutil.py) để tính độ phủ thực tế.
4. Phát hiện ứng viên:
   - class_swap / category_swap: Box và Segment trùng vị trí (IoU/pixel cao) nhưng khác lớp.
   - bbox_drift: Box và Segment cùng lớp nhưng box bị lệch khỏi mask vật thể.
5. Xuất danh sách ứng viên chuẩn vào candidates.json để review bằng mắt.

Chỉ dùng thư viện chuẩn của Python + scripts/pngutil.py.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# Thêm đường dẫn scripts để dùng pngutil
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pngutil  # noqa: E402


def parse_classes(classes_path: Path) -> dict[int, str]:
    """Đọc classes.txt (80 lớp detection) -> map class_id sang tên lớp."""
    classes = {}
    for line in classes_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        classes[int(parts[0])] = parts[1].strip().lower()
    return classes


def load_panoptic_metadata(panoptic_path: Path):
    """Đọc panoptic.json -> map categories, images, annotations."""
    doc = json.loads(panoptic_path.read_text(encoding="utf-8"))
    cat_by_id = {}
    cat_by_name = {}
    thing_cats = set()
    for c in doc["categories"]:
        cid = c["id"]
        cname = c["name"].strip().lower()
        cat_by_id[cid] = cname
        cat_by_name[cname] = cid
        if c.get("isthing", 0) == 1:
            thing_cats.add(cid)

    images = {im["id"]: im for im in doc["images"]}
    anns_by_stem = {}
    for ann in doc["annotations"]:
        stem = Path(ann["file_name"]).stem
        anns_by_stem[stem] = ann

    return cat_by_id, cat_by_name, thing_cats, images, anns_by_stem


def parse_yolo_boxes(txt_path: Path, width: int, height: int, class_id_to_name: dict[int, str]) -> list[dict]:
    """Đổi nhãn YOLO sang toạ độ pixel [x1, y1, x2, y2]."""
    boxes = []
    if not txt_path.is_file():
        return boxes
    for line in txt_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            cid = int(parts[0])
            xc, yc, w, h = map(float, parts[1:5])
        except ValueError:
            continue

        cname = class_id_to_name.get(cid, f"class_{cid}")
        x1 = max(0.0, (xc - w / 2) * width)
        y1 = max(0.0, (yc - h / 2) * height)
        x2 = min(float(width), (xc + w / 2) * width)
        y2 = min(float(height), (yc + h / 2) * height)
        bw_px = x2 - x1
        bh_px = y2 - y1

        boxes.append({
            "class_id": cid,
            "class_name": cname,
            "bbox": [x1, y1, x2, y2],
            "center": (xc * width, yc * height),
            "size": (bw_px, bh_px),
            "area_rel": w * h,
            "area_px": bw_px * bh_px
        })
    return boxes


def bbox_iou(b1: list[float], b2: list[float]) -> float:
    """Tính IoU giữa 2 bounding box [x1, y1, x2, y2]."""
    ix1 = max(b1[0], b2[0])
    iy1 = max(b1[1], b2[1])
    ix2 = min(b1[2], b2[2])
    iy2 = min(b1[3], b2[3])
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


def get_mask_segment_coverage(pixels: bytes, width: int, height: int, seg_bbox: list[int], target_sid: int, det_box: list[float]) -> tuple[int, int, float]:
    """Tính tỉ lệ pixel của segment target_sid nằm lọt trong det_box."""
    sx, sy, sw, sh = seg_bbox
    bx1, by1, bx2, by2 = det_box

    total_px = 0
    in_box_px = 0

    y_start = max(0, sy)
    y_end = min(height, sy + sh)
    x_start = max(0, sx)
    x_end = min(width, sx + sw)

    for y in range(y_start, y_end):
        row_offset = y * width
        for x in range(x_start, x_end):
            idx = (row_offset + x) * 3
            sid = pngutil.segment_id(pixels, idx)
            if sid == target_sid:
                total_px += 1
                if bx1 <= x <= bx2 and by1 <= y <= by2:
                    in_box_px += 1

    coverage = (in_box_px / total_px) if total_px > 0 else 0.0
    return total_px, in_box_px, coverage


def find_swap_and_drift_candidates(delivery_dir: Path) -> list[dict]:
    """Hàm đối chiếu chính tìm ứng viên swap và drift."""
    delivery_dir = Path(delivery_dir)
    classes_file = delivery_dir / "classes.txt"
    panoptic_file = delivery_dir / "panoptic.json"
    labels_dir = delivery_dir / "labels"
    masks_dir = delivery_dir / "masks"

    if not classes_file.is_file() or not panoptic_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy classes.txt hoặc panoptic.json trong {delivery_dir}")

    class_id_to_name = parse_classes(classes_file)
    cat_by_id, cat_by_name, thing_cats, images, anns_by_stem = load_panoptic_metadata(panoptic_file)

    candidates = []

    # Duyệt từng ảnh theo danh mục ảnh panoptic
    for im_id, im_info in sorted(images.items()):
        stem = Path(im_info["file_name"]).stem
        lbl_path = labels_dir / f"{stem}.txt"
        mask_path = masks_dir / f"{stem}.png"

        w_img = im_info["width"]
        h_img = im_info["height"]

        # Parse YOLO boxes
        det_boxes = parse_yolo_boxes(lbl_path, w_img, h_img, class_id_to_name)
        ann = anns_by_stem.get(stem)
        if not ann:
            continue

        # Lọc segments thing (bỏ iscrowd)
        thing_segs = []
        for s in ann.get("segments_info", []):
            cid = s.get("category_id")
            if cid in thing_cats and not s.get("iscrowd", 0):
                sname = cat_by_id.get(cid, f"cat_{cid}")
                sx, sy, sw, sh = s["bbox"]
                thing_segs.append({
                    "id": s["id"],
                    "category_id": cid,
                    "class_name": sname,
                    "bbox_px": [sx, sy, sx + sw, sy + sh],
                    "raw_bbox": s["bbox"],
                    "center": (sx + sw / 2, sy + sh / 2),
                    "size": (sw, sh),
                    "area": s.get("area", sw * sh)
                })

        mask_data = None  # Lazy load mask nếu có nghi vấn

        # -------------------------------------------------------------
        # 1. TÌM ỨNG VIÊN SWAP (class_swap hoặc category_swap)
        # Bbox YOLO và Segment Panoptic trùng vị trí (IoU cao) nhưng khác tên lớp
        # -------------------------------------------------------------
        for db in det_boxes:
            # Bỏ qua box có class_id không hợp lệ (thuộc lỗi luật invalid_class của Validator B)
            if db["class_id"] not in class_id_to_name:
                continue
            if db["area_rel"] < 0.005:  # Bỏ qua box quá bé khó nhìn
                continue
            for ps in thing_segs:
                if ps["area"] < 300:  # Bỏ qua segment quá bé
                    continue
                iou = bbox_iou(db["bbox"], ps["bbox_px"])
                if iou >= 0.50 and db["class_name"] != ps["class_name"]:
                    # Kiểm tra thêm pixel coverage để loại bớt chồng lấn tự nhiên
                    if mask_data is None and mask_path.is_file():
                        mask_data = pngutil.read_rgb(mask_path)

                    if mask_data:
                        mw, mh, mpixels = mask_data
                        tot_px, in_bx, cov = get_mask_segment_coverage(mpixels, mw, mh, ps["raw_bbox"], ps["id"], db["bbox"])
                    else:
                        cov = iou

                    # Nếu coverage cao >= 0.60: segment thực sự nằm trọn trong box -> Khả năng cao bị swap nhãn!
                    if cov >= 0.60:
                        candidates.append({
                            "image": stem,
                            "type": "class_swap",  # Cần xem ảnh: nếu det sai -> class_swap, nếu pan sai -> category_swap
                            "possible_types": ["class_swap", "category_swap"],
                            "det_class": db["class_name"],
                            "pan_class": ps["class_name"],
                            "iou": round(iou, 3),
                            "pixel_coverage": round(cov, 3),
                            "det_bbox": [round(x, 1) for x in db["bbox"]],
                            "pan_bbox": ps["raw_bbox"],
                            "segment_id": ps["id"],
                            "note": f"det ghi '{db['class_name']}' nhưng pan ghi '{ps['class_name']}' (IoU={iou:.2f}, cov={cov:.2f})"
                        })

        # -------------------------------------------------------------
        # 2. TÌM ỨNG VIÊN BBOX DRIFT (bbox_drift)
        # Cùng tên lớp, nhưng box bị dịch chuyển/trôi khỏi mask vật thể
        # -------------------------------------------------------------
        # Ghép cặp greedy theo IoU cho các đối tượng cùng tên lớp
        same_class_pairs = []
        for i, db in enumerate(det_boxes):
            if db["area_rel"] < 0.005 or db["size"][0] < 15 or db["size"][1] < 15:
                continue
            for j, ps in enumerate(thing_segs):
                if ps["area"] < 400:
                    continue
                if db["class_name"] == ps["class_name"]:
                    iou = bbox_iou(db["bbox"], ps["bbox_px"])
                    if iou > 0.20:
                        same_class_pairs.append((iou, i, j))

        same_class_pairs.sort(reverse=True, key=lambda x: x[0])
        matched_boxes = set()
        matched_segs = set()

        for iou, i, j in same_class_pairs:
            if i in matched_boxes or j in matched_segs:
                continue
            matched_boxes.add(i)
            matched_segs.add(j)

            db = det_boxes[i]
            ps = thing_segs[j]

            # Tính độ lệch tâm chuẩn hoá theo kích thước box
            dx = abs(db["center"][0] - ps["center"][0]) / max(db["size"][0], 1.0)
            dy = abs(db["center"][1] - ps["center"][1]) / max(db["size"][1], 1.0)
            drift_metric = math.sqrt(dx * dx + dy * dy)

            # Nếu IoU bị giảm (0.35 <= IoU <= 0.82) và độ lệch tâm >= 0.12
            if 0.35 <= iou <= 0.82 and drift_metric >= 0.12:
                if mask_data is None and mask_path.is_file():
                    mask_data = pngutil.read_rgb(mask_path)

                if mask_data:
                    mw, mh, mpixels = mask_data
                    tot_px, in_bx, cov = get_mask_segment_coverage(mpixels, mw, mh, ps["raw_bbox"], ps["id"], db["bbox"])
                else:
                    cov = iou

                # Dấu hiệu cốt lõi của bbox_drift: segment bị rớt một phần đáng kể ra ngoài box (cov < 0.85)
                # Hoặc box trôi làm che sang vùng trống
                if cov < 0.85 and tot_px >= 400:
                    candidates.append({
                        "image": stem,
                        "type": "bbox_drift",
                        "det_class": db["class_name"],
                        "pan_class": ps["class_name"],
                        "iou": round(iou, 3),
                        "pixel_coverage": round(cov, 3),
                        "drift_metric": round(drift_metric, 3),
                        "det_bbox": [round(x, 1) for x in db["bbox"]],
                        "pan_bbox": ps["raw_bbox"],
                        "segment_id": ps["id"],
                        "note": f"box '{db['class_name']}' lệch khỏi mask (IoU={iou:.2f}, cov={cov:.2f}, lệch tâm={drift_metric:.2f})"
                    })

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Đối chiếu Detection ↔ Panoptic tìm ứng viên class_swap và bbox_drift")
    parser.add_argument("delivery", help="Đường dẫn thư mục delivery")
    parser.add_argument("--out", default=None, help="Đường dẫn file candidates.json xuất ra")
    args = parser.parse_args()

    delivery_dir = Path(args.delivery)
    if not delivery_dir.is_dir():
        print(f"Lỗi: Không tìm thấy thư mục {delivery_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Đang đối chiếu trên thư mục: {delivery_dir}")
    candidates = find_swap_and_drift_candidates(delivery_dir)
    print(f"[+] Tìm thấy {len(candidates)} ứng viên (swap + drift):")

    for i, c in enumerate(candidates, 1):
        print(f"  {i:2d}. [{c['type']}] Ảnh {c['image']}: {c['note']}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_doc = {"candidates": candidates}
        out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[+] Đã ghi danh sách ứng viên vào {out_path}")


if __name__ == "__main__":
    main()
