#pragma once
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <latch>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <vector>

namespace pc {
using Clock = std::chrono::steady_clock;
struct RunTiming { std::int64_t program_ns; std::int64_t worker_ns; };
struct alignas(64) WorkerTime { Clock::time_point start, end; };

// Independent standard-library gate. Allocation happens before the program timer;
// program_ns covers thread spawn, ready/start gates, work, and joins.
template<class Function>
RunTiming run_workers(std::size_t count, Function&& work) {
    if (count == 0) throw std::invalid_argument("workers must be positive");
    std::latch ready(static_cast<std::ptrdiff_t>(count)), go(1);
    std::atomic<bool> cancel{false};
    auto times = std::make_unique<WorkerTime[]>(count);
    std::vector<std::thread> workers;
    workers.reserve(count);
    std::exception_ptr failure;
    std::mutex failure_mutex;
    auto program_start = Clock::now();
    try {
        for (std::size_t id = 0; id < count; ++id) workers.emplace_back([&, id] {
            ready.count_down();
            go.wait();
            if (cancel.load(std::memory_order_relaxed)) return;
            times[id].start = Clock::now();
            try { work(id); }
            catch (...) {
                std::lock_guard guard(failure_mutex);
                if (!failure) failure = std::current_exception();
            }
            times[id].end = Clock::now();
        });
    } catch (...) {
        cancel.store(true, std::memory_order_relaxed);
        go.count_down();
        for (auto& worker : workers) worker.join();
        throw;
    }
    ready.wait();
    go.count_down();
    for (auto& worker : workers) worker.join();
    auto program_end = Clock::now();
    if (failure) std::rethrow_exception(failure);
    auto first = times[0].start, last = times[0].end;
    for (std::size_t id = 1; id < count; ++id) {
        first = std::min(first, times[id].start);
        last = std::max(last, times[id].end);
    }
    return {std::chrono::duration_cast<std::chrono::nanoseconds>(program_end - program_start).count(),
            std::chrono::duration_cast<std::chrono::nanoseconds>(last - first).count()};
}

inline std::uint64_t share(std::uint64_t total, std::size_t count, std::size_t id) noexcept {
    return total / count + (id < total % count ? 1 : 0);
}
template<class Context>
struct alignas(64) WorkerSlot { Context context; std::uint64_t checksum = 0; };
} // namespace pc
