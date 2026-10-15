# Đối chiếu yêu cầu Assignment 1

Nguồn duy nhất cho yêu cầu môn học trong tài liệu này: `Assignment1_v1_16092026.pdf`. Số trang là số trang PDF tính từ 1. Các lựa chọn kỹ thuật bên dưới là đề xuất của repo, không phải yêu cầu thêm từ giảng viên.

## 1. Các yêu cầu gốc

| ID | Trang | Yêu cầu | Sản phẩm dự kiến / bằng chứng |
| --- | --- | --- | --- |
| L1 | 1 | Cài TAS, TTAS và MCS bằng C++ cho chương trình nhiều luồng | Header/implementation cho đủ 3 locks |
| L2 | 1 | Đề xuất cách kiểm tra tính đúng | Test mutual exclusion, payload visibility, tiến triển và MCS handoff; lập luận memory order |
| L3 | 1-2 | Thử các lock trên workload `is_prime(N)` với tham số điều chỉnh | `bench_locks`: `threads`, `iterations`, `outside_work`, `N` |
| L4 | 2 | Nghiên cứu performance/scalability; metric thời gian toàn chương trình | CSV theo số thread và mức contention, biểu đồ, phân tích |
| L5 | 2 | So sánh với lock hiện có | Baseline chính: `std::mutex` |
| B1 | 2 | Cài Sense-Reversing Barrier bằng C++ | Barrier reusable, số participant cố định |
| B2 | 2 | Đề xuất cách kiểm tra tính đúng | No early release, visibility, nhiều episode, nhiều instance |
| B3 | 3 | Đo số barrier episode hoàn thành trên đơn vị thời gian, không có useful work giữa barriers | `episodes_per_second = episodes / elapsed_seconds` |
| B4 | 3 | So sánh với barrier hiện có | Baseline chính: C++20 `std::barrier` |
| C1 | 3 | Cài concurrent counters với mutex locks, CAS, FAA | Counter dùng từng lock đã cài, `std::mutex`, CAS loop, `fetch_add` |
| C2 | 3 | Đề xuất cách kiểm tra tính đúng | Final count, giá trị trả về duy nhất, nhiều thread, kiểm tra overflow đầu vào |
| C3 | 3 | Nghiên cứu performance/scalability, metric execution time | Cùng tổng số increment cho các biến thể, CSV và phân tích |
| X1 | 2-3 | Đo trên tất cả shared-memory platforms đang sở hữu | Danh sách máy thực có, metadata và kết quả riêng theo platform |
| S1 | 4 | Làm cá nhân | Người nộp hiểu và giải thích được implementation, không chia bài cho nhóm |
| S2 | 4 | Nộp ZIP gồm PDF report và tất cả mã C++ liên quan | ZIP tự đủ để build/run và báo cáo PDF cuối |
| S3 | 4 | Hạn nộp 29/10/2026 trên website môn học | Đối chiếu giờ đóng cổng trên LMS; chốt nội bộ 28/10 |
| O1 | 3 | Distributed versions dùng MPI-3 One-Sided Communications | Tùy chọn; chỉ cân nhắc sau khi hoàn tất S1-S3 và các phần bắt buộc |

Đề nêu exponential backoff là kỹ thuật có thể dùng, không bắt buộc áp dụng cho mọi thuật toán. Đề không quy định số trang báo cáo, chuẩn C++, số lần lặp phép đo, số biểu đồ, tên file ZIP hay định dạng CLI.

## 2. Workload gốc cần giữ

Với mỗi thread, mỗi vòng lặp thực hiện:

1. Acquire lock.
2. Gọi `is_prime(N)` một lần trong critical section.
3. Release lock.
4. Gọi `is_prime(N)` thêm `OUTSIDE_WORK` lần ngoài critical section.

Mã mẫu `is_prime()` thử mọi ước số từ `2` đến `N-1`, dừng khi tìm thấy ước. Bản triển khai đo chính phải giữ cách thử chia đơn giản này cho tất cả locks; không đổi sang thuật toán căn bậc hai cho một biến thể riêng.

| `OUTSIDE_WORK` | Tỷ lệ số lần gọi nằm trong CS |
| --- | --- |
| 0 | 1 |
| 1 | 1/2 |
| 2 | 1/3 |
| k | 1/(k+1) |

Đây là tỷ lệ **số lần gọi công việc**, không phải cam kết tỷ lệ thời gian đo: còn có chi phí lock, spin, lịch CPU và bộ nhớ. Đặt `N >= 2`; hàm vẫn nên xử lý đúng 0 và 1 trong test riêng.

Kết quả tính toán phải được sử dụng để compiler không loại bỏ/đưa toàn bộ công việc ra ngoài vùng cần đo. Cách làm cụ thể và phép kiểm tra tối ưu hóa ở [benchmarking.md](benchmarking.md).

## 3. Những quyết định của repo

| Quyết định | Lý do / phương án khi gặp vấn đề |
| --- | --- |
| C++20 + CMake >= 3.20 + `std::thread` | Dùng cùng harness và có baseline `std::barrier`; không cần OpenMP cho bản bắt buộc |
| `std::mutex` và `std::barrier` là baseline chính | Đáp ứng yêu cầu so sánh với implementation có sẵn mà tránh quá nhiều toolchain |
| CAS/FAA dùng `uint64_t` | Dễ kiểm soát tổng số phép tăng; kiểm tra input không vượt miền giá trị |
| Hoàn thành bản `seq_cst` trước, rồi acquire/release | Phát triển theo từng bước có chứng cứ correctness |
| TTAS-backoff và CAS-backoff là thí nghiệm bổ sung ưu tiên | Đánh giá tác động backoff với chi phí triển khai vừa phải |
| Một platform cũng phải có metadata đầy đủ | Không giả định có laptop thứ hai hay máy ARM; nếu có thì chạy cùng protocol |
| Giữ raw CSV và metadata gắn commit | Truy ngược mọi bảng/hình tới dữ liệu và mã đã chạy |

## 4. Điểm cần xác nhận khi bắt đầu M1

- CPU, số core vật lý/logical CPU, RAM, OS thực tế và compiler của từng máy sẽ đo.
- Nếu Windows: chọn WSL2 hay native, ghi chính xác môi trường; hai môi trường trên cùng máy không được gọi là hai phần cứng độc lập.
- Giờ hạn nộp và phiên bản đề/thông báo mới nhất trên LMS.
- Họ tên, MSSV và tên ZIP theo quy định lớp nếu có.
- Công cụ xuất PDF báo cáo: ưu tiên công cụ người làm đã dùng được; chọn và kiểm tra sớm trong M1.

Các điểm này chưa chặn việc đọc tài liệu và tổ chức repo, nhưng phải được chốt trước khi chạy phép đo chính hoặc nộp bài.
