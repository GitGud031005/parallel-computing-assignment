#pragma once
#include "pc/common/spin.hpp"
#include <cstdint>

namespace pc {
template<bool Sequential = false>
class BasicFaaCounter {
    std::atomic<std::uint64_t> value_;
public:
    struct ThreadContext {};
    explicit BasicFaaCounter(std::uint64_t initial = 0) : value_(initial) {}
    std::uint64_t increment(ThreadContext&) noexcept {
        return value_.fetch_add(1, order<Sequential>(std::memory_order_relaxed));
    }
    std::uint64_t value(ThreadContext&) const noexcept {
        return value_.load(order<Sequential>(std::memory_order_relaxed));
    }
};
using FaaCounter = BasicFaaCounter<>;
} // namespace pc
