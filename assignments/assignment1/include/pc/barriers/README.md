# Reusable barriers

`sense_reversing_barrier.hpp` chứa custom sense-reversing và SC reference; `std_barrier_adapter.hpp` chứa C++20 baseline. API `arrive_and_wait(context)`, participant count cố định và dương.

Context local sense riêng cho từng worker và từng instance. Không hỗ trợ drop/cancel; hủy barrier sau join. Lập luận happens-before ở mục 3 của báo cáo; xem [tests](../../../tests/test_barriers.cpp).
