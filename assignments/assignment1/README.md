# Assignment 1: Shared-memory Synchronization

Nguồn: `Assignment1_v1_16092026.pdf`, ngày 16/09/2026, 4 trang. Đã đối chiếu cả các đoạn code là ảnh trên trang 1-2.

Ba phần bắt buộc: **mutex locks**, **Sense-Reversing Barrier**, **concurrent counters**. Phần distributed dùng MPI-3 One-Sided Communications là tùy chọn.

| Tài liệu | Mục đích |
| --- | --- |
| [Yêu cầu](docs/requirements.md) | Ranh giới yêu cầu gốc và đề xuất triển khai |
| [Kế hoạch](docs/plan.md) | Thứ tự công việc, sản phẩm, tiêu chí hoàn thành, lịch |
| [Thiết kế](docs/design.md) | API, memory orders, node lifetime, baseline |
| [Kiểm thử](docs/testing.md) | Mutual exclusion, visibility, barrier reuse, counter correctness |
| [Benchmark](docs/benchmarking.md) | Workload, thời gian, ma trận đo, CSV, biểu đồ |
| [Dàn ý báo cáo](report/outline.md) | Các phần cần viết và bằng chứng cần đưa vào |

Các thư mục code hiện có README mô tả file sẽ tạo. Mọi tên executable, CLI và script trong tài liệu đều là **giao diện dự kiến**, chưa phải lệnh đã chạy được, trừ hai lệnh cấu hình/build scaffold ở README gốc.

## Tiến độ

- [x] Đọc và ghi chú slide Ch00-Ch07 (gồm Ch02a, Ch02b).
- [x] Đọc toàn bộ Assignment 1; tách bắt buộc và tùy chọn.
- [x] Lập kế hoạch, thiết kế và chiến lược kiểm thử/đo đạc.
- [x] Tạo khung thư mục và cấu hình CMake ban đầu.
- [ ] M1: workload, harness và baseline.
- [ ] M2: TAS/TTAS/MCS và correctness.
- [ ] M3: barrier và correctness.
- [ ] M4: counters và correctness.
- [ ] M5: benchmark trên các máy thực tế.
- [ ] M6: báo cáo PDF, tái lập và ZIP nộp bài.

Tiến độ chi tiết quản lý tại [plan.md](docs/plan.md); cập nhật cùng commit triển khai.

## Kiểm tra khung ban đầu

Ngày 15/10/2026: JSON parse hợp lệ, các Markdown links nội bộ trỏ tới file có thật; page counts/manifest được kiểm tra từ tài liệu nguồn. Một probe C++20 độc lập dùng `std::thread`, atomic và `std::barrier` đã compile/chạy thành công bằng g++ trong môi trường hỗ trợ soạn repo. Môi trường này chưa có CMake, nên chưa thực thi configure/build bằng CMake. Đây không phải kết quả correctness hay performance của Assignment 1; M1 vẫn cần kiểm tra trên máy thực tế sẽ dùng.
