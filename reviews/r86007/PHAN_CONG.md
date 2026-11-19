# Phân công xem ảnh — seed 86007

Hàng đợi: 27 ứng viên trên 19 ảnh (đã bỏ 2 ảnh đã dính lỗi luật: 000000009483, 000000014380).

Ảnh vẽ sẵn: **khung đỏ = detection (DET)**, **khung + vùng tô xanh = panoptic (PAN)**.

## Trường (@nnt7923) — 3 ảnh → `reviews/r86007/nnt7923.csv`
- **000000000776**
  - `class_swap` — det ghi 'bed' nhưng pan ghi 'teddy bear' (IoU=0.59, cov=1.00) — ảnh: `001_000000000776_class_swap.jpg`
  - `class_swap` — det ghi 'bed' nhưng pan ghi 'teddy bear' (IoU=0.65, cov=1.00) — ảnh: `002_000000000776_class_swap.jpg`
- **000000015440**
  - `class_swap` — det ghi 'bus' nhưng pan ghi 'truck' (IoU=0.97, cov=1.00) — ảnh: `010_000000015440_class_swap.jpg`
- **000000022892**
  - `class_swap` — det ghi 'cat' nhưng pan ghi 'chair' (IoU=0.65, cov=0.85) — ảnh: `020_000000022892_class_swap.jpg`
  - `class_swap` — det ghi 'chair' nhưng pan ghi 'cat' (IoU=0.65, cov=0.86) — ảnh: `021_000000022892_class_swap.jpg`

## Khải (@LeVinhKhai) — 3 ảnh → `reviews/r86007/LeVinhKhai.csv`
- **000000003845**
  - `class_swap` — det ghi 'fork' nhưng pan ghi 'spoon' (IoU=0.83, cov=1.00) — ảnh: `003_000000003845_class_swap.jpg`
  - `class_swap` — det ghi 'spoon' nhưng pan ghi 'fork' (IoU=0.88, cov=0.96) — ảnh: `004_000000003845_class_swap.jpg`
- **000000015497**
  - `class_swap` — det ghi 'couch' nhưng pan ghi 'cat' (IoU=0.64, cov=1.00) — ảnh: `011_000000015497_class_swap.jpg`
- **000000022935**
  - `bbox_drift` — box 'person' lệch khỏi mask (IoU=0.71, cov=0.61, lệch tâm=0.20) — ảnh: `022_000000022935_bbox_drift.jpg`
  - `instance_merge` — 1 segment 'person' phủ 2 box cùng lớp (cov=[0.61, 0.45]) — ảnh: `023_000000022935_instance_merge.jpg`

## Phú (@nguyendinhphu2004) — 3 ảnh → `reviews/r86007/nguyendinhphu2004.csv`
- **000000004395**
  - `missing_box` — segment 'person' lớn (area=174729px) nhưng thiếu box (max_cov=0.07) — ảnh: `005_000000004395_missing_box.jpg`
- **000000016249**
  - `class_swap` — det ghi 'person' nhưng pan ghi 'bench' (IoU=0.53, cov=0.97) — ảnh: `012_000000016249_class_swap.jpg`
- **000000023937**
  - `class_swap` — det ghi 'sheep' nhưng pan ghi 'cow' (IoU=0.57, cov=0.99) — ảnh: `024_000000023937_class_swap.jpg`
  - `class_swap` — det ghi 'cow' nhưng pan ghi 'sheep' (IoU=0.57, cov=0.77) — ảnh: `025_000000023937_class_swap.jpg`

## Hưng (@hungcui) — 3 ảnh → `reviews/r86007/hungcui.csv`
- **000000009590**
  - `class_swap` — det ghi 'cup' nhưng pan ghi 'bowl' (IoU=0.92, cov=1.00) — ảnh: `006_000000009590_class_swap.jpg`
- **000000016451**
  - `class_swap` — det ghi 'handbag' nhưng pan ghi 'backpack' (IoU=0.60, cov=0.99) — ảnh: `013_000000016451_class_swap.jpg`
- **000000024021**
  - `class_swap` — det ghi 'spoon' nhưng pan ghi 'person' (IoU=0.95, cov=1.00) — ảnh: `026_000000024021_class_swap.jpg`

## Chung (@qchung2124) — 3 ảnh → `reviews/r86007/qchung2124.csv`
- **000000009914**
  - `class_swap` — det ghi 'hot dog' nhưng pan ghi 'sandwich' (IoU=0.81, cov=0.97) — ảnh: `007_000000009914_class_swap.jpg`
- **000000018193**
  - `class_swap` — det ghi 'chair' nhưng pan ghi 'person' (IoU=0.57, cov=0.86) — ảnh: `014_000000018193_class_swap.jpg`
  - `class_swap` — det ghi 'person' nhưng pan ghi 'chair' (IoU=0.57, cov=0.64) — ảnh: `015_000000018193_class_swap.jpg`
- **000000025393**
  - `class_swap` — det ghi 'fire hydrant' nhưng pan ghi 'person' (IoU=1.00, cov=1.00) — ảnh: `027_000000025393_class_swap.jpg`

## Long (@Long16082004) — 2 ảnh → `reviews/r86007/Long16082004.csv`
- **000000010092**
  - `class_swap` — det ghi 'chair' nhưng pan ghi 'dining table' (IoU=0.60, cov=0.97) — ảnh: `008_000000010092_class_swap.jpg`
- **000000019402**
  - `bbox_drift` — box 'person' lệch khỏi mask (IoU=0.50, cov=0.58, lệch tâm=0.29) — ảnh: `016_000000019402_bbox_drift.jpg`

## Hiếu (@kudo2382k4) — 2 ảnh → `reviews/r86007/kudo2382k4.csv`
- **000000013597**
  - `class_swap` — det ghi 'dining table' nhưng pan ghi 'cake' (IoU=0.67, cov=1.00) — ảnh: `009_000000013597_class_swap.jpg`
- **000000022705**
  - `class_swap` — det ghi 'refrigerator' nhưng pan ghi 'person' (IoU=0.73, cov=0.94) — ảnh: `017_000000022705_class_swap.jpg`
  - `class_swap` — det ghi 'person' nhưng pan ghi 'refrigerator' (IoU=0.72, cov=0.73) — ảnh: `018_000000022705_class_swap.jpg`
  - `bbox_drift` — box 'refrigerator' lệch khỏi mask (IoU=0.60, cov=0.69, lệch tâm=0.20) — ảnh: `019_000000022705_bbox_drift.jpg`
