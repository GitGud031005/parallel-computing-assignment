# Reproducibility tools

`collect_environment.py` thu metadata và đối chiếu C++/CMake digest. `verify.py` build/test nhiều modes, lưu logs và checks; --stress chạy thêm ba C++ suites. `run_benchmarks.py` chạy matrix tuần tự, seeded order, warmups/reps, timeout và raw CSV. `summarize.py` kiểm manifest/checksum rồi tính median/IQR/throughput/speedup. `plot_results.py` xuất biểu đồ. `create_report.py` tạo PDF/Markdown từ dữ liệu đã kiểm. `package_submission.py` tạo ZIP theo allowlist kèm SHA-256 manifest.

Các script dùng --help; lệnh toàn pipeline ở [README Ass1](../README.md). Requirements chỉ cần cho plotting/PDF. PDF cần font Unicode DejaVu hoặc Arial; --font-dir hỗ trợ thư mục font ngoài. Raw samples bất biến; output run phải chưa tồn tại. Mọi failed/timeout row được giữ, không loại outlier theo thứ hạng algorithm.
