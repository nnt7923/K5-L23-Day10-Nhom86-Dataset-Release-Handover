# Dùng AI

| # | Ai dùng | Công cụ | Prompt (tóm tắt) | AI sai ở đâu | Nhóm kiểm lại thế nào |
|---|---|---|---|---|---|
| 1 | Đỗ Trung Hiếu (kudo2382k4) | Claude Code | "Đọc GUIDE/RUBRIC, ticket.md, changelog.md, jobs.csv rồi viết script `trace_query` chỉ dùng thư viện chuẩn, chỉ đọc delivery, tên lớp và danh sách cảnh làm tham số" | Bản đầu đọc `classes.txt` như mỗi dòng chỉ có tên lớp, nên báo không tìm thấy `cup`. File thật có dạng `41 cup` (id + tên). | Chạy script trên `runs/r86007` thì thấy lỗi, sửa cách đọc. Chấm bằng `score_findings.py` bản gốc: tier_a, tier_b, notify đều F1 1.0. Chạy thêm trên 2 lô `inject_release.py --opaque` (seed 33, 77) để chắc không phụ thuộc tên ảnh/seed. Tự đối chiếu: J01–J03 là v1.2 trong `jobs.csv`, 7 ảnh đều thuộc J02 → notify A04, Q03. |
| 2 | <<>> | | | | |
