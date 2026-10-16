# Source files

`workload.cpp`: naive is_prime thử divisor từ 2 tới N-1, xử lý N<2. `environment.cpp`: executable pc_environment báo compiler-mode fingerprint, standard library và atomic lock-free capabilities.

Workload tắt IPO/LTO và gọi từ translation unit khác; các call sites optimized được lưu trong results/validation. Entry points của ba phép đo ở ../benchmarks/.
