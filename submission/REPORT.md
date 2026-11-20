# Báo cáo nhóm 86

Seed luyện tập **86007**, release v1 `lab250_9fe09dde91ec` (250 ảnh COCO, 10 job J01–J10). Mọi số dưới đây do nhóm tự chạy bằng `validator/validate.py` và `scripts/score_findings.py` (bản gốc). Validator không đọc `_private/`.

## 1. Số liệu luyện tập

**F1 theo seed** (lỗi luật `rule_detectable` / lỗi gán nhãn `cross_check_review` / tổng):

| Seed | Bài nộp | Lỗi luật | Lỗi gán nhãn | Tổng |
|---|---|---:|---:|---:|
| 86007 | `errors.json` cuối (luật + review), 20 lỗi | 1.0 (11/11) | 0.67 (TP 6, FP 3, FN 3) | **0.85** (TP 17, FP 3, FN 3) |
| 86007 | chỉ lỗi luật, 11 lỗi | 1.0 | — (bỏ sót cả 9) | 0.71 |
| 11 (`inject_release.py`) | chỉ lỗi luật | ≈ 1.0 | — | ≈ 0.8 |
| 22 (`inject_release.py`) | chỉ lỗi luật | ≈ 1.0 | — | ≈ 0.7 |
| lô sạch seed 5 (`--no-faults`) | chỉ lỗi luật | 0 lỗi luật báo ra (đúng) | — | — |

Ở seed 11 và 22 nhóm không xem ảnh, nên chỉ đo phần luật. Lỗi luật đạt F1 ≈ 1.0 trên cả 3 seed và báo 0 lỗi trên lô sạch, đạt CP1.

**Ứng viên:**
- Lô sạch (`--no-faults`, 50 ảnh pool calib): **9 ứng viên trên 7 ảnh**, đều là `class_swap`. Đây là lệch tự nhiên của COCO giữa detection và panoptic.
- Seed 86007: **27 ứng viên trên 19 ảnh** (22 `class_swap`, 3 `bbox_drift`, 1 `missing_box`, 1 `instance_merge`). Đã bỏ 2 ảnh dính lỗi luật, vì mỗi ảnh mang nhiều nhất một lỗi. Hàng đợi chia cho 7 người, khoảng 3 ảnh mỗi người (`reviews/r86007/PHAN_CONG.md`).
- Kết quả review: 22 dòng trong `review_log.csv`, gồm **9 confirmed, 13 rejected** (12 `class_swap` và 1 `bbox_drift` bị loại vì là lệch tự nhiên).

**Ngưỡng đã chọn và cách chọn** (chỉ dựa vào lô sạch và mắt người, không dùng `_private`):
- Ghép box ↔ segment thing bằng IoU, rồi kiểm lại bằng **pixel mask** (tỉ lệ pixel của segment nằm trong box, gọi là `cov`). Bỏ segment `iscrowd`, bỏ box quá nhỏ (dưới 0,5% diện tích ảnh) và segment dưới 300–400 px, vì quá nhỏ để xem bằng mắt.
- `class_swap` / `category_swap`: IoU ≥ 0.50, khác lớp, `cov` ≥ 0.60.
- `bbox_drift`: cùng lớp, 0.35 ≤ IoU ≤ 0.82, lệch tâm ≥ 0.12, và `cov` < 0.85 (một phần segment rơi ra ngoài box).
- `missing_box`: segment thing lớn mà không box nào phủ quá 25% (`max_cov` 0.25).
- `instance_merge`: một segment có ít nhất 20% pixel nằm trong mỗi box của **hai** box cùng lớp, và không box nào ôm quá 88% segment (để loại cặp `duplicate_box`).
- Lý do: với các ngưỡng này lô sạch chỉ còn 9 ứng viên. Hàng đợi seed 86007 (27 ứng viên) 7 người xem hết trong khoảng 30 phút, kịp cho đề ẩn 40 phút. Nới ngưỡng ra (chỉ dùng IoU bbox) thì số ứng viên tăng mạnh mà phần thêm chủ yếu là lệch tự nhiên.

