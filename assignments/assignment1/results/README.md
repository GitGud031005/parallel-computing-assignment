# Results và validation

GitHub chỉ giữ README và thư mục trống dành sẵn. Raw data, metadata máy, validation logs, figures và report sinh ra được giữ cục bộ. Tóm tắt kiểm tra ở [verification.md](../docs/verification.md); không có liên kết tới file kết quả chưa upload.

Sau khi chạy `verify.py`, thư mục output chứa logs/exit codes và `checks.json`. Trong lần chạy tham chiếu, ASan đầu thất bại do LeakSanitizer không đọc được `/proc task`; ASan+UBSan chạy lại thành công với detect_leaks=0, không phải chứng nhận leak-free.

`raw/<platform>/<run>/`: manifest/environment/raw.csv/completion. `processed/<run>/`: summary.csv và validation.json của dữ liệu. `figures/<run>/`: hình cho báo cáo. Dữ liệu reference lấy từ managed Linux environment, không đại diện laptop cá nhân của người nộp.

Metadata chứa source/binary fingerprints và revision. Raw data không sửa tay. Smoke chỉ xác minh wiring, không dùng làm evidence performance. Lệnh README dùng `results-local/` và `validation-local/` từ gốc repo. ZIP nộp có thể chứa dữ liệu cần thiết; ZIP cũng không được push GitHub.
