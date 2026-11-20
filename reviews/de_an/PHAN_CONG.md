# Phân công xem ảnh — ĐỀ ẨN

32 ứng viên trên 27 ảnh. Khung đỏ = DET, khung + vùng tô xanh = PAN. Ảnh gốc: delivery/images/<tên>.jpg

## Trường (@nnt7923) — 4 ảnh → reviews/de_an/nnt7923.csv
- **img_0004**
  - `class_swap` — det ghi 'motorcycle' nhưng pan ghi 'person' (IoU=0.53, cov=0.64) — `001_img_0004_class_swap.jpg`
  - `class_swap` — det ghi 'person' nhưng pan ghi 'motorcycle' (IoU=0.53, cov=0.85) — `002_img_0004_class_swap.jpg`
- **img_0061**
  - `class_swap` — det ghi 'cake' nhưng pan ghi 'donut' (IoU=0.99, cov=1.00) — `010_img_0061_class_swap.jpg`
- **img_0120**
  - `class_swap` — det ghi 'backpack' nhưng pan ghi 'handbag' (IoU=0.92, cov=1.00) — `018_img_0120_class_swap.jpg`
- **img_0178**
  - `bbox_drift` — box 'car' lệch khỏi mask (IoU=0.61, cov=0.84, lệch tâm=0.18) — `026_img_0178_bbox_drift.jpg`

## Khải (@LeVinhKhai) — 4 ảnh → reviews/de_an/LeVinhKhai.csv
- **img_0006**
  - `class_swap` — det ghi 'bus' nhưng pan ghi 'truck' (IoU=0.90, cov=0.99) — `003_img_0006_class_swap.jpg`
- **img_0062**
  - `class_swap` — det ghi 'truck' nhưng pan ghi 'car' (IoU=0.95, cov=0.98) — `011_img_0062_class_swap.jpg`
- **img_0129**
  - `class_swap` — det ghi 'bowl' nhưng pan ghi 'dining table' (IoU=0.93, cov=0.81) — `019_img_0129_class_swap.jpg`
  - `class_swap` — det ghi 'dining table' nhưng pan ghi 'bowl' (IoU=0.91, cov=1.00) — `020_img_0129_class_swap.jpg`
- **img_0188**
  - `class_swap` — det ghi 'dining table' nhưng pan ghi 'bowl' (IoU=0.75, cov=1.00) — `027_img_0188_class_swap.jpg`

## Phú (@nguyendinhphu2004) — 4 ảnh → reviews/de_an/nguyendinhphu2004.csv
- **img_0028**
  - `class_swap` — det ghi 'bicycle' nhưng pan ghi 'motorcycle' (IoU=1.00, cov=1.00) — `004_img_0028_class_swap.jpg`
- **img_0079**
  - `missing_box` — segment 'cat' lớn (area=38450px) nhưng thiếu box (max_cov=0.16) — `012_img_0079_missing_box.jpg`
- **img_0145**
  - `class_swap` — det ghi 'couch' nhưng pan ghi 'chair' (IoU=0.97, cov=1.00) — `021_img_0145_class_swap.jpg`
- **img_0224**
  - `class_swap` — det ghi 'bowl' nhưng pan ghi 'sandwich' (IoU=0.58, cov=0.87) — `028_img_0224_class_swap.jpg`

## Hưng (@hungcui) — 4 ảnh → reviews/de_an/hungcui.csv
- **img_0036**
  - `class_swap` — det ghi 'bed' nhưng pan ghi 'couch' (IoU=0.93, cov=1.00) — `005_img_0036_class_swap.jpg`
- **img_0082**
  - `class_swap` — det ghi 'couch' nhưng pan ghi 'person' (IoU=0.63, cov=0.87) — `013_img_0082_class_swap.jpg`
  - `class_swap` — det ghi 'person' nhưng pan ghi 'couch' (IoU=0.63, cov=0.66) — `014_img_0082_class_swap.jpg`
- **img_0146**
  - `class_swap` — det ghi 'truck' nhưng pan ghi 'car' (IoU=0.97, cov=0.99) — `022_img_0146_class_swap.jpg`
- **img_0226**
  - `class_swap` — det ghi 'backpack' nhưng pan ghi 'suitcase' (IoU=0.92, cov=0.99) — `029_img_0226_class_swap.jpg`

## Chung (@qchung2124) — 4 ảnh → reviews/de_an/qchung2124.csv
- **img_0045**
  - `class_swap` — det ghi 'handbag' nhưng pan ghi 'backpack' (IoU=0.88, cov=1.00) — `006_img_0045_class_swap.jpg`
- **img_0086**
  - `class_swap` — det ghi 'chair' nhưng pan ghi 'dining table' (IoU=0.90, cov=1.00) — `015_img_0086_class_swap.jpg`
- **img_0166**
  - `class_swap` — det ghi 'dining table' nhưng pan ghi 'pizza' (IoU=0.68, cov=1.00) — `023_img_0166_class_swap.jpg`
- **img_0238**
  - `class_swap` — det ghi 'bench' nhưng pan ghi 'chair' (IoU=0.97, cov=1.00) — `030_img_0238_class_swap.jpg`
  - `class_swap` — det ghi 'couch' nhưng pan ghi 'chair' (IoU=0.69, cov=0.99) — `031_img_0238_class_swap.jpg`

## Long (@Long16082004) — 4 ảnh → reviews/de_an/Long16082004.csv
- **img_0054**
  - `class_swap` — det ghi 'hot dog' nhưng pan ghi 'sandwich' (IoU=0.73, cov=0.91) — `007_img_0054_class_swap.jpg`
  - `class_swap` — det ghi 'sandwich' nhưng pan ghi 'hot dog' (IoU=0.73, cov=0.93) — `008_img_0054_class_swap.jpg`
- **img_0113**
  - `class_swap` — det ghi 'person' nhưng pan ghi 'motorcycle' (IoU=0.55, cov=0.88) — `016_img_0113_class_swap.jpg`
- **img_0169**
  - `class_swap` — det ghi 'bus' nhưng pan ghi 'truck' (IoU=0.82, cov=1.00) — `024_img_0169_class_swap.jpg`
- **img_0245**
  - `missing_box` — segment 'toilet' lớn (area=30816px) nhưng thiếu box (max_cov=0.00) — `032_img_0245_missing_box.jpg`

## Hiếu (@kudo2382k4) — 3 ảnh → reviews/de_an/kudo2382k4.csv
- **img_0057**
  - `class_swap` — det ghi 'chair' nhưng pan ghi 'person' (IoU=0.61, cov=0.93) — `009_img_0057_class_swap.jpg`
- **img_0115**
  - `class_swap` — det ghi 'cup' nhưng pan ghi 'bowl' (IoU=0.97, cov=1.00) — `017_img_0115_class_swap.jpg`
- **img_0171**
  - `instance_merge` — 1 segment 'backpack' phủ 2 box cùng lớp (cov=[0.52, 0.48]) — `025_img_0171_instance_merge.jpg`
