#pragma once
#include <barrier>
#include <cstddef>
#include <stdexcept>

namespace pc {
class StdBarrier {
    static std::ptrdiff_t checked(std::size_t n) {
        if (n == 0 || n > static_cast<std::size_t>(std::barrier<>::max()))
            throw std::invalid_argument("invalid std::barrier participant count");
        return static_cast<std::ptrdiff_t>(n);
    }
    std::barrier<> barrier_;
public:
    struct ThreadContext {};
    explicit StdBarrier(std::size_t n) : barrier_(checked(n)) {}
    void arrive_and_wait(ThreadContext&) { barrier_.arrive_and_wait(); }
};
} // namespace pc
