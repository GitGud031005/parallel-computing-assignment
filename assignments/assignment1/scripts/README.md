# Scripts dự kiến

Chưa có script chạy được. Tạo theo thứ tự M1 rồi M5-M6, ưu tiên Python để dùng được cả Linux/WSL và Windows khi toolchain tương thích.

| Script sẽ tạo | Trách nhiệm |
| --- | --- |
| `collect_environment.py` | Platform ID, CPU/core topology, OS/compiler/stdlib/atomic metadata |
| `run_benchmarks.py` | Resolve matrix, pilot manifest, seeded order, warmup/reps, timeout và raw CSV |
| `summarize.py` | Kiểm schema/counts; median, Q1/Q3, metrics dẫn xuất từ raw data |
| `plot_results.py` | Biểu đồ có đơn vị/platform/workload, sinh từ summary |
| `package_submission.py` | Kiểm PDF/source tồn tại, tạo ZIP từ allowlist, không gói build/cache |

Khi implementation xong mới ghi lệnh thật vào README gốc. Ghi dependency plotting và version khi chọn thư viện; dữ liệu gốc là bất biến, không sửa bằng tay để làm đẹp plot.
