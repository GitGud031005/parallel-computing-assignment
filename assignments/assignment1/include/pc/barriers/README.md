# Barrier headers dự kiến

Chưa có implementation. M3 sẽ tạo `sense_reversing_barrier.hpp` và `std_barrier_adapter.hpp` theo [design.md](../../../docs/design.md).

Context local sense thuộc từng worker và từng custom barrier instance. Participant count cố định; không hỗ trợ drop trong bản bắt buộc. Tách state của start gate khỏi barrier đang test/đo.
