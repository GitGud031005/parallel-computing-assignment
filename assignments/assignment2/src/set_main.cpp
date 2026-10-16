#include "pc/a2/cli.hpp"
#include "pc/a2/sorted_list.hpp"
#include "pc/a2/workers.hpp"
#include <algorithm>
#include <chrono>
#include <sstream>
#include <vector>
using namespace pc::a2;
static std::uint64_t random_next(std::uint64_t &x) {
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    return x;
}
template <class Set> void benchmark(const Options &o, const std::string &kind) {
    auto p = o.number("threads", 1), total = o.number("operations", 20000),
         range = o.number("key-range", 256), seed = o.number("seed", 20261016);
    auto mix = o.text("mix", "read_heavy");
    if (p > 1024 || range > 1000000 || (mix != "read_heavy" && mix != "update_heavy"))
        throw std::invalid_argument("invalid set workload");
    Set set;
    for (std::uint64_t i = 0; i < range; i += 2)
        set.insert(static_cast<std::int64_t>(i));
    struct alignas(64) Stats {
        std::uint64_t read = 0, insert = 0, erase = 0, success = 0;
    };
    std::vector<Stats> stats(p);
    auto begin = std::chrono::steady_clock::now();
    workers(p, [&](std::size_t id) {
        auto rng = seed + id + 1;
        auto n = total / p + (id < total % p);
        for (std::uint64_t i = 0; i < n; ++i) {
            auto key = static_cast<std::int64_t>(random_next(rng) % range);
            auto r = random_next(rng) % 100;
            bool ok;
            auto reads = mix == "read_heavy" ? 80U : 20U;
            auto inserts = mix == "read_heavy" ? 90U : 60U;
            if (r < reads) {
                ++stats[id].read;
                ok = set.contains(key);
            } else if (r < inserts) {
                ++stats[id].insert;
                ok = set.insert(key);
            } else {
                ++stats[id].erase;
                ok = set.erase(key);
            }
            stats[id].success += ok;
        }
    });
    auto end = std::chrono::steady_clock::now();
    auto final = set.snapshot_after_join();
    if (!std::is_sorted(final.begin(), final.end()) ||
        std::adjacent_find(final.begin(), final.end()) != final.end())
        throw std::runtime_error("set invariant failed");
    for (auto key : final)
        if (key < 0 || static_cast<std::uint64_t>(key) >= range)
            throw std::runtime_error("set key outside workload");
    Stats sum;
    for (auto s : stats) {
        sum.read += s.read;
        sum.insert += s.insert;
        sum.erase += s.erase;
        sum.success += s.success;
    }
    if (sum.read + sum.insert + sum.erase != total)
        throw std::runtime_error("operation count mismatch");
    std::ostringstream out;
    out << "{\"suite\":\"sets\",\"implementation\":\"" << kind << "\",\"threads\":" << p
        << ",\"operations\":" << total << ",\"key_range\":" << range << ",\"seed\":" << seed
        << ",\"mix\":\"" << mix << "\",\"program_elapsed_ns\":"
        << std::chrono::duration_cast<std::chrono::nanoseconds>(end - begin).count()
        << ",\"reads\":" << sum.read << ",\"inserts\":" << sum.insert << ",\"erases\":" << sum.erase
        << ",\"successful_operations\":" << sum.success << ",\"final_size\":" << final.size();
    build_fields(out);
    out << '}';
    o.emit(out.str());
}
int main(int argc, char **argv) {
    try {
        Options o(
            argc, argv,
            {"implementation", "threads", "operations", "key-range", "seed", "mix", "output"});
        if (o.has("help")) {
            std::cout << "a2_bench_set --implementation coarse|fine --threads P --operations K "
                         "--key-range K --seed K --mix read_heavy|update_heavy [--output JSON]\n";
            return 0;
        }
        auto kind = o.text("implementation", "coarse");
        if (kind == "coarse")
            benchmark<CoarseList<std::int64_t>>(o, kind);
        else if (kind == "fine")
            benchmark<FineList<std::int64_t>>(o, kind);
        else
            throw std::invalid_argument("implementation must be coarse|fine");
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
