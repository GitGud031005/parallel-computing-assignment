#pragma once
#include <mutex>

namespace pc {
class StdMutex {
    std::mutex mutex_;
public:
    struct ThreadContext {};
    void acquire(ThreadContext&) { mutex_.lock(); }
    void release(ThreadContext&) { mutex_.unlock(); }
};
} // namespace pc
