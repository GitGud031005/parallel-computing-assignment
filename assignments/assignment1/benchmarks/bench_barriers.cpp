#include "pc/common/cli.hpp"
#include "pc/barriers/sense_reversing_barrier.hpp"
#include "pc/barriers/std_barrier_adapter.hpp"

template<class Barrier>
pc::Result benchmark(pc::Result result) {
    Barrier barrier(result.threads);
    auto contexts = std::make_unique<pc::WorkerSlot<typename Barrier::ThreadContext>[]>(result.threads);
    const auto episodes = *result.episodes;
    result.timing = pc::run_workers(result.threads, [&](std::size_t id) {
        for (std::uint64_t i = 0; i < episodes; ++i) barrier.arrive_and_wait(contexts[id].context);
    });
    return result;
}
int main(int argc, char** argv) {
    try {
        pc::Options o(argc, argv, {"implementation", "threads", "episodes", "output"});
        if (o.has("help")) {
            std::cout << "bench_barriers --implementation sense_reversing|std_barrier --threads P --episodes E [--output JSON]\n";
            return 0;
        }
        pc::Result r;
        r.suite = "barriers"; r.mode = "fixed_episodes";
        r.implementation = o.text("implementation", "std_barrier");
        r.threads = o.threads(); r.episodes = o.number("episodes", 10000);
        pc::checked_mul(*r.episodes, r.threads);
        if (r.implementation == "sense_reversing") r = benchmark<pc::SenseReversingBarrier>(r);
        else if (r.implementation == "std_barrier") r = benchmark<pc::StdBarrier>(r);
        else throw std::invalid_argument("unknown barrier implementation");
        pc::emit_result(o, r);
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
