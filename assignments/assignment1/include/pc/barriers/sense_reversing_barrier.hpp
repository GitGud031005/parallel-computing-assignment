#pragma once
#include "pc/common/spin.hpp"
#include <cstddef>
#include <stdexcept>

namespace pc {
struct NoBarrierHooks { void after_arrival(bool) const noexcept {} };
template<bool Sequential = false, class Hooks = NoBarrierHooks>
class BasicSenseReversingBarrier {
    const std::size_t participants_;
    alignas(64) std::atomic<std::size_t> remaining_;
    alignas(64) std::atomic<bool> sense_{false};
    [[no_unique_address]] Hooks hooks_;
public:
    struct ThreadContext { bool local_sense = false; };
    explicit BasicSenseReversingBarrier(std::size_t participants, Hooks hooks = {})
        : participants_(participants), remaining_(participants), hooks_(hooks) {
        if (participants == 0) throw std::invalid_argument("barrier participants must be positive");
    }
    void arrive_and_wait(ThreadContext& context) noexcept {
        context.local_sense = !context.local_sense;
        // Each RMW acquires all earlier arrivals and releases its own payload.
        const auto previous = remaining_.fetch_sub(1, order<Sequential>(std::memory_order_acq_rel));
        hooks_.after_arrival(previous == 1);
        if (previous == 1) {
            remaining_.store(participants_, order<Sequential>(std::memory_order_relaxed));
            // Reset precedes release; departing threads can safely start next phase.
            sense_.store(context.local_sense, order<Sequential>(std::memory_order_release));
        } else {
            while (sense_.load(order<Sequential>(std::memory_order_acquire)) != context.local_sense)
                cpu_relax();
        }
    }
};
using SenseReversingBarrier = BasicSenseReversingBarrier<>;
} // namespace pc
