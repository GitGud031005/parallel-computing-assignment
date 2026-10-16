#pragma once
#include "pc/common/spin.hpp"
#include <cstdint>

namespace pc {
template<bool WithBackoff = false, bool Sequential = false>
class BasicCasCounter {
    std::atomic<std::uint64_t> value_;
public:
    struct ThreadContext {};
    explicit BasicCasCounter(std::uint64_t initial = 0) : value_(initial) {}
    std::uint64_t increment(ThreadContext&) noexcept {
        auto expected = value_.load(order<Sequential>(std::memory_order_relaxed));
        Backoff backoff;
        // Failure updates expected. Recompute desired on EVERY retry.
        while (!value_.compare_exchange_weak(expected, expected + 1,
                order<Sequential>(std::memory_order_relaxed),
                order<Sequential>(std::memory_order_relaxed))) {
            if constexpr (WithBackoff) backoff.wait();
        }
        return expected;
    }
    std::uint64_t value(ThreadContext&) const noexcept {
        return value_.load(order<Sequential>(std::memory_order_relaxed));
    }
};
using CasCounter = BasicCasCounter<>;
using CasBackoffCounter = BasicCasCounter<true>;
} // namespace pc
