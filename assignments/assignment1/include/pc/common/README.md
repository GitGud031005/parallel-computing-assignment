# Common utilities

`spin.hpp`: pause hint, memory-order selector, bounded backoff. `worker_harness.hpp`: standard latch start gate độc lập, spawn-to-join timer, worker interval, quotient/remainder partition. `cli.hpp`: input validation, checked arithmetic và JSON output. `workload.hpp` chỉ khai báo naive prime; implementation ở source riêng để tránh hoist qua module. `build_info.hpp` cung cấp metadata macros do CMake tạo.

Harness thu exception từ worker; workload có barrier phải tuân thủ participant contract, không bỏ dở phase. Caller/runner dùng process timeout để chặn case treo do implementation lỗi.
