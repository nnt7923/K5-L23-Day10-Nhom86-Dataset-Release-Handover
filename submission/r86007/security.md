# Bảo mật khi làm việc

> Gắn với lô nhóm 86 vừa bàn giao: release `lab250_9fe09dde91ec` (seed 86007), 250 ảnh COCO, 10 job J01–J10, người gán A01–A05, người kiểm Q01–Q03.

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp

Không chép lô ra USB. Lô này có 250 ảnh, trong đó nhiều ảnh chụp người thật nhìn rõ mặt. Có cả nhãn, `jobs.csv` và mã người gán / người kiểm. Một khi đã chép ra USB thì dữ liệu nằm ngoài hệ thống được kiểm soát: USB có thể bị mất, máy ở nhà không được quản lý, và không còn ghi lại được ai đã mở file nào.

Gửi lô về email cá nhân cũng sai vì cùng lý do đó: dữ liệu lúc này nằm trên server của bên thứ ba và không thu hồi được. Nhờ người khác làm hộ cũng sai: người đó không được giao job, nên log và `truyvet.csv` sẽ ghi sai người làm, khi có lỗi thì không truy được trách nhiệm.

Cách đúng: dừng ở chỗ đang làm, lưu tiến độ trên hệ thống, hôm sau làm tiếp trên máy công ty, hoặc qua kênh được cấp như VPN hay máy công ty mang về. Nếu sợ trễ hạn (ví dụ còn rework của J02) thì báo trưởng nhóm để dời hạn hoặc chia lại việc, không tự tìm cách mang dữ liệu ra ngoài.

## 2. Năm việc: được hay không

1. **Mở job được giao trên máy công ty: được.** Đây là đúng quy trình: đúng người, đúng job, đúng máy, và mọi thao tác đều được ghi lại (ví dụ A04 mở J02 trên máy công ty).
2. **Chụp màn hình gửi người quen: không.** Ảnh chụp màn hình vẫn chứa ảnh gốc, nhãn và có thể có mặt người. Gửi đi là làm lộ dữ liệu ra ngoài, không thu hồi được, kể cả khi chỉ là để "khoe" hay hỏi bài.
3. **Chép lô ra USB: không.** Lý do như mục 1: mất kiểm soát, dễ thất lạc, không còn dấu vết truy cập. Lô có ảnh người thật, nên đây là dữ liệu cá nhân.
4. **Dán nhãn thật lên chatbot: không.** Nội dung dán vào chatbot công cộng bị gửi lên server bên ngoài và có thể được lưu lại hay dùng để train. Khi cần AI hỗ trợ viết code, nhóm chỉ mô tả định dạng file hoặc dùng dữ liệu giả, không dán nhãn, ảnh hay `jobs.csv` thật.
5. **Đưa tài khoản CVAT cho đồng nghiệp: không.** Mỗi tài khoản gắn với một người. Nếu dùng chung thì `jobs.csv` / `truyvet.csv` ghi A0x gán nhãn nhưng thực tế là người khác. Khi đó rework sẽ giao nhầm người, và không ai chịu trách nhiệm cho nhãn sai. Muốn đồng nghiệp làm thì nhờ trưởng nhóm giao job cho tài khoản của người đó.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ

Ví dụ trong lô của nhóm: ảnh `000000004395` là chân dung một thanh niên áo sơ mi trắng thắt cà vạt, khuôn mặt nhìn rõ và chiếm gần nửa khung ảnh. Ngoài ra còn ảnh `000000001296` (cô gái cầm điện thoại, mặt rõ) và `000000016598` (người tóc xanh chụp selfie trước gương). Guideline yêu cầu làm mờ, nhưng các ảnh này chưa được làm mờ.

Việc cần làm: dừng xử lý các ảnh đó, chuyển lô sang **Hold** (không Release, không giao cho team AI), rồi **báo người phụ trách** dữ liệu / bảo mật và trưởng nhóm. Kèm danh sách tên ảnh và mô tả ngắn, sau đó chờ quyết định.

Annotator không tự làm mờ hay xoá ảnh vì 3 lý do:
- Sửa ảnh trong `delivery/` là ghi đè v1. Hash trong manifest sẽ sai và mất khả năng truy vết bản gốc.
- Làm mờ đúng hay sai (bỏ sót mặt, mờ chưa đủ) cần người có thẩm quyền kiểm, và có thể phải làm lại cho cả lô theo một quy trình thống nhất.
- Quyết định xử lý dữ liệu cá nhân (làm mờ, loại ảnh, hay xin lại quyền sử dụng) thuộc người phụ trách, không phải người gán nhãn.

Nếu tự xoá ảnh thì nhãn và lineage còn bị lệch thêm. Nếu cần sửa, việc đó sẽ đi vào một bản mới (v2 có parent v1), không đè lên bản cũ.
