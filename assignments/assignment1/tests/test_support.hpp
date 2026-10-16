#pragma once
#include "pc/common/spin.hpp"
#include "pc/common/worker_harness.hpp"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>

namespace test {
inline void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
inline void perturb(std::uint64_t& seed) {
    seed ^= seed << 13; seed ^= seed >> 7; seed ^= seed << 17;
    if ((seed & 63U) == 0) std::this_thread::yield();
}
inline void wait(const std::atomic<bool>& flag) {
    while (!flag.load(std::memory_order_acquire)) pc::cpu_relax();
}
template<class F>
void run(const std::string& name, F&& f) {
    f();
    std::cout << "PASS " << name << '\n';
}
template<class F>
int main(F&& f) {
    try { f(); return 0; }
    catch (const std::exception& error) { std::cerr << "FAIL " << error.what() << '\n'; return 1; }
}
inline bool stress(int argc, char** argv) {
    if (argc == 1) return false;
    if (argc == 2 && std::string(argv[1]) == "--stress") return true;
    throw std::invalid_argument("only --stress is supported");
}
} // namespace test
