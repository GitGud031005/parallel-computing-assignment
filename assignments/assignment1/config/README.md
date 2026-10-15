# Cấu hình thí nghiệm

[benchmark_matrix.json](benchmark_matrix.json) mô tả core/sensitivity/extensions; [smoke_matrix.json](smoke_matrix.json) chỉ dùng kiểm wiring khi runner đã có. Cả hai hiện là **đặc tả**, chưa có runner thực thi.

Chuỗi `physical_cores`, `logical_cpus`, `2*logical_cpus` là token cần được collector/runner resolve từ máy thật; không đưa nguyên chuỗi này cho executable C++.

Các initial workload trong phần pilot cần hiệu chỉnh trước phép đo chính. Lưu các số cuối vào manifest của run, giữ nguyên giữa algorithms trong cùng comparison và giữa P ở fixed-total. Đọc [benchmarking.md](../docs/benchmarking.md) trước khi thay số.
