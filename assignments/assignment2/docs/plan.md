> Hoàn tất implementation, tests, reference study, PDF 8 trang và standalone ZIP validation ngày 16/10/2026. Chi tiết source hash, sanitizer rechecks, dữ liệu và giới hạn ở [verification.md](verification.md). Còn yêu cầu đo các máy cá nhân và đối chiếu định danh/LMS do người nộp thực hiện.

# Kế hoạch thực hiện Ass2

1. Đọc đề, slide A* và Ch06/Ch05; định nghĩa rõ dynamic/uncertain h, Pareto objective và oracle.
2. Xây graph/parser, integer cost arithmetic, Dijkstra reference, directed landmark preprocessing.
3. Cài coarse/fine sorted set, priority adaptation, tests linearizability và safe reclamation.
4. Cài sequential heap A*, parallel coarse/fine priority lists; reopen labels, pending accounting, exception cancellation.
5. Kiểm exhaustive small graphs, path replay, real-road reference, all combinations, stress và sanitizers; kiểm hồi quy Ass1.
6. Khóa benchmark matrix, đo repeats trên platform hiện có, kiểm quality trước thống kê; ghi hạn chế phần cứng.
7. Viết README/design/testing/verification/report, render PDF, đóng gói và build từ ZIP mới.
8. Publish code/tài liệu tự viết lên GitHub; loại slide, đề, notebook gốc và generated outputs; đối chiếu remote hashes.

Đây là kế hoạch thực thi, trạng thái cuối xem README và verification.md. Thí nghiệm trên các máy cá nhân thực có và nộp LMS cần người nộp thực hiện khi có quyền truy cập.
