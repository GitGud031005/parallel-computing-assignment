# Parallel Computing Assignments

Assignment 1 được triển khai bằng C++20: TAS/TTAS/MCS, Sense-Reversing Barrier, counters mutex/CAS/FAA, standard baselines, TTAS/CAS backoff, correctness tests và pipeline benchmark/report.

**Bắt đầu tại [README Assignment 1](assignments/assignment1/README.md)**: giải thích từng module, API/context, memory ordering, CLI, build/test, đọc JSON, benchmark và đóng gói bài nộp.

```bash
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release
cmake --build build/release -j 4
ctest --test-dir build/release --output-on-failure
```

Cần CMake >=3.20, compiler/standard library hỗ trợ C++20 `std::barrier`; Python >=3.10 để chạy đủ 6 nhóm test/scripts. Linux/WSL2 là môi trường tham chiếu.

| Tài liệu | Nội dung |
| --- | --- |
| [Assignment 1](assignments/assignment1/README.md) | Hướng dẫn code và lệnh thực thi |
| [Requirements](assignments/assignment1/docs/requirements.md) | Đối chiếu từng yêu cầu đề |
| [Verification](assignments/assignment1/docs/verification.md) | Review thuật toán, kiến thức slide, tests và giới hạn |
| [Design](assignments/assignment1/docs/design.md) | State, contracts và happens-before |
| [Testing](assignments/assignment1/docs/testing.md) | Oracles và các lịch chạy khó |
| [Benchmarking](assignments/assignment1/docs/benchmarking.md) | Workload, timers và thống kê |
| [Plan](assignments/assignment1/docs/plan.md) | Kế hoạch và trạng thái |
| [Slide notes](docs/slide-notes.md) | Ghi chú tự viết từ 9 bộ slide |
| [Source index](references/source-index.md) | Danh mục nguồn đã đọc |

GitHub lưu source, tests, scripts, cấu hình và tài liệu tự viết. **Không upload slide/PDF đề gốc.** Build output, logs, raw data, figures, report sinh ra và ZIP nằm ngoài phần code publish; các đường dẫn này đã được ignore. Ghi chú/manifest nguồn là thông tin tham chiếu, không chứa bản sao tài liệu gốc.

Phần shared-memory bắt buộc đã có implementation và pipeline; MPI-3 RMA tùy chọn chưa triển khai. Reference study chạy trong managed Linux, không phải laptop người nộp. Yêu cầu đo trên máy cá nhân thực có, điền định danh và đối chiếu giờ LMS vẫn cần hoàn tất trước nộp. Assignment 2 hiện chỉ dành sẵn thư mục.
