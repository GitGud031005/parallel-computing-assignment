# Data

`tradeoff.road` là fixture tổng hợp tự tạo, có ba Pareto vectors (2,18), (12,12), (18,2); tọa độ chỉ phục vụ GPS test. Không gọi đây là dữ liệu đường thật.

Road extracts thật được tải/chuyển đổi bằng scripts vào `results-local/`, không publish GitHub. Mẫu đã đo là vùng nhỏ TP.HCM, 3106 nodes/5350 directed edges; fixture West Oakland riêng dùng smoke. Dữ liệu OSM: © OpenStreetMap contributors, [ODbL-1.0](https://opendatacommons.org/licenses/odbl/1-0/), [copyright](https://www.openstreetmap.org/copyright).

PCROAD1 text format:

```text
PCROAD1
N M
osm_id latitude longitude  (N rows)
from_index to_index distance_mm estimated_time_ms  (M rows)
```

Các dòng chú thích trong ví dụ trên không nằm trong file. IDs nội bộ là vị trí dòng node 0..N-1; edge IDs là thứ tự dòng edge 0..M-1. Có directed parallel edges; không âm, không vượt finite domain. Node OSM IDs phải unique; tọa độ finite và trong miền độ lat/lon. Missing/trailing data bị reject.

Converter giữ từng đoạn giữa OSM nodes, làm tròn lên mm/ms, không simplify graph. Ước lượng speed theo road class không phải tốc độ đo hay khuyến nghị giao thông; không turn restrictions/traffic dynamics. Không giả định hai ways cắt nhau trên bản đồ sẽ nối nhau: phải chia sẻ node ID. Metadata lưu model, source/graph SHA, source name, attribution/license; giữ snapshot để tái lập vì OSM thay đổi.