## 2. Vì sao báo hết ứng viên làm F1 giảm?

Ứng viên chỉ là "chỗ hai nguồn nhãn bất đồng", chưa phải lỗi. COCO vốn lệch tự nhiên giữa detection và panoptic (vật bị che, crowd, vật cắt mép, hai lớp giống nhau như fork/spoon). Lô sạch không gài lỗi nào mà vẫn có 9 ứng viên. Báo hết ứng viên thì recall tăng một chút, nhưng mỗi ứng viên tự nhiên thành một FP, nên precision giảm mạnh hơn nhiều.

Nhóm đo trên seed 86007:

| Cách nộp | Số lỗi nộp | Precision | Recall | F1 tổng | F1 lỗi gán nhãn |
|---|---:|---:|---:|---:|---:|
| Chỉ lỗi luật | 11 | 1.00 | 0.55 | 0.71 | — |
| Luật + **báo hết** 21 ứng viên (không xem ảnh) | 32 | 0.53 | 0.85 | **0.65** | 0.40 (FP 15) |
| Luật + chỉ ứng viên **confirmed** sau khi xem ảnh | 20 | 0.85 | 0.85 | **0.85** | 0.67 (FP 3) |

Báo hết ứng viên còn **thấp hơn cả chỉ nộp lỗi luật** (0.65 so với 0.71). Riêng `class_swap` có 14 FP khi báo hết. Xem ảnh để loại 13 ca lệch tự nhiên giữ nguyên recall 0.85 nhưng kéo precision từ 0.53 lên 0.85.

Thêm nữa, rubric bỏ mọi lỗi gán nhãn không có dòng `confirmed`, nên báo hết mà không xem ảnh cũng không được tính.

**Chỗ nhóm còn sai:** 3 FP và 3 FN ở lỗi gán nhãn. Trong đó có ca nhầm giữa `class_swap` và `category_swap` (xác định sai nguồn nào ghi sai), và một số `bbox_drift` / `instance_merge` không lọt vào hàng đợi. Ở đề ẩn, nhóm sẽ luôn tự hỏi "vật thật trong ảnh là gì" trước khi chọn loại, và gọi người thứ hai xem chéo ca khó.

## 3. Quyết định và lineage

- **QC v1: 20/250 = 8,0%** ảnh lỗi (mỗi ảnh tối đa một lỗi; `scene_leak` tính là một ảnh), lớn hơn ngưỡng 2% của Day 7, nên **HOLD**. Ngưỡng tính theo tỉ lệ ảnh lỗi vì điều team AI quan tâm là bao nhiêu phần dữ liệu train bị bẩn, không phải tổng số nhãn sai.
- Lineage (`submission/lineage.jsonl`) có đủ 4 sự kiện: `inject` → `train R-021` trên v1 → `decision HOLD` cho `lab250_9fe09dde91ec` → `release lab250_9fe09dde91ec_v2` với `parent lab250_9fe09dde91ec`. Lệnh `lineage.py impact` cho ra `R-021: affected=True action=review_or_retrain`.
- **Vì sao R-021 phải xem lại hoặc train lại:** model R-021 đã học từ v1, gồm cả 8% ảnh lỗi (box đổi lớp, box lệch, box lặp, thiếu box). Sửa dataset thành v2 không làm thay đổi trọng số đã học. Model vẫn mang theo các lỗi đó, ví dụ bỏ sót `cup` bị che như ticket báo. Vì vậy phải đánh giá lại R-021 trên dữ liệu sạch và train lại trên v2 nếu ảnh hưởng đáng kể.
- **v2:** 237 ảnh, 1646 nhãn.
  - 13 ảnh lỗi nhãn detection tách ra `rework_queue.csv`, giao lại đúng annotator/reviewer theo `jobs.csv`.
  - Sửa ngay trong v2: `wrong_hash` (`000000005586`; đã mở ảnh, ảnh nguyên vẹn, chỉ manifest sai), `scene_leak` (`scene_326` đưa cả cảnh về một split), `guideline_mismatch` (`000000025139`, lấy guideline theo job).
  - 4 ảnh chỉ lỗi panoptic ở lại v2 và được ghi chú trong README để báo team panoptic.

