#pragma once
#include <cstdint>

namespace pc {
// Deliberately naive trial division from the assignment. Separate TU; no LTO.
bool is_prime(std::uint32_t n) noexcept;
}
