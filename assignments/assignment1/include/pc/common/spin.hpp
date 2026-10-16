#pragma once

#include <atomic>
#include <cstdint>
#include <thread>
#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
#include <immintrin.h>
#endif

namespace pc {
// A CPU hint, not a memory barrier or a scheduling/fairness guarantee.
inline void cpu_relax() noexcept {
#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
    _mm_pause();
#else
    std::this_thread::yield();
#endif
}

template<bool Sequential>
constexpr std::memory_order order(std::memory_order normal) noexcept {
    return Sequential ? std::memory_order_seq_cst : normal;
}

// Bounded deterministic exponential backoff, measured in pause steps, NOT ns.
class Backoff {
    std::uint32_t delay_ = 1;
public:
    static constexpr std::uint32_t initial = 1;
    static constexpr std::uint32_t maximum = 1024;
    void wait() noexcept {
        for (std::uint32_t i = 0; i < delay_; ++i) cpu_relax();
        delay_ = delay_ < maximum / 2 ? delay_ * 2 : maximum;
    }
};
} // namespace pc
