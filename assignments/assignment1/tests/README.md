# Correctness tests

Đặc tả chi tiết ở [testing.md](../docs/testing.md). Chưa có test code hoặc CTest registration.

| File sẽ tạo | Phạm vi |
| --- | --- |
| `test_workload.cpp` | Naive prime và input edge cases |
| `test_locks.cpp` | Mutual exclusion, visibility, stress, MCS enqueue gap |
| `test_barriers.cpp` | Reusable phases, no early release, visibility, multiple instances |
| `test_counters.cpp` | Final count, old-value uniqueness, nhỏ/boundary cases |

Khi có tests thật: đăng ký CTest cùng TIMEOUT, trả exit code khác 0 khi fail, không phụ thuộc output nhìn bằng mắt. CTest không có tests ở scaffold hiện tại không được tính là correctness pass.
