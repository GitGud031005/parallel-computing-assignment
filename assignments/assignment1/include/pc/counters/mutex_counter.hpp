#pragma once
#include "pc/locks/scoped_lock.hpp"
#include <cstdint>

namespace pc {
template<class Lock>
class MutexCounter {
    Lock lock_;
    std::uint64_t value_;
public:
    using ThreadContext = typename Lock::ThreadContext;
    explicit MutexCounter(std::uint64_t initial = 0) : value_(initial) {}
    // Precondition: the workload does not wrap uint64_t.
    std::uint64_t increment(ThreadContext& context) {
        ScopedLock guard(lock_, context);
        return value_++;
    }
    std::uint64_t value(ThreadContext& context) {
        ScopedLock guard(lock_, context);
        return value_;
    }
};
} // namespace pc
