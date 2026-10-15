# Kết quả thí nghiệm

**Chưa có số liệu.** Các thư mục con được tạo sẵn để lưu dữ liệu thật theo [protocol](../docs/benchmarking.md):

| Thư mục | Nội dung sẽ lưu |
| --- | --- |
| `platforms/` | `<platform_id>.json`: cấu hình phần cứng/phần mềm, atomic capabilities |
| `raw/` | `<platform_id>/<run_id>/`: manifest, raw CSV, log, lỗi/timeout |
| `processed/` | Bảng summary từ raw: median/Q1/Q3, throughput, speedup hợp lệ |
| `figures/` | Hình cho báo cáo, có platform/config/run ID trong caption hoặc metadata |

Giữ raw bất biến. Không điền kết quả suy đoán vào CSV; không dùng số minh họa trong report như dữ liệu đo thật. Không lấy tốc độ của container hỗ trợ soạn tài liệu làm đại diện laptop của người làm.
