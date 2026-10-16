#pragma once
#include "pc/common/spin.hpp"

namespace pc {
template<bool Sequential = false>
class BasicTasLock {
    std::atomic_flag flag_ = ATOMIC_FLAG_INIT;
public:
    struct ThreadContext {};
    void acquire(ThreadContext&) noexcept {
        while (flag_.test_and_set(order<Sequential>(std::memory_order_acquire))) cpu_relax();
    }
    void release(ThreadContext&) noexcept {
        // Publishes the protected payload to the next successful acquire.
        flag_.clear(order<Sequential>(std::memory_order_release));
    }
};
using TasLock = BasicTasLock<>;
} // namespace pc
