# Counter headers dự kiến

Chưa có implementation. M4 sẽ tạo:

- `mutex_counter.hpp`: template trên lock/context; thử TAS, TTAS, MCS và standard mutex.
- `cas_counter.hpp`: atomic uint64_t, CAS retry loop, trả old value.
- `faa_counter.hpp`: atomic uint64_t, fetch_add, trả old value.
- `cas_backoff_counter.hpp`: mở rộng sau correctness gate nếu đủ thời gian.

Contract ở [design.md](../../../docs/design.md); test oracle ở [testing.md](../../../docs/testing.md). Không đưa plain shared counter không khóa vào benchmark nhiều thread.
