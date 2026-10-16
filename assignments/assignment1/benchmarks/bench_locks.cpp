#include "pc/common/cli.hpp"
#include "pc/common/workload.hpp"
#include "pc/locks/tas_lock.hpp"
#include "pc/locks/ttas_lock.hpp"
#include "pc/locks/mcs_lock.hpp"
#include "pc/locks/std_mutex_adapter.hpp"
#include "pc/locks/scoped_lock.hpp"

template<class Lock>
pc::Result benchmark(pc::Result result) {
    Lock lock;
    auto slots = std::make_unique<pc::WorkerSlot<typename Lock::ThreadContext>[]>(result.threads);
    auto total = *result.total, outside = *result.outside_work;
    auto n = static_cast<std::uint32_t>(*result.prime_n);
    result.timing = pc::run_workers(result.threads, [&](std::size_t id) {
        auto iterations = result.mode == "per_thread" ? *result.iterations : pc::share(total, result.threads, id);
        auto& context = slots[id].context;
        std::uint64_t checksum = 0;
        for (std::uint64_t i = 0; i < iterations; ++i) {
            { pc::ScopedLock guard(lock, context); checksum += pc::is_prime(n); }
            for (std::uint64_t j = 0; j < outside; ++j) checksum += pc::is_prime(n);
        }
        slots[id].checksum = checksum;
    });
    std::uint64_t checksum = 0;
    for (std::size_t id = 0; id < result.threads; ++id) checksum += slots[id].checksum;
    auto expected = pc::is_prime(n) ? pc::checked_mul(total, pc::checked_add(outside, 1)) : 0;
    if (checksum != expected) throw std::runtime_error("prime workload checksum mismatch");
    result.checksum = checksum;
    return result;
}
int main(int argc, char** argv) {
    try {
        pc::Options o(argc, argv, {"implementation", "threads", "mode", "iterations-per-thread",
                                 "total-operations", "prime-n", "outside-work", "output"});
        if (o.has("help")) {
            std::cout << "bench_locks --implementation tas|ttas|mcs|std_mutex|ttas_backoff --threads P "
                         "--mode per_thread|fixed_total [--iterations-per-thread I | --total-operations K] "
                         "--prime-n N --outside-work W [--output JSON]\n";
            return 0;
        }
        pc::Result r;
        r.suite = "locks"; r.implementation = o.text("implementation", "std_mutex");
        r.threads = o.threads(); r.mode = o.text("mode", "per_thread");
        r.prime_n = o.number("prime-n", 997);
        if (*r.prime_n < 2 || *r.prime_n > std::numeric_limits<std::uint32_t>::max())
            throw std::invalid_argument("prime-n must be in [2, UINT32_MAX]");
        r.outside_work = o.number("outside-work", 0, true);
        if (r.mode == "per_thread") {
            if (o.has("total-operations")) throw std::invalid_argument("total-operations requires fixed_total mode");
            r.iterations = o.number("iterations-per-thread", 10000);
            r.total = pc::checked_mul(*r.iterations, r.threads);
        } else if (r.mode == "fixed_total") {
            if (o.has("iterations-per-thread")) throw std::invalid_argument("iterations-per-thread requires per_thread mode");
            r.total = o.number("total-operations", 100000);
        } else throw std::invalid_argument("unknown workload mode");
        pc::checked_mul(*r.total, pc::checked_add(*r.outside_work, 1));
        if (r.implementation == "tas") r = benchmark<pc::TasLock>(r);
        else if (r.implementation == "ttas") r = benchmark<pc::TtasLock>(r);
        else if (r.implementation == "mcs") r = benchmark<pc::McsLock>(r);
        else if (r.implementation == "std_mutex") r = benchmark<pc::StdMutex>(r);
        else if (r.implementation == "ttas_backoff") { r.backoff = true; r = benchmark<pc::TtasBackoffLock>(r); }
        else throw std::invalid_argument("unknown lock implementation");
        pc::emit_result(o, r);
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
