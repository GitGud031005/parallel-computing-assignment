# Benchmark executables dự kiến

Chưa có source/executable; các tên CLI bên dưới là thiết kế cho M1-M4. Protocol bắt buộc đọc trước: [benchmarking.md](../docs/benchmarking.md).

| Target dự kiến | Input chính | Output chính |
| --- | --- | --- |
| `bench_locks` | implementation, threads, mode, iterations/total, N, outside_work | program time, worker time, checksum |
| `bench_barriers` | implementation, threads, episodes | worker time, global episode/s |
| `bench_counters` | implementation, threads, total increments | program time, worker time, final value |

CLI dự kiến dùng `--implementation`, `--threads`, `--mode`, `--iterations-per-thread`, `--total-operations`, `--prime-n`, `--outside-work`, `--episodes`, `--output`. Chỉ expose các flags áp dụng cho từng suite; validation từ chối input mâu thuẫn. Runner scripts sẽ quản lý repetitions/warmups và run metadata.

Build Release riêng; tắt sanitizer/test scheduling hooks; log/cấp phát/sinh ngẫu nhiên ngoài hot loop. Trong benchmark barrier không làm prime hoặc ghi checksum giữa các episode.
