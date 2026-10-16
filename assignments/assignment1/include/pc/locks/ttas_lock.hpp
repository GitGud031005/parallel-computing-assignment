#pragma once
#include "pc/common/spin.hpp"

namespace pc {
template<bool WithBackoff = false, bool Sequential = false>
class BasicTtasLock {
    std::atomic<bool> flag_{false};
public:
    struct ThreadContext {};
    void acquire(ThreadContext&) noexcept {
        Backoff backoff;
        for (;;) {
            // This load is only a hint. Only the successful RMW grants the lock.
            while (flag_.load(order<Sequential>(std::memory_order_relaxed))) cpu_relax();
            if (!flag_.exchange(true, order<Sequential>(std::memory_order_acquire))) return;
            if constexpr (WithBackoff) backoff.wait();
        }
    }
    void release(ThreadContext&) noexcept {
        flag_.store(false, order<Sequential>(std::memory_order_release));
    }
};
using TtasLock = BasicTtasLock<>;
using TtasBackoffLock = BasicTtasLock<true>;
} // namespace pc
