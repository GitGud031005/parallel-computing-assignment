#pragma once

namespace pc {
template<class Lock>
class ScopedLock {
    Lock& lock_;
    typename Lock::ThreadContext& context_;
public:
    ScopedLock(Lock& lock, typename Lock::ThreadContext& context)
        : lock_(lock), context_(context) { lock_.acquire(context_); }
    ~ScopedLock() { lock_.release(context_); }
    ScopedLock(const ScopedLock&) = delete;
    ScopedLock& operator=(const ScopedLock&) = delete;
};
} // namespace pc
