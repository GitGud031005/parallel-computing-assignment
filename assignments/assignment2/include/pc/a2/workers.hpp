#pragma once
#include <atomic>
#include <cstddef>
#include <exception>
#include <latch>
#include <mutex>
#include <thread>
#include <vector>
namespace pc::a2 {
// Function must cancel any algorithm-specific waits before rethrowing an exception.
template <class Function> void workers(std::size_t count, Function &&function) {
    std::latch ready(static_cast<std::ptrdiff_t>(count)), go(1);
    std::atomic<bool> aborted = false;
    std::vector<std::thread> threads;
    threads.reserve(count);
    std::mutex mutex;
    std::exception_ptr failure;
    try {
        for (std::size_t id = 0; id < count; ++id)
            threads.emplace_back([&, id] {
                ready.count_down();
                go.wait();
                if (aborted.load())
                    return;
                try {
                    function(id);
                } catch (...) {
                    std::lock_guard lock(mutex);
                    if (!failure)
                        failure = std::current_exception();
                }
            });
    } catch (...) {
        aborted.store(true);
        go.count_down();
        for (auto &t : threads)
            t.join();
        throw;
    }
    ready.wait();
    go.count_down();
    for (auto &t : threads)
        t.join();
    if (failure)
        std::rethrow_exception(failure);
}
} // namespace pc::a2
