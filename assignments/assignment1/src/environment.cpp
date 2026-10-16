#include "pc/common/spin.hpp"
#include <iostream>
#include <version>
#ifndef PC_SOURCE_SHA256
#define PC_SOURCE_SHA256 "unrecorded"
#endif
#ifndef PC_BUILD_TYPE
#define PC_BUILD_TYPE "unrecorded"
#endif
#ifndef PC_SANITIZER_NAME
#define PC_SANITIZER_NAME "none"
#endif
int main() {
    std::atomic<std::uint64_t> integer{0};
    std::atomic<bool> boolean{false};
    std::atomic<void*> pointer{nullptr};
    std::cout << std::boolalpha << "{\"source_sha256\":\"" << PC_SOURCE_SHA256
              << "\",\"build_type\":\"" << PC_BUILD_TYPE
              << "\",\"sanitizer\":\"" << PC_SANITIZER_NAME
              << "\",\"cxx_standard\":" << __cplusplus
              << ",\"atomic_uint64_lock_free\":" << integer.is_lock_free()
              << ",\"atomic_bool_lock_free\":" << boolean.is_lock_free()
              << ",\"atomic_pointer_lock_free\":" << pointer.is_lock_free()
#ifdef __GLIBCXX__
              << ",\"libstdcxx_date\":" << __GLIBCXX__
#endif
#ifdef _LIBCPP_VERSION
              << ",\"libcxx_version\":" << _LIBCPP_VERSION
#endif
#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) || defined(_M_X64)
              << ",\"spin_hint\":\"x86_pause\""
#else
              << ",\"spin_hint\":\"std_this_thread_yield\""
#endif
              << "}\n";
}
