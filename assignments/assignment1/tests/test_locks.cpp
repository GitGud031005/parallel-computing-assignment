#include "test_support.hpp"
#include "pc/locks/tas_lock.hpp"
#include "pc/locks/ttas_lock.hpp"
#include "pc/locks/mcs_lock.hpp"
#include "pc/locks/std_mutex_adapter.hpp"
#include "pc/locks/scoped_lock.hpp"
#include <array>
#include <latch>

template<class Lock>
void exercise(std::size_t p, std::uint64_t iterations, std::uint64_t seed) {
    Lock lock;
    auto contexts = std::make_unique<pc::WorkerSlot<typename Lock::ThreadContext>[]>(p);
    std::atomic<int> occupancy{0};
    std::atomic<bool> bad{false};
    std::uint64_t count = 0;
    pc::run_workers(p, [&](std::size_t id) {
        auto rng = seed + id + 1;
        for (std::uint64_t i = 0; i < iterations; ++i) {
            pc::ScopedLock guard(lock, contexts[id].context);
            if (occupancy.fetch_add(1) != 0) bad.store(true, std::memory_order_relaxed);
            ++count;
            test::perturb(rng);
            if (occupancy.fetch_sub(1) != 1) bad.store(true, std::memory_order_relaxed);
        }
    });
    test::require(!bad.load() && count == p * iterations, "mutual exclusion/count");

    // Separate test: no occupancy or telemetry RMW in the valid payload path.
    constexpr std::uint64_t mask = 0xabcddcba12345678ULL;
    std::uint64_t version = 0, mirror = mask, checksum = 7;
    pc::run_workers(p, [&](std::size_t id) {
        auto rng = seed + id + 7;
        for (std::uint64_t i = 0; i < iterations; ++i) {
            test::perturb(rng);
            pc::ScopedLock guard(lock, contexts[id].context);
            if (mirror != (version ^ mask) || checksum != version * 3 + 7)
                bad.store(true, std::memory_order_relaxed);
            ++version; mirror = version ^ mask; checksum = version * 3 + 7;
        }
    });
    test::require(!bad.load() && version == p * iterations, "payload publication");

    Lock other;
    auto other_contexts = std::make_unique<pc::WorkerSlot<typename Lock::ThreadContext>[]>(p);
    std::uint64_t paired = 0;
    pc::run_workers(p, [&](std::size_t id) {
        for (int i = 0; i < 100; ++i) {
            pc::ScopedLock first(lock, contexts[id].context);
            pc::ScopedLock second(other, other_contexts[id].context);
            ++paired;
        }
    });
    test::require(paired == p * 100, "independent instances/contexts");
    typename Lock::ThreadContext local;
    try { pc::ScopedLock guard(lock, local); throw std::runtime_error("intentional"); }
    catch (const std::runtime_error&) {}
    { pc::ScopedLock guard(lock, local); }
}

struct GapState {
    std::atomic<bool> exchanged{false}, allow_link{false}, failed_release{false};
};
struct GapHooks {
    GapState* state;
    void after_exchange(bool queued) const noexcept {
        if (queued) {
            state->exchanged.store(true, std::memory_order_release);
            test::wait(state->allow_link);
        }
    }
    void after_failed_release() const noexcept { state->failed_release.store(true, std::memory_order_release); }
};
template<bool Sequential>
void enqueue_gap() {
    using Lock = pc::BasicMcsLock<Sequential, GapHooks>;
    GapState state;
    Lock lock(GapHooks{&state});
    typename Lock::ThreadContext owner, successor;
    lock.acquire(owner);
    std::atomic<bool> owner_returned{false}, saw_blocked_release{false}, successor_entered{false};
    std::thread next([&] {
        lock.acquire(successor);
        successor_entered.store(true, std::memory_order_relaxed);
        lock.release(successor);
    });
    test::wait(state.exchanged);
    std::thread controller([&] {
        test::wait(state.failed_release);
        saw_blocked_release.store(!owner_returned.load(), std::memory_order_relaxed);
        state.allow_link.store(true, std::memory_order_release);
    });
    lock.release(owner); // Must wait for successor's link; controller opens it.
    owner_returned.store(true);
    next.join(); controller.join();
    test::require(saw_blocked_release.load() && successor_entered.load(), "MCS enqueue gap/handoff");
}
struct FifoHooks {
    std::atomic<int>* count;
    void after_exchange(bool queued) const noexcept { if (queued) count->fetch_add(1, std::memory_order_release); }
    void after_failed_release() const noexcept {}
};
void fifo() {
    using Lock = pc::BasicMcsLock<false, FifoHooks>;
    std::atomic<int> enqueued{0};
    Lock lock(FifoHooks{&enqueued});
    std::array<Lock::ThreadContext, 4> contexts;
    std::array<int, 3> order{};
    int position = 0;
    lock.acquire(contexts[0]);
    std::vector<std::thread> workers;
    for (int id = 1; id <= 3; ++id) {
        workers.emplace_back([&, id] {
            pc::ScopedLock guard(lock, contexts[id]);
            order[position++] = id;
        });
        while (enqueued.load(std::memory_order_acquire) != id) pc::cpu_relax();
    }
    lock.release(contexts[0]);
    for (auto& t : workers) t.join();
    test::require(order == std::array<int, 3>{1, 2, 3}, "MCS FIFO enqueue order");
}
template<class Lock>
void matrix(const std::string& name, bool stress) {
    for (std::uint64_t seed : {1ULL, 17ULL, 2026ULL, 65537ULL, 99991ULL})
        for (std::size_t p : {1U, 2U, 3U, 4U, 5U, 8U})
            exercise<Lock>(p, stress ? 10000 : 1000, seed);
    test::run(name + " safety/payload/reuse/instances/RAII 5 seeds x 6 thread counts", [] {});
}
int main(int argc, char** argv) {
    return test::main([&] {
        auto stress = test::stress(argc, argv);
        matrix<pc::TasLock>("TAS acquire/release", stress);
        matrix<pc::TtasLock>("TTAS acquire/release", stress);
        matrix<pc::McsLock>("MCS acquire/release", stress);
        matrix<pc::StdMutex>("std::mutex", stress);
        matrix<pc::TtasBackoffLock>("TTAS backoff", stress);
        matrix<pc::BasicTasLock<true>>("TAS SC", stress);
        matrix<pc::BasicTtasLock<false, true>>("TTAS SC", stress);
        matrix<pc::BasicMcsLock<true>>("MCS SC", stress);
        test::run("MCS deterministic enqueue gap acquire/release", [] { enqueue_gap<false>(); });
        test::run("MCS deterministic enqueue gap SC", [] { enqueue_gap<true>(); });
        test::run("MCS controlled FIFO", fifo);
        test::run("MCS bounded oversubscription", [] {
            auto p = std::clamp(std::thread::hardware_concurrency() + 1, 2U, 32U);
            exercise<pc::McsLock>(p, 100, 20261016);
        });
    });
}
