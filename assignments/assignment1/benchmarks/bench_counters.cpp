#include "pc/common/cli.hpp"
#include "pc/counters/mutex_counter.hpp"
#include "pc/counters/cas_counter.hpp"
#include "pc/counters/faa_counter.hpp"
#include "pc/locks/tas_lock.hpp"
#include "pc/locks/ttas_lock.hpp"
#include "pc/locks/mcs_lock.hpp"
#include "pc/locks/std_mutex_adapter.hpp"

template<class Counter>
pc::Result benchmark(pc::Result result) {
    Counter counter;
    auto slots = std::make_unique<pc::WorkerSlot<typename Counter::ThreadContext>[]>(result.threads);
    const auto total = *result.total;
    result.timing = pc::run_workers(result.threads, [&](std::size_t id) {
        std::uint64_t checksum = 0;
        auto count = pc::share(total, result.threads, id);
        for (std::uint64_t i = 0; i < count; ++i) checksum += counter.increment(slots[id].context);
        slots[id].checksum = checksum;
    });
    typename Counter::ThreadContext reader;
    result.final_value = counter.value(reader);
    std::uint64_t checksum = 0;
    for (std::size_t id = 0; id < result.threads; ++id) checksum += slots[id].checksum;
    auto expected = total % 2 == 0 ? (total / 2) * (total - 1) : total * ((total - 1) / 2);
    if (*result.final_value != total || checksum != expected)
        throw std::runtime_error("counter result/checksum mismatch");
    result.checksum = checksum;
    return result;
}
int main(int argc, char** argv) {
    try {
        pc::Options o(argc, argv, {"implementation", "threads", "total-operations", "output"});
        if (o.has("help")) {
            std::cout << "bench_counters --implementation mutex_tas|mutex_ttas|mutex_mcs|mutex_std|cas|faa|cas_backoff "
                         "--threads P --total-operations K [--output JSON]\n";
            return 0;
        }
        pc::Result r;
        r.suite = "counters"; r.mode = "fixed_total";
        r.implementation = o.text("implementation", "faa");
        r.threads = o.threads(); r.total = o.number("total-operations", 100000);
        if (r.implementation == "mutex_tas") r = benchmark<pc::MutexCounter<pc::TasLock>>(r);
        else if (r.implementation == "mutex_ttas") r = benchmark<pc::MutexCounter<pc::TtasLock>>(r);
        else if (r.implementation == "mutex_mcs") r = benchmark<pc::MutexCounter<pc::McsLock>>(r);
        else if (r.implementation == "mutex_std") r = benchmark<pc::MutexCounter<pc::StdMutex>>(r);
        else if (r.implementation == "cas") r = benchmark<pc::CasCounter>(r);
        else if (r.implementation == "faa") r = benchmark<pc::FaaCounter>(r);
        else if (r.implementation == "cas_backoff") { r.backoff = true; r = benchmark<pc::CasBackoffCounter>(r); }
        else throw std::invalid_argument("unknown counter implementation");
        pc::emit_result(o, r);
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
