"""Pha 5 — truy vết ticket của team AI (chỉ thư viện chuẩn).

Dùng:
    py -X utf8 tools/trace_query.py runs/r86007/delivery --out runs/r86007/trace.json
    py -X utf8 tools/trace_query.py delivery --out submission/de_an/trace.json   # đề ẩn
    # truyền tay tên lớp + danh sách cảnh (ghi đè phần tự đọc):
    py -X utf8 tools/trace_query.py runs/r86007/delivery --out runs/r86007/trace.json \
        --cls cup --scenes scene_553,scene_863

Chỉ đọc thư mục delivery truyền vào. Tự lấy từ tài liệu (không gõ cứng):
  - scene bị báo: các chuỗi scene_<số> trong incoming/ticket.md
  - lớp bị đổi quy tắc + phiên bản mới: mục "## vX.Y" đầu tiên trong guideline/changelog.md
    có nhắc "Lớp `<tên>`"
Tiêu chí:
  - job "guideline cũ" = guideline ghi ở JOB (jobs.csv) nhỏ hơn phiên bản mới
    (KHÔNG dùng guideline_version ghi ở từng ảnh — đó có thể là lỗi guideline_mismatch)
  - ảnh "có lớp đó" = labels/<ảnh>.txt có ít nhất một box class_id của lớp đó
  - tier_a = ảnh đủ điều kiện và nằm trong scene bị báo; tier_b = ảnh đủ điều kiện còn lại
  - notify = annotator + reviewer của các job chứa ảnh tier_a và tier_b
"""
import argparse
import csv
import json
import re
from pathlib import Path


def vtuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def parse_changelog(text: str):
    """Trả về (tên lớp bị đổi, phiên bản áp dụng quy tắc mới)."""
    for block in re.split(r"^##\s+", text, flags=re.M)[1:]:
        version = block.split("\n", 1)[0].strip()
        m = re.search(r"[Ll]ớp\s+`([^`]+)`", block)
        if m:
            return m.group(1).strip(), version
    raise SystemExit("Không tìm thấy lớp bị đổi quy tắc trong changelog.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("delivery")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cls", help="tên lớp bị đổi quy tắc (mặc định: đọc từ changelog.md)")
    ap.add_argument("--scenes", help="danh sách cảnh, cách nhau dấu phẩy (mặc định: đọc từ ticket.md)")
    ap.add_argument("--new-version", help="phiên bản guideline mới (mặc định: đọc từ changelog.md)")
    a = ap.parse_args()
    d = Path(a.delivery)

    if a.scenes:
        scenes = {s.strip() for s in a.scenes.split(",") if s.strip()}
    else:
        scenes = set(re.findall(r"scene_\d+", (d / "incoming" / "ticket.md").read_text(encoding="utf-8")))
    if a.cls and a.new_version:
        cls_name, new_ver = a.cls, a.new_version
    else:
        auto_cls, auto_ver = parse_changelog((d / "guideline" / "changelog.md").read_text(encoding="utf-8"))
        cls_name, new_ver = a.cls or auto_cls, a.new_version or auto_ver

    # classes.txt: mỗi dòng "<id> <tên>" (vd "41 cup"); dòng chỉ có tên thì id = số thứ tự dòng
    name2id = {}
    lines = [ln.strip() for ln in (d / "classes.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        parts = ln.split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            name2id[parts[1].strip()] = int(parts[0])
        else:
            name2id[ln] = i
    if cls_name not in name2id:
        raise SystemExit(f"Lớp {cls_name!r} không có trong classes.txt")
    cls_id = name2id[cls_name]

    with open(d / "jobs.csv", encoding="utf-8", newline="") as f:
        jobs = {r["job_id"]: r for r in csv.DictReader(f)}
    old_jobs = {j for j, r in jobs.items() if vtuple(r["guideline"]) < vtuple(new_ver)}

    items = json.loads((d / "metadata.json").read_text(encoding="utf-8"))["items"]

    def has_class(image: str) -> bool:
        p = d / "labels" / f"{image}.txt"
        if not p.is_file():
            return False
        for ln in p.read_text(encoding="utf-8").splitlines():
            parts = ln.split()
            if parts and parts[0].lstrip("-").isdigit() and int(parts[0]) == cls_id:
                return True
        return False

    tier_a, tier_b, used_jobs = [], [], set()
    for it in items:
        if it["job_id"] not in old_jobs or not has_class(it["image"]):
            continue
        (tier_a if it["scene_id"] in scenes else tier_b).append(it["image"])
        used_jobs.add(it["job_id"])

    notify = sorted({jobs[j]["annotator"] for j in used_jobs} | {jobs[j]["reviewer"] for j in used_jobs})
    out = {"tier_a": sorted(tier_a), "tier_b": sorted(tier_b), "notify": notify}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Scene bị báo: {sorted(scenes)} | lớp: {cls_name} (id {cls_id}) | quy tắc mới từ {new_ver}")
    print(f"Job guideline cũ (theo jobs.csv): {sorted(old_jobs)} | job liên quan: {sorted(used_jobs)}")
    print(f"tier_a {len(tier_a)} ảnh · tier_b {len(tier_b)} ảnh · notify {notify}")


if __name__ == "__main__":
    main()
