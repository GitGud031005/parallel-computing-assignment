# Correctness và analysis tests

6 CTest groups: workload, locks, barriers, counters, cli_validation, analysis_validation. C++ test checks vẫn hoạt động ở Release. Các suite locks/barriers/counters nhận --stress để tăng 10 lần iterations.

Các interleaving khó dùng compile-time hooks: MCS successor dừng giữa tail exchange và next publication; barrier quan sát một arrival thật trước khi giữ last participant. Payload test tách khỏi occupancy instrumentation. Cùng worker có context riêng ở 2 instances; barrier test dùng lịch A-A-B và barrier thứ hai trước vòng ghi kế tiếp.

Kết quả và giới hạn: mục 4 của báo cáo. Logs/checks.json sinh cục bộ bằng `scripts/verify.py`. Bảng tính chất cần kiểm và oracle tương ứng cũng ở mục 4.
