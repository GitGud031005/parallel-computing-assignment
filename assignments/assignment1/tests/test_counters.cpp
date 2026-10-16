#include "test_support.hpp"
#include "pc/counters/mutex_counter.hpp"
#include "pc/counters/cas_counter.hpp"
#include "pc/counters/faa_counter.hpp"
#include "pc/locks/tas_lock.hpp"
#include "pc/locks/ttas_lock.hpp"
#include "pc/locks/mcs_lock.hpp"
#include "pc/locks/std_mutex_adapter.hpp"
#include <limits>

template<class Counter>
void exercise(std::size_t p, std::uint64_t per_thread, std::uint64_t seed) {
    Counter counter;
    auto contexts = std::make_unique<pc::WorkerSlot<typename Counter::ThreadContext>[]>(p);
    std::vector<std::vector<std::uint64_t>> returned(p, std::vector<std::uint64_t>(per_thread));
    std::atomic<bool> bad{false};
    pc::run_workers(p, [&](std::size_t id) {
        auto rng = seed + id + 1;
        for (std::uint64_t i = 0; i < per_thread; ++i) {
            test::perturb(rng);
            auto old = counter.increment(contexts[id].context);
            returned[id][i] = old;
            if (i % 13 == 0 && counter.value(contexts[id].context) < old + 1)
                bad.store(true, std::memory_order_relaxed);
        }
    });
    typename Counter::ThreadContext main_context;
    auto total = p * per_thread;
    test::require(counter.value(main_context) == total && !bad.load(), "count/monotonic read");
    std::vector<std::uint64_t> all;
    all.reserve(total);
    for (auto& local : returned) all.insert(all.end(), local.begin(), local.end());
    std::sort(all.begin(), all.end());
    for (std::uint64_t i = 0; i < total; ++i) test::require(all[i] == i, "duplicate/missing returned value");
    // These calls cannot overlap the workers (join establishes real-time precedence).
    test::require(counter.increment(main_context) == total, "post-join increment ordering");
    test::require(counter.value(main_context) == total + 1, "post-join value ordering");
}
template<class Counter>
void matrix(const std::string& name, bool stress) {
    for (auto p : {1U, 2U, 3U, 4U, 5U, 8U})
        for (auto seed : {1ULL, 17ULL, 2026ULL, 65537ULL, 99991ULL})
            exercise<Counter>(p, stress ? 10000 : 1000, seed);
    Counter a(0), b(std::numeric_limits<std::uint64_t>::max() - 2);
    typename Counter::ThreadContext x, y;
    test::require(a.increment(x) == 0, "instance initialization");
    auto max = std::numeric_limits<std::uint64_t>::max();
    test::require(b.increment(y) == max - 2 && b.increment(y) == max - 1 && b.value(y) == max, "nonwrapping boundary");
    test::require(a.value(x) == 1, "instance state leaked");
    test::run(name + " count/unique/read/precedence/boundary/instances 5 seeds", [] {});
}
int main(int argc, char** argv) {
    return test::main([&] {
        auto stress = test::stress(argc, argv);
        matrix<pc::MutexCounter<pc::TasLock>>("mutex TAS", stress);
        matrix<pc::MutexCounter<pc::TtasLock>>("mutex TTAS", stress);
        matrix<pc::MutexCounter<pc::McsLock>>("mutex MCS", stress);
        matrix<pc::MutexCounter<pc::StdMutex>>("mutex std", stress);
        matrix<pc::CasCounter>("CAS relaxed", stress);
        matrix<pc::FaaCounter>("FAA relaxed", stress);
        matrix<pc::CasBackoffCounter>("CAS backoff", stress);
        matrix<pc::BasicCasCounter<false, true>>("CAS SC", stress);
        matrix<pc::BasicFaaCounter<true>>("FAA SC", stress);
        test::run("CAS bounded oversubscription", [] {
            auto p = std::clamp(std::thread::hardware_concurrency() + 1, 2U, 32U);
            exercise<pc::CasCounter>(p, 100, 20261016);
        });
    });
}
