# Results và validation

Toàn bộ số liệu trong báo cáo được đo trên laptop của người nộp: Intel Core i7-13620H (6 P-core có Hyper-Threading + 4 E-core, 10 core vật lý, 16 logical CPUs), 15.7 GiB RAM, Windows 11, MinGW-w64 GCC 13.2, Release `-O3`, cắm sạc, power plan Legion Balance Mode, không pin thread. Ngày đo: 24/10/2026. Source fingerprint của binary đã đo: `38a67327a7a796b185cbda8610e235bfac08c2ab067e2ebacf906cfeffe9a8b2`.

| Đường dẫn | Nội dung |
| --- | --- |
| `raw/run-laptop-02/` | Lượt đo chính: 711 configurations × (2 warmups + 7 measured reps) = 6399 samples, P = 1, 2, 3, 4, 6, 8, 10, 12, 14. Gồm `manifest.json` (matrix và thứ tự chạy), `environment.json` (máy, compiler, fingerprint), `raw.csv` (mỗi sample một dòng) và `completion.json`. |
| `raw/saturation-laptop-01/` | Lượt đo bão hòa P = 12, 14, 15, 16: 28 configurations × (1 warmup + 5 measured reps) = 168 samples, timeout 120 s, không sample nào lỗi. |
| `processed/summary.csv`, `processed/validation.json` | Median, IQR, throughput và speedup của lượt đo chính, cùng kết quả kiểm tra: đủ mọi nhóm, 0 measured sample lỗi. |
| `processed/failed_samples.csv` | Sample lỗi duy nhất: một warmup MCS ở P = 14 (per-thread, W = 4) vượt timeout 60 s. Warmup không tính vào thống kê. |
| `processed/saturation/` | Summary và validation của lượt đo bão hòa. |
| `figures/` | Năm hình dùng trong báo cáo, vẽ từ `processed/summary.csv`. |
| `platforms/laptop-i7-13620H.json` | Bản sao `environment.json` của máy đo. |
| `platforms/checks-laptop-02.json` | Kết quả `verify.py` trên cùng source: Debug và Release đều 6/6 nhóm CTest pass, 3/3 stress suite pass. |

Raw data không sửa tay. Mỗi sample tự kiểm checksum, và `summarize.py` kiểm lại manifest, checksum, duplicate và tính đầy đủ trước khi tính thống kê. Smoke matrix chỉ dùng kiểm tra wiring, không dùng làm số liệu.

Trong repo Git, các file kết quả này bị `.gitignore` bỏ qua; chúng chỉ được đưa vào ZIP nộp bài.
