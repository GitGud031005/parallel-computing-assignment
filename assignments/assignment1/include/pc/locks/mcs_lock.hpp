#pragma once
#include "pc/common/spin.hpp"

namespace pc {
struct NoMcsHooks {
    void after_exchange(bool) const noexcept {}
    void after_failed_release() const noexcept {}
};

// Hooks are compile-time test instrumentation. Production NoMcsHooks is empty.
template<bool Sequential = false, class Hooks = NoMcsHooks>
class BasicMcsLock {
public:
    // 64 is a layout choice, not a claim about every machine's cache-line size.
    struct alignas(64) ThreadContext {
        std::atomic<ThreadContext*> next{nullptr};
        std::atomic<bool> waiting{false};
    };
private:
    std::atomic<ThreadContext*> tail_{nullptr};
    [[no_unique_address]] Hooks hooks_;
public:
    explicit BasicMcsLock(Hooks hooks = {}) : hooks_(hooks) {}
    BasicMcsLock(const BasicMcsLock&) = delete;
    BasicMcsLock& operator=(const BasicMcsLock&) = delete;

    void acquire(ThreadContext& node) noexcept {
        node.next.store(nullptr, order<Sequential>(std::memory_order_relaxed));
        node.waiting.store(true, order<Sequential>(std::memory_order_relaxed));
        // Also acquires the payload from the previous empty-queue release CAS.
        auto* predecessor = tail_.exchange(&node, order<Sequential>(std::memory_order_acq_rel));
        hooks_.after_exchange(predecessor != nullptr);
        if (predecessor != nullptr) {
            predecessor->next.store(&node, order<Sequential>(std::memory_order_release));
            // Acquires protected data published by predecessor's handoff.
            while (node.waiting.load(order<Sequential>(std::memory_order_acquire))) cpu_relax();
        }
    }

    void release(ThreadContext& node) noexcept {
        auto* successor = node.next.load(order<Sequential>(std::memory_order_acquire));
        if (successor == nullptr) {
            auto* expected = &node; // CAS may overwrite expected, never overwrite node.
            if (tail_.compare_exchange_strong(expected, nullptr,
                    order<Sequential>(std::memory_order_release),
                    order<Sequential>(std::memory_order_relaxed))) return;
            // A successor changed tail, but has not necessarily linked next yet.
            // Strong CAS is essential here: a spurious failure would wait forever.
            hooks_.after_failed_release();
            do {
                successor = node.next.load(order<Sequential>(std::memory_order_acquire));
                if (successor == nullptr) cpu_relax();
            } while (successor == nullptr);
        }
        successor->waiting.store(false, order<Sequential>(std::memory_order_release));
    }
};
using McsLock = BasicMcsLock<>;
} // namespace pc