## 4. Hash chứng minh gì, không chứng minh gì?

**Chứng minh:** file hiện tại **giống từng byte** với file lúc lập manifest. Không ai sửa, không bị hỏng hay cắt cụt khi chép. Vì vậy validator phải tự tính lại sha256 trên bytes (`open(..., 'rb')`), không chỉ kiểm chuỗi có đủ 64 ký tự hex. Ví dụ, `wrong_hash` của `000000005586` chỉ phát hiện được nhờ tính lại. File `.sha256` của gói v2 chứng minh gói nhóm nộp đúng là gói đã đóng, và `check_handover` đóng gói lại ra cùng mã.

**Không chứng minh:**
- Nhãn đúng: một box ghi sai lớp vẫn có hash "đúng" nếu manifest được lập sau khi gán sai.
- Ảnh đúng nội dung, đúng guideline hay đúng split.
- Ai đã tạo file, hay file đã qua review.
- Khi hash lệch, hash cũng không cho biết file hỏng hay manifest ghi sai. Phải mở ảnh ra kiểm (như nhóm đã làm với `000000005586`).

Đó cũng là lý do không ghi đè v1. v1 giữ nguyên để hash và lineage của R-021 vẫn trỏ đúng dữ liệu đã train; mọi sửa đổi nằm trong v2 có parent là v1.

## 5. Truy vết

Ticket team AI: model bỏ sót `cup` bị che, thấy rõ ở `scene_553` và `scene_863`. Changelog: từ **v1.3**, `cup` bị che trên 50% hoặc cắt mép **vẫn phải gán box**; v1.2 cho phép bỏ qua.

**Tiêu chí** (script `tools/trace_query.py`, chỉ đọc delivery; tên lớp và cảnh truyền bằng `--cls`, `--scenes` hoặc tự đọc từ ticket/changelog):
- Job dùng guideline cũ: guideline ghi **ở job trong `jobs.csv`** nhỏ hơn v1.3, tức J01, J02, J03.
- Ảnh "có lớp bị đổi quy tắc": `labels/<ảnh>.txt` có ít nhất một box `cup` (class 41).
- `tier_a`: ảnh đủ hai điều kiện trên và thuộc `scene_553` / `scene_863`, được **4 ảnh**.
- `tier_b`: ảnh đủ hai điều kiện ở các cảnh khác, chưa ai báo, được **3 ảnh**. Đây là phần team AI chưa thấy nhưng cùng rủi ro.
- `notify`: annotator và reviewer của các job chứa ảnh tầng a và b. Cả 7 ảnh đều thuộc J02, nên báo **A04, Q03**.
- Kết quả trên seed 86007: F1 = 1.0 cho cả `tier_a`, `tier_b`, `notify`. Nhóm chạy thử thêm trên 2 lô `--opaque` (seed 33, 77), cũng đạt 1.0.

**Vì sao lấy guideline theo job:** người gán làm theo guideline của job được giao. `guideline_version` ghi ở từng ảnh có thể sai, và đó chính là lỗi `guideline_mismatch` (ví dụ `000000025139` trong lô này). Nếu lọc theo cột ở ảnh thì sẽ bỏ sót hoặc báo nhầm ảnh.

## 6. Bug hoặc điểm chưa rõ trong lab

- `check_handover.py` dừng ngay ở H4 khi chưa có thư mục v2, nên không kiểm được H16 (trace) và H17 (security) sớm. Nhóm phải tự kiểm `trace.json` / `security.md` theo đúng điều kiện trong script trước khi có v2.
- Bộ chấm chỉ in F1 làm tròn khi không có `--truth-dir`, nên seed 11 và 22 ở bảng mục 1 ghi "≈".
