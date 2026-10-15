# Thành phần dùng chung dự kiến

Chưa có implementation. M1 tạo giao diện cho `workload.hpp`, `cli.hpp`, `worker_harness.hpp`, `csv_writer.hpp`; bổ sung `backoff.hpp` khi làm extensions.

- Workload chỉ khai báo ở header; naive `is_prime()` nằm trong `src/workload.cpp` để kiểm soát tối ưu hóa liên module.
- Worker harness hỗ trợ context địa chỉ ổn định, gate độc lập, timer và buffer kết quả riêng theo thread.
- CLI kiểm input và overflow trước khi spawn; CSV ghi ra ngoài timed loops.
- Tiện ích backoff phải log policy/limits; không bật ẩn cho mọi algorithm.
