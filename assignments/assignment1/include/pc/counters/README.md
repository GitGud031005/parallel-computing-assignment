# Concurrent counters

`mutex_counter.hpp`: template cho TAS/TTAS/MCS/std mutex. `cas_counter.hpp`: CAS relaxed, SC reference và backoff alias. `faa_counter.hpp`: FAA relaxed/SC.

`increment(context)` trả old value; `value(context)` đọc theo cơ chế bảo vệ tương ứng. Khởi tạo tùy chọn bằng uint64_t; caller đảm bảo workload không wraparound. CLI kiểm tra overflow khi tính tổng.

Lập luận happens-before ở mục 3 của báo cáo; xem [tests](../../../tests/test_counters.cpp).
