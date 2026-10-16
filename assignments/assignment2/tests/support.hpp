#pragma once
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
inline void require(bool condition, const std::string &message) {
    if (!condition)
        throw std::runtime_error(message);
}
template <class F> int test_main(F &&f) {
    try {
        f();
        std::cout << "PASS\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL " << e.what() << '\n';
        return 1;
    }
}
inline std::uint64_t rng(std::uint64_t &x) {
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    return x;
}
