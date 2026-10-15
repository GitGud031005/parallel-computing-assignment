# Lock headers dự kiến

Chưa có implementation. Tạo các file theo M2; contract và memory orders nằm trong [design.md](../../../docs/design.md).

| File sẽ tạo | Vai trò |
| --- | --- |
| `tas_lock.hpp` | TAS bằng atomic flag |
| `ttas_lock.hpp` | TTAS bằng atomic bool |
| `mcs_lock.hpp` | MCS, node atomic, context và queue handoff |
| `std_mutex_adapter.hpp` | Adapter baseline standard mutex |
| `scoped_lock.hpp` | Scope guard dùng cùng explicit worker context |
| `ttas_backoff_lock.hpp` | Biến thể bổ sung sau correctness gate |

Không tái sử dụng một MCS node cho hai acquisitions đang tồn tại đồng thời. Header implementations có thể tách thêm `.cpp` nếu cần, nhưng hot path của các biến thể phải có chính sách biên dịch nhất quán.
