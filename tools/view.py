#!/usr/bin/env python3
"""Công cụ hỗ trợ xem ảnh ứng viên & chia hàng đợi review cho 7 thành viên
Vai trò: Đối chiếu B (Người 5). Được phép sử dụng thư viện Pillow.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from PIL import Image, ImageDraw


def find_image_path(images_dir: Path, stem: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png"):
        p = images_dir / f"{stem}{ext}"
        if p.is_file():
            return p
    return None


def render_candidate(
    delivery_dir: Path,
    cand: dict,
    idx: int,
    out_img_dir: Path,
    pad: int = 45,
    min_crop_size: int = 520,
) -> str:
    stem = cand["image"]
    img_path = find_image_path(delivery_dir / "images", stem)
    if not img_path:
        return ""

    base_img = Image.open(img_path).convert("RGBA")
    w, h = base_img.size

    # 1. Tô mờ vùng pixel của segment panoptic (nếu có mask và segment_id)
    mask_path = delivery_dir / "masks" / f"{stem}.png"
    seg_id = cand.get("segment_id")
    pan_bbox = cand.get("pan_bbox")  # [x, y, sw, sh]

    if mask_path.is_file() and seg_id is not None and pan_bbox:
        mask_img = Image.open(mask_path).convert("RGB")
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ov_px = overlay.load()
        mk_px = mask_img.load()

        sx, sy, sw, sh = [int(v) for v in pan_bbox]
        for y in range(max(0, sy), min(h, sy + sh)):
            for x in range(max(0, sx), min(w, sx + sw)):
                r, g, b = mk_px[x, y]
                if (r + g * 256 + b * 65536) == seg_id:
                    ov_px[x, y] = (0, 220, 110, 95)  # Xanh lá bán trong suốt
        base_img = Image.alpha_composite(base_img, overlay)

    canvas = base_img.convert("RGB")
    draw = ImageDraw.Draw(canvas)

    all_boxes = []

    # 2. Vẽ khung Panoptic (màu xanh lá)
    if pan_bbox:
        px1, py1, pw, ph = pan_bbox
        p_rect = [px1, py1, px1 + pw, py1 + ph]
        all_boxes.append(p_rect)
        draw.rectangle(p_rect, outline=(0, 200, 80), width=3)
        pan_lbl = f"PAN: {cand.get('pan_class', '')}"
        draw.text((max(2, px1), max(2, py1 - 14)), pan_lbl, fill=(0, 230, 90))

    # 3. Vẽ khung Detection (màu đỏ) - hỗ trợ cả 1 box và nhiều box (instance_merge)
    det_boxes = cand.get("det_bboxes") or ([cand["det_bbox"]] if cand.get("det_bbox") else [])
    for b_idx, d_rect in enumerate(det_boxes):
        all_boxes.append(d_rect)
        draw.rectangle(d_rect, outline=(240, 45, 45), width=3)
        det_lbl = f"DET: {cand.get('det_class', '')}" + (f" #{b_idx+1}" if len(det_boxes) > 1 else "")
        draw.text((max(2, d_rect[0]), min(h - 14, d_rect[3] + 2)), det_lbl, fill=(255, 70, 70))

    # 4. Cắt vùng quanh vật thể và phóng to nếu ảnh nhỏ
    if all_boxes:
        ux1 = max(0, int(min(b[0] for b in all_boxes)) - pad)
        uy1 = max(0, int(min(b[1] for b in all_boxes)) - pad)
        ux2 = min(w, int(max(b[2] for b in all_boxes)) + pad)
        uy2 = min(h, int(max(b[3] for b in all_boxes)) + pad)
        cropped = canvas.crop((ux1, uy1, ux2, uy2))
    else:
        cropped = canvas

    cw, ch = cropped.size
    if max(cw, ch) < min_crop_size and max(cw, ch) > 0:
        scale = min_crop_size / max(cw, ch)
        cropped = cropped.resize((int(cw * scale), int(ch * scale)), Image.Resampling.NEAREST)

    out_name = f"{idx:03d}_{stem}_{cand['type']}.jpg"
    out_path = out_img_dir / out_name
    cropped.save(out_path, quality=92)
    return out_name


def split_queue_and_render(
    delivery_dir: Path,
    candidates_path: Path,
    out_dir: Path,
    num_members: int = 7,
) -> None:
    raw = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates = raw["candidates"] if isinstance(raw, dict) else raw

    # Sắp xếp theo tên ảnh để phân bổ đều cho 7 thành viên (i mod 7)
    candidates.sort(key=lambda x: (x.get("image", ""), x.get("type", "")))

    out_img_dir = out_dir / "annotated"
    out_img_dir.mkdir(parents=True, exist_ok=True)

    member_rows: list[list[list[str]]] = [[] for _ in range(num_members)]

    for i, cand in enumerate(candidates):
        rendered_file = render_candidate(delivery_dir, cand, i + 1, out_img_dir)
        member_idx = i % num_members
        # Giữ đúng 4 cột chuẩn: image,type,verdict,note
        member_rows[member_idx].append([cand["image"], cand["type"], "", ""])
        print(f"[{i+1:02d}/{len(candidates):02d}] TV{member_idx+1} <- {rendered_file} | {cand.get('note', '')}")

    for m_idx in range(num_members):
        csv_path = out_dir / f"review_log_tv{m_idx+1}.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["image", "type", "verdict", "note"])
            writer.writerows(member_rows[m_idx])

    print(f"\n[+] Đã xuất {len(candidates)} ảnh vào {out_img_dir}/ và chia thành {num_members} file CSV tại {out_dir}/")


def merge_member_logs(logs_dir: Path, out_csv: Path) -> None:
    """Gộp các file review_log_tv*.csv thành review_log.csv hoàn chỉnh."""
    rows = []
    for p in sorted(logs_dir.glob("review_log_tv*.csv")):
        with p.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("verdict", "").strip():
                    rows.append([r["image"].strip(), r["type"].strip(), r["verdict"].strip(), r["note"].strip()])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image", "type", "verdict", "note"])
        writer.writerows(rows)
    print(f"[+] Đã gộp {len(rows)} dòng review vào {out_csv}")


def main():
    parser = argparse.ArgumentParser(description="Công cụ xem ảnh ứng viên & chia hàng đợi review")
    parser.add_argument("--delivery", type=Path, help="Thư mục delivery")
    parser.add_argument("--candidates", type=Path, help="File candidates.json")
    parser.add_argument("--out", type=Path, required=True, help="Thư mục xuất ảnh và file review_log")
    parser.add_argument("--members", type=int, default=7, help="Số thành viên chia hàng đợi")
    parser.add_argument("--merge", action="store_true", help="Gộp các file review_log_tv*.csv trong --out")
    args = parser.parse_args()

    if args.merge:
        merge_member_logs(args.out, args.out / "review_log.csv")
    else:
        if not args.delivery or not args.candidates:
            parser.error("Cần truyền đủ --delivery và --candidates")
        split_queue_and_render(args.delivery, args.candidates, args.out, args.members)


if __name__ == "__main__":
    main()