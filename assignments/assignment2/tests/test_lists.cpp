#include "pc/a2/sorted_list.hpp"
#include "pc/a2/workers.hpp"
#include "support.hpp"
#include <algorithm>
#include <atomic>
#include <limits>
#include <set>
#include <thread>
using namespace pc::a2;
struct Event {
    int op, key;
    bool result;
    int popped = 0;
    std::uint64_t begin, end;
};
bool linearizable(const std::vector<Event> &h, std::uint64_t done = 0, std::set<int> model = {}) {
    if (done == ((1ULL << h.size()) - 1))
        return true;
    for (std::size_t i = 0; i < h.size(); ++i) {
        if (done & (1ULL << i))
            continue;
        bool ready = true;
        for (std::size_t j = 0; j < h.size(); ++j)
            if (!(done & (1ULL << j)) && h[j].end < h[i].begin)
                ready = false;
        if (!ready)
            continue;
        auto next = model;
        auto e = h[i];
        bool r = false;
        int popped = 0;
        if (e.op == 0)
            r = next.insert(e.key).second;
        if (e.op == 1)
            r = next.erase(e.key) != 0;
        if (e.op == 2)
            r = next.contains(e.key);
        if (e.op == 3 && !next.empty()) {
            r = true;
            popped = *next.begin();
            next.erase(next.begin());
        }
        if (r == e.result && (e.op != 3 || !r || popped == e.popped) &&
            linearizable(h, done | (1ULL << i), std::move(next)))
            return true;
    }
    return false;
}
template <class Set> void suite(bool stress) {
    Set s;
    std::set<std::int64_t> model;
    std::uint64_t seed = 20261016;
    for (int i = 0; i < 5000; ++i) {
        auto key = static_cast<std::int64_t>(rng(seed) % 129) - 64;
        auto op = rng(seed) % 3;
        if (op == 0)
            require(s.insert(key) == model.insert(key).second, "sequential insert");
        if (op == 1)
            require(s.erase(key) == (model.erase(key) != 0), "sequential erase");
        if (op == 2)
            require(s.contains(key) == model.contains(key), "sequential contains");
    }
    for (auto key :
         {std::numeric_limits<std::int64_t>::min(), std::numeric_limits<std::int64_t>::max()}) {
        require(s.insert(key), "boundary insert");
        require(s.erase(key), "boundary erase");
    }
    require(s.snapshot_after_join() == std::vector<std::int64_t>(model.begin(), model.end()),
            "sequential final state");
    for (auto p : {1U, 2U, 3U, 4U, 8U}) {
        Set shared;
        auto count = stress ? 1000U : 200U;
        workers(p, [&](std::size_t id) {
            for (unsigned i = 0; i < count; ++i)
                require(shared.insert(static_cast<std::int64_t>(id * count + i)), "unique insert");
        });
        require(shared.snapshot_after_join().size() == p * count, "all unique inserts retained");
        std::vector<std::vector<std::int64_t>> popped(p);
        workers(p, [&](std::size_t id) {
            std::int64_t v;
            while (shared.try_pop_min(v))
                popped[id].push_back(v);
        });
        std::vector<std::int64_t> all;
        for (auto &v : popped)
            all.insert(all.end(), v.begin(), v.end());
        std::sort(all.begin(), all.end());
        require(all.size() == p * count, "pop count");
        for (std::size_t i = 0; i < all.size(); ++i)
            require(all[i] == static_cast<std::int64_t>(i), "pop unique/no missing");
        std::atomic<unsigned> winners = 0;
        workers(p, [&](std::size_t) { winners += shared.insert(42); });
        require(winners == 1, "one insertion winner");
        workers(p, [&](std::size_t id) {
            auto state = id + 123;
            for (unsigned i = 0; i < count * 4; ++i) {
                auto k = static_cast<std::int64_t>(rng(state) % 64);
                switch (rng(state) % 3) {
                case 0:
                    shared.insert(k);
                    break;
                case 1:
                    shared.erase(k);
                    break;
                default:
                    shared.contains(k);
                }
                if (i % 17 == 0)
                    std::this_thread::yield();
            }
        });
        auto values = shared.snapshot_after_join();
        require(std::is_sorted(values.begin(), values.end()) &&
                    std::adjacent_find(values.begin(), values.end()) == values.end(),
                "stress sorted unique");
    }
    for (std::uint64_t seed2 = 1; seed2 <= (stress ? 100U : 20U); ++seed2) {
        Set list;
        std::atomic<std::uint64_t> clock = 0;
        std::vector<Event> h(12);
        workers(3, [&](std::size_t id) {
            auto state = seed2 * 123 + id + 1;
            for (std::size_t j = 0; j < 4; ++j) {
                Event e{};
                e.op = static_cast<int>(rng(state) % 4);
                e.key = static_cast<int>(rng(state) % 3);
                e.begin = clock.fetch_add(1);
                std::int64_t popped = 0;
                if (e.op == 0)
                    e.result = list.insert(e.key);
                if (e.op == 1)
                    e.result = list.erase(e.key);
                if (e.op == 2)
                    e.result = list.contains(e.key);
                if (e.op == 3)
                    e.result = list.try_pop_min(popped);
                e.popped = static_cast<int>(popped);
                e.end = clock.fetch_add(1);
                h[id * 4 + j] = e;
            }
        });
        require(linearizable(h), "bounded history is not linearizable");
    }
}
int main(int argc, char **argv) {
    return test_main([&] {
        bool stress = argc == 2 && std::string(argv[1]) == "--stress";
        require(!linearizable({{0, 1, true, 0, 0, 3}, {0, 1, true, 0, 1, 2}}),
                "history oracle must reject duplicate insertion success");
        suite<CoarseList<std::int64_t>>(stress);
        suite<FineList<std::int64_t>>(stress);
    });
}
