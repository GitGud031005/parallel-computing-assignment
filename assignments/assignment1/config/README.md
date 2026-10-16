# Executable experiment matrices

Schema v2 có `experiments`, mỗi experiment chứa `suite`, `name`, `parameters` với các list giá trị cụ thể; runner lấy Cartesian product. `benchmark_matrix.json` là reference sweep: 395 configurations, 2 warmups và 7 measured reps = 3555 rows. `smoke_matrix.json`: 57 short functional samples, không dùng làm kết luận performance.

Reference threads [1,2,3,4,8] phù hợp giới hạn quota 8 CPU của môi trường đo. Khi chạy máy khác, chỉnh list theo physical/logical CPUs thực có và ghi điều kiện oversubscription. I/K/E cố định giữa algorithms và P trong cùng series; không hiệu chỉnh riêng để làm đẹp kết quả một algorithm.
