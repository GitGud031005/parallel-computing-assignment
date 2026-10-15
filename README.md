# Parallel Computing Assignments

Repo môn Parallel Computing (CO5133). Ghi chú và kế hoạch viết bằng tiếng Việt; mã nguồn dự kiến dùng C++20.

**Trạng thái:** đã đọc tài liệu, lập kế hoạch và tạo khung thư mục cho Assignment 1. Chưa triển khai thuật toán, test hay benchmark; chưa có số liệu thực nghiệm.

## Bắt đầu từ đây

| Nội dung | Đường dẫn |
| --- | --- |
| Kế hoạch chi tiết Assignment 1, lịch và checklist | [plan.md](assignments/assignment1/docs/plan.md) |
| Đối chiếu từng yêu cầu của đề | [requirements.md](assignments/assignment1/docs/requirements.md) |
| Thiết kế API, atomic và memory ordering | [design.md](assignments/assignment1/docs/design.md) |
| Chiến lược kiểm thử correctness | [testing.md](assignments/assignment1/docs/testing.md) |
| Phương pháp benchmark và phân tích | [benchmarking.md](assignments/assignment1/docs/benchmarking.md) |
| Ghi chú cả 9 bộ slide và trang cần đọc lại | [slide-notes.md](docs/slide-notes.md) |
| Mục lục tài liệu gốc | [source-index.md](references/source-index.md) |

## Tổ chức repo

| Thư mục | Vai trò |
| --- | --- |
| `docs/` | Kiến thức dùng chung từ slide |
| `references/` | Mục lục, thông tin nhận diện tài liệu nguồn |
| `assignments/assignment1/docs/` | Yêu cầu, kế hoạch, thiết kế, kiểm thử, benchmark |
| `assignments/assignment1/include/pc/` | Header cho locks, barriers, counters và tiện ích chung |
| `assignments/assignment1/src/` | Phần triển khai `.cpp`, đặc biệt workload `is_prime()` |
| `assignments/assignment1/tests/` | Correctness và stress tests |
| `assignments/assignment1/benchmarks/` | Ba chương trình đo locks, barriers, counters |
| `assignments/assignment1/config/` | Ma trận thí nghiệm dự kiến |
| `assignments/assignment1/scripts/` | Thu cấu hình máy, chạy phép đo, vẽ hình, đóng gói |
| `assignments/assignment1/results/` | Dữ liệu gốc, metadata máy, bảng tổng hợp, biểu đồ |
| `assignments/assignment1/report/` | Bản thảo báo cáo và PDF cuối cùng |
| `assignments/assignment2/` | Chỗ dành sẵn; chưa phân tích Assignment 2 |

## Công việc tiếp theo

Thực hiện **M1 trong [kế hoạch](assignments/assignment1/docs/plan.md)**: xác nhận máy/OS/compiler sẽ dùng, hoàn thiện workload và harness, dựng baseline `std::mutex`/`std::barrier`. Sau đó triển khai TAS → TTAS → MCS → Sense-Reversing Barrier → counters, với correctness tests đi cùng từng phần.

## Build scaffold

Cần compiler hỗ trợ C++20 và thư viện có `std::barrier`, CMake >= 3.20, cùng thư viện threads. Linux hoặc WSL2 là môi trường tham chiếu đề xuất; vẫn ghi riêng OS/kernel thực tế của từng máy đo.

```bash
cmake -S . -B build/debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build/debug
```

Hiện CMake chỉ cấu hình project, kiểm tra `std::barrier` và cung cấp target tùy chọn biên dịch. **Chưa có executable hay CTest test nào.** Lệnh build thành công ở giai đoạn này không chứng minh các thuật toán đã được cài đặt hoặc kiểm thử.

## Mốc nộp bài

Theo Assignment 1 bản 16/09/2026: làm cá nhân, nộp một ZIP chứa báo cáo PDF và toàn bộ mã C++ liên quan lên website môn học vào **29/10/2026**. Giờ đóng cổng và các thay đổi mới hơn cần đối chiếu trên LMS. Mục tiêu nội bộ: đóng gói xong **28/10/2026**, giờ Việt Nam.
