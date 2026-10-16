#include "pc/common/workload.hpp"

namespace pc {
bool is_prime(std::uint32_t n) noexcept {
    if (n < 2) return false;
    for (std::uint32_t divisor = 2; divisor < n; ++divisor)
        if (n % divisor == 0) return false;
    return true;
}
} // namespace pc
