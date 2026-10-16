#include "test_support.hpp"
#include "pc/barriers/sense_reversing_barrier.hpp"
#include "pc/barriers/std_barrier_adapter.hpp"

template<class Barrier>
void visibility(std::size_t p, std::uint64_t rounds, std::uint64_t seed) {
    Barrier barrier(p), other(p);
    auto a = std::make_unique<pc::WorkerSlot<typename Barrier::ThreadContext>[]>(p);
    auto b = std::make_unique<pc::WorkerSlot<typename Barrier::ThreadContext>[]>(p);
    std::vector<std::uint64_t> slots(p, 0);
    std::atomic<bool> bad{false};
    pc::run_workers(p, [&](std::size_t id) {
        auto rng = seed + id + 1;
        for (std::uint64_t round = 1; round <= rounds; ++round) {
            test::perturb(rng);
            slots[id] = round * p + id;
            barrier.arrive_and_wait(a[id].context);
            for (std::size_t j = 0; j < p; ++j)
                if (slots[j] != round * p + j) bad.store(true, std::memory_order_relaxed);
            // Prevent next-round writes from racing this round's readers.
            barrier.arrive_and_wait(a[id].context);
            other.arrive_and_wait(b[id].context); // A has twice as many phases as B.
        }
    });
    test::require(!bad.load(), "barrier phase/visibility/instance isolation");
}
struct ArrivalHooks {
    std::atomic<bool>* arrived;
    void after_arrival(bool last) const noexcept {
        if (!last) arrived->store(true, std::memory_order_release);
    }
};
void no_early_release() {
    std::atomic<bool> arrived{false}, returned{false};
    pc::BasicSenseReversingBarrier<false, ArrivalHooks> barrier(2, ArrivalHooks{&arrived});
    decltype(barrier)::ThreadContext first, last;
    std::thread worker([&] { barrier.arrive_and_wait(first); returned.store(true); });
    test::wait(arrived); // The first fetch_sub actually happened, not just a pre-call flag.
    bool early = false;
    for (int i = 0; i < 1000; ++i) { early = early || returned.load(); std::this_thread::yield(); }
    barrier.arrive_and_wait(last);
    worker.join();
    test::require(!early && returned.load(), "barrier released before second arrival");
}
template<class Barrier>
void matrix(const std::string& name, bool stress) {
    for (auto p : {1U, 2U, 3U, 4U, 5U, 8U})
        for (auto seed : {1ULL, 17ULL, 2026ULL, 65537ULL, 99991ULL})
            visibility<Barrier>(p, stress ? 10000 : 1000, seed);
    test::run(name + " odd/even, visibility, reuse, A-A-B instances, 5 seeds", [] {});
}
int main(int argc, char** argv) {
    return test::main([&] {
        auto stress = test::stress(argc, argv);
        matrix<pc::SenseReversingBarrier>("Sense-Reversing acquire/release", stress);
        matrix<pc::BasicSenseReversingBarrier<true>>("Sense-Reversing SC", stress);
        matrix<pc::StdBarrier>("std::barrier", stress);
        test::run("delayed last participant/no early release", no_early_release);
        test::run("barrier bounded oversubscription", [] {
            auto p = std::clamp(std::thread::hardware_concurrency() + 1, 2U, 32U);
            visibility<pc::SenseReversingBarrier>(p, 100, 20261016);
        });
        test::run("zero participants rejected", [] {
            bool custom = false, standard = false;
            try { pc::SenseReversingBarrier b(0); } catch (const std::invalid_argument&) { custom = true; }
            try { pc::StdBarrier b(0); } catch (const std::invalid_argument&) { standard = true; }
            test::require(custom && standard, "zero barrier accepted");
        });
    });
}
