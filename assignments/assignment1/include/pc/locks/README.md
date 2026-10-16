# Mutex locks

`tas_lock.hpp`: TAS; `ttas_lock.hpp`: TTAS và `TtasBackoffLock`; `mcs_lock.hpp`: MCS; `std_mutex_adapter.hpp`: baseline; `scoped_lock.hpp`: RAII guard.

API `acquire(context)` / `release(context)`. MCS context chứa node và phải sống đủ đến hết release; từng lock/acquisition còn tồn tại dùng context riêng. Các `Basic*<...>` có SC mode cho tests; production aliases dùng acquire/release. Hooks được template hóa và production dùng no-op rỗng.

Xem [thiết kế](../../../docs/design.md) và [tests](../../../tests/test_locks.cpp).
