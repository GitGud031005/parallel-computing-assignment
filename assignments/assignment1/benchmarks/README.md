# Benchmark executables

`bench_locks`, `bench_barriers`, `bench_counters` dùng --help để xem flags. JSON stdout (hoặc --output FILE) gồm tham số thực tế, program/worker times, checksum/final value và fingerprint. Runner chuyển từng sample thành raw CSV cùng run metadata.

Lock modes: per_thread (I vòng mỗi thread) hoặc fixed_total (K chia thương/số dư). Counter dùng fixed_total. Barrier có E episode toàn cục, mỗi worker E lần arrive_and_wait; không useful work trong loop.

Protocol đo chi tiết ở mục 5 của báo cáo. Log/CSV/cấp phát không nằm trong hot loops; standard baselines dùng cùng harness.
