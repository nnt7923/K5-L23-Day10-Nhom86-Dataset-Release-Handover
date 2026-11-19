#!/usr/bin/env python3
"""P4 - Dung lo ban giao v2 tu errors.json (khong ghi de v1). Chi dung thu vien chuan.

  python tools/build_v2.py --run runs/r86007
  python tools/build_v2.py --run runs/r86007 --rework-hash 000000000123   # anh wrong_hash da mo xem va thay bi hong

Doc  : <run>/delivery (CHI DOC), <run>/errors.json
Ghi  : <run>/handover/<release_id>_v2/  (images, labels, manifest.csv, label_summary.csv,
       truyvet.csv, rework_queue.csv, README.txt)

Sau do chay:
  python scripts/pack_release.py <run>/handover/<release_id>_v2
  python scripts/lineage.py record --event release --release-id <release_id>_v2 --parent <release_id>
  python scripts/check_handover.py --run <run>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path

# Loi nhan detection / thieu file: anh phai gan lai, roi khoi v2.
DET_REWORK = {"missing_image", "invalid_class", "bbox_out_of_bounds", "duplicate_box",
              "class_swap", "bbox_drift", "missing_box"}
# Loi chi o panoptic: nhan detection van dung, anh o lai v2, bao team panoptic.
PANOPTIC_ONLY = {"invalid_category_id", "thing_overlap", "category_swap", "instance_merge"}
# Sua ngay trong v2.
FIX_IN_V2 = {"wrong_hash", "guideline_mismatch", "scene_leak"}
THRESHOLD = 0.02

ACTION = {
    "missing_image": "bo sung lai anh goc va gan lai nhan",
    "invalid_class": "gan lai class_id (ngoai 0-79)",
    "bbox_out_of_bounds": "ve lai box tran khoi anh",
    "duplicate_box": "xoa box lap va kiem tra lai",
    "class_swap": "gan lai lop cua box detection",
    "bbox_drift": "ve lai box lech khoi vat",
    "missing_box": "bo sung box con thieu",
    "wrong_hash": "anh hong, tai lai anh va gan lai",
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def jpeg_intact(data: bytes) -> bool:
    """Kiem cau truc JPEG co ban: mo dau SOI, ket thuc EOI, co SOF va SOS. Khong thay cho viec mo anh bang mat."""
    if not (data.startswith(b"\xff\xd8") and data.rstrip(b"\x00").endswith(b"\xff\xd9")):
        return False
    markers = set()
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return False
        m = data[i + 1]
        markers.add(m)
        if m == 0xDA:  # SOS: sau do la du lieu nen
            break
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return 0xDA in markers and bool(markers & {0xC0, 0xC1, 0xC2})


def main() -> int:
    ap = argparse.ArgumentParser(description="Dung lo v2 tu errors.json")
    ap.add_argument("--run", required=True)
    ap.add_argument("--rework-hash", nargs="*", default=[],
                    help="anh wrong_hash da mo xem va thay hong that: dua vao rework thay vi ghi hash moi")
    ap.add_argument("--force", action="store_true", help="xoa v2 cu neu da co")
    args = ap.parse_args()

    run = Path(args.run)
    d = run / "delivery"
    rid = json.loads((d / "release.json").read_text(encoding="utf-8"))["release_id"]
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["items"]
    meta = {m["image"]: m for m in json.loads((d / "metadata.json").read_text(encoding="utf-8"))["items"]}
    jobs = {r["job_id"]: r for r in read_csv(d / "jobs.csv")}
    names80 = [ln.split(" ", 1)[1].strip() for ln in (d / "classes.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    errors = json.loads((run / "errors.json").read_text(encoding="utf-8"))["errors"]

    v2 = run / "handover" / f"{rid}_v2"
    if v2.exists():
        if not args.force:
            raise SystemExit(f"{v2} da ton tai. Them --force de dung lai.")
        shutil.rmtree(v2)
    (v2 / "images").mkdir(parents=True)
    (v2 / "labels").mkdir()

    # ---- phan loai loi theo anh
    by_image: dict[str, set[str]] = defaultdict(set)
    leak_scenes: set[str] = set()
    for e in errors:
        if e["type"] == "scene_leak":
            leak_scenes.add(e["target"])
        else:
            by_image[e["target"]].add(e["type"])

    rework: dict[str, str] = {}      # image -> type
    hash_fixed: list[str] = []       # wrong_hash, anh nguyen, chi manifest sai
    hash_damaged: list[str] = []     # wrong_hash, anh hong -> rework
    for img, types in sorted(by_image.items()):
        if img not in man:
            print(f"! bo qua target khong co trong lo: {img}")
            continue
        det = sorted(types & DET_REWORK)
        if det:
            rework[img] = det[0]
            continue
        if "wrong_hash" in types:
            p = d / man[img]["image"]
            if img in args.rework_hash or not p.is_file() or not jpeg_intact(p.read_bytes()):
                rework[img] = "wrong_hash"
                hash_damaged.append(img)
            else:
                hash_fixed.append(img)

    panoptic_only = sorted(i for i, t in by_image.items() if i in man and i not in rework and t & PANOPTIC_ONLY)
    guideline_fixed = sorted(i for i, t in by_image.items() if "guideline_mismatch" in t and i not in rework)

    # ---- split: ca canh ve mot split (da so, hoa thi train)
    scene_imgs: dict[str, list[str]] = defaultdict(list)
    for img, m in meta.items():
        scene_imgs[m["scene_id"]].append(img)
    scene_split: dict[str, str] = {}
    for sc, imgs in scene_imgs.items():
        c = Counter(meta[i]["split"] for i in imgs)
        top = c.most_common()
        scene_split[sc] = "train" if len(top) > 1 and top[0][1] == top[1][1] else top[0][0]

    # ---- copy anh/nhan giu nguyen, tru anh rework
    kept: list[str] = []
    for img in sorted(man):
        if img in rework:
            continue
        it = man[img]
        src_img, src_lab = d / it["image"], d / it["label"]
        if not src_img.is_file() or not src_lab.is_file():
            raise SystemExit(f"{img}: thieu file nhung khong co trong errors.json. Chay lai validator.")
        shutil.copy2(src_img, v2 / "images" / f"{img}.jpg")
        shutil.copy2(src_lab, v2 / "labels" / f"{img}.txt")
        kept.append(img)

    # ---- rework_queue.csv
    rq = []
    for img, t in sorted(rework.items()):
        j = jobs[meta[img]["job_id"]]
        rq.append([img, t, j["annotator"], j["reviewer"], ACTION.get(t, "gan lai nhan")])
    write_csv(v2 / "rework_queue.csv", ["image", "type", "annotator", "reviewer", "action"], rq)

    # ---- manifest.csv
    rows = []
    for sub in ("images", "labels"):
        for p in sorted((v2 / sub).iterdir()):
            if p.is_file():
                rows.append([f"{sub}/{p.name}", sha_bytes(p.read_bytes())])
    write_csv(v2 / "manifest.csv", ["file", "sha256"], rows)

    # ---- label_summary.csv
    counts: Counter = Counter()
    for img in kept:
        for ln in (v2 / "labels" / f"{img}.txt").read_text(encoding="utf-8").splitlines():
            if ln.strip():
                c = int(float(ln.split()[0]))
                counts[names80[c] if 0 <= c < len(names80) else str(c)] += 1
    total = sum(counts.values())
    write_csv(v2 / "label_summary.csv", ["class", "count"],
              [[n, counts[n]] for n in names80 if counts[n]] + [["TOTAL", total]])

    # ---- truyvet.csv (guideline theo JOB, split theo canh)
    tv = []
    for img in kept:
        m = meta[img]
        j = jobs[m["job_id"]]
        tv.append([img, m["scene_id"], scene_split[m["scene_id"]], m["job_id"], j["annotator"], j["reviewer"], j["guideline"]])
    write_csv(v2 / "truyvet.csv", ["image", "scene_id", "split", "job_id", "annotator", "reviewer", "guideline"], tv)

    # ---- README.txt
    g: dict[str, list[str]] = defaultdict(list)
    for jid, j in sorted(jobs.items()):
        g[j["guideline"]].append(jid)
    guideline = ", ".join(f"{v} ({ids[0]}-{ids[-1]})" if len(ids) > 1 else f"{v} ({ids[0]})" for v, ids in sorted(g.items()))
    n_err = len({e["target"] for e in errors})
    rate = n_err / len(man)
    v1 = "Hold" if rate > THRESHOLD else "Release"
    reason = f"{rate:.1%} {'>' if rate > THRESHOLD else '<='} nguong 2% (Day 7)"
    notes = []
    if hash_fixed:
        notes.append(f"wrong_hash {len(hash_fixed)} anh ({', '.join(hash_fixed)}): da mo anh kiem, anh nguyen ven, chi manifest sai nen ghi hash dung")
    if hash_damaged:
        notes.append(f"wrong_hash {len(hash_damaged)} anh hong ({', '.join(hash_damaged)}) dua vao rework")
    if leak_scenes:
        notes.append(f"scene_leak {len(leak_scenes)} canh ({', '.join(sorted(leak_scenes))}) da dua ca canh ve mot split (theo da so)")
    if guideline_fixed:
        notes.append(f"guideline_mismatch {len(guideline_fixed)} anh ({', '.join(guideline_fixed)}) lay guideline theo job trong truyvet.csv")
    if rework:
        owners = sorted({(r[2], r[3]) for r in rq})
        notes.append(f"{len(rework)} anh rework giao lai cho annotator/reviewer: " + "; ".join(f"{a}/{r}" for a, r in owners))
    if panoptic_only:
        notes.append(f"{len(panoptic_only)} anh loi chi o panoptic o lai v2, bao team panoptic: {', '.join(panoptic_only)}")
    (v2 / "README.txt").write_text(
        f"Release: {rid}_v2\n"
        f"Parent: {rid}\n"
        f"Số ảnh: {len(kept)}\n"
        f"Số nhãn: {total}\n"
        f"Guideline: {guideline}\n"
        f"QC v1: {n_err}/{len(man)} = {rate:.1%}\n"
        f"Kết luận v1: {v1} — {reason}\n"
        f"Kết luận v2: Release — tách {len(rework)} ảnh lỗi nhãn detection sang rework_queue, "
        f"sửa hash/guideline/split trong v2, giữ nguyên nhãn đã gán\n"
        f"Ghi chú: {' | '.join(notes) if notes else 'không có'}\n",
        encoding="utf-8")

    print(f"v2: {v2}")
    print(f"  anh giu lai {len(kept)} | nhan {total} | rework {len(rework)} | panoptic-only {len(panoptic_only)}")
    print(f"  QC v1 {n_err}/{len(man)} = {rate:.1%} -> {v1}")
    if hash_fixed:
        print(f"  wrong_hash anh nguyen (hay MO ANH KIEM truoc khi tin): {hash_fixed}")
    if hash_damaged:
        print(f"  wrong_hash anh hong -> rework: {hash_damaged}")
    print("Tiep: pack_release.py, lineage.py record --event release, check_handover.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
