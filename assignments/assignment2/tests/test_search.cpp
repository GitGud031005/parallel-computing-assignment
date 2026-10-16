#include "pc/a2/search.hpp"
#include "support.hpp"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <future>
#include <set>
#include <thread>
using namespace pc::a2;
std::vector<Cost> exhaustive(const Graph &g, std::size_t s, std::size_t t) {
    std::set<Cost> costs;
    std::vector<bool> visited(g.vertices.size(), false);
    std::function<void(std::size_t, Cost)> dfs = [&](std::size_t u, Cost cost) {
        if (u == t) {
            costs.insert(cost);
            return;
        }
        visited[u] = true;
        for (auto e : g.edges[u])
            if (!visited[e.to])
                dfs(e.to, add(cost, e.cost));
        visited[u] = false;
    };
    dfs(s, {0, 0});
    std::vector<Cost> frontier;
    for (auto a : costs) {
        bool bad = false;
        for (auto b : costs)
            if (a != b && dominates(b, a, Objective::pareto))
                bad = true;
        if (!bad)
            frontier.push_back(a);
    }
    return frontier;
}
void compare(const Graph &g, bool stress) {
    LandmarkBounds bounds(g);
    auto target = g.vertices.size() - 1;
    auto expected = exhaustive(g, 0, target);
    for (std::size_t c = 0; c < 2; ++c) {
        auto d = dijkstra(g, 0, c);
        auto best = infinity;
        for (auto cost : expected)
            best = std::min(best, cost[c]);
        require(d[target] == best, "independent Dijkstra oracle");
    }
    for (std::size_t c = 0; c < 2; ++c) {
        auto exact = dijkstra(g, target, c, true);
        for (std::size_t v = 0; v < g.vertices.size(); ++v)
            require(bounds.estimate(v, target)[c] <= exact[v], "landmark admissibility");
    }
    for (auto policy :
         {Heuristic::zero, Heuristic::landmark, Heuristic::dynamic, Heuristic::uncertain})
        for (auto objective : {Objective::distance, Objective::time, Objective::pareto})
            for (auto engine : {"sequential", "coarse", "fine"})
                for (auto p : {1U, 2U, 4U}) {
                    if (std::string(engine) == "sequential" && p != 1)
                        continue;
                    SearchOptions o;
                    o.engine = engine;
                    o.heuristic = policy;
                    o.objective = objective;
                    o.threads = p;
                    o.dynamic_period = 1;
                    auto r = search(g, bounds, 0, target, o);
                    std::vector<Cost> got;
                    for (auto &path : r.paths) {
                        validate_path(g, path, 0, target);
                        got.push_back(path.cost);
                    }
                    require(got.empty() == expected.empty(), "reachability");
                    if (objective == Objective::pareto)
                        require(got == expected, "full exact Pareto frontier");
                    else if (!expected.empty()) {
                        auto c = objective == Objective::distance ? 0U : 1U;
                        auto best = infinity;
                        for (auto a : expected)
                            best = std::min(best, a[c]);
                        require(got.size() == 1 && got[0][c] == best, "scalar optimum");
                    }
                    if (stress) {
                        auto again = search(g, bounds, 0, target, o);
                        require(again.paths.size() == r.paths.size(),
                                "repeat frontier cardinality");
                    }
                }
}
void in_flight() {
    Graph g(3);
    g.connect(0, 1, {1, 1});
    g.connect(0, 2, {20, 20});
    g.connect(1, 2, {1, 1});
    LandmarkBounds b(g);
    for (auto engine : {"coarse", "fine"}) {
        std::atomic<bool> blocked = false, allow = false, goal_seen = false;
        SearchOptions o;
        o.engine = engine;
        o.threads = 2;
        o.heuristic = Heuristic::zero;
        o.after_pop = [&](std::size_t v) {
            if (v == 1) {
                blocked = true;
                while (!allow.load())
                    std::this_thread::yield();
            }
            if (v == 2)
                goal_seen = true;
        };
        auto future = std::async(std::launch::async, [&] { return search(g, b, 0, 2, o); });
        auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
        while ((!blocked.load() || !goal_seen.load()) &&
               std::chrono::steady_clock::now() < deadline)
            std::this_thread::yield();
        bool reached = blocked && goal_seen;
        bool waiting = future.wait_for(std::chrono::milliseconds(5)) == std::future_status::timeout;
        allow = true;
        auto r = future.get();
        require(reached && waiting, "must not terminate with active work and empty queue");
        require(r.paths.at(0).cost == Cost{2, 2}, "first parallel goal is not necessarily optimal");
        o.after_pop = [](std::size_t) { throw std::runtime_error("injected worker failure"); };
        bool caught = false;
        try {
            search(g, b, 0, 2, o);
        } catch (const std::runtime_error &) {
            caught = true;
        }
        require(caught, "exception cancellation");
        o.after_pop = {};
        o.max_labels = 1;
        caught = false;
        try {
            search(g, b, 0, 2, o);
        } catch (const std::runtime_error &) {
            caught = true;
        }
        require(caught, "budget reports failure");
    }
}
int main(int argc, char **argv) {
    return test_main([&] {
        bool stress = argc == 2 && std::string(argv[1]) == "--stress";
        Graph trade(4);
        trade.connect(0, 1, {1, 9});
        trade.connect(1, 3, {1, 9});
        trade.connect(0, 2, {9, 1});
        trade.connect(2, 3, {9, 1});
        trade.connect(0, 3, {12, 12});
        compare(trade, stress);
        Graph single(1);
        compare(single, stress);
        Graph unreachable(3);
        unreachable.connect(0, 1, {0, 0});
        unreachable.connect(1, 0, {0, 0});
        compare(unreachable, stress);
        for (std::uint64_t seed = 1; seed <= (stress ? 60U : 15U); ++seed) {
            Graph g(6);
            auto r = seed;
            for (std::size_t u = 0; u < 6; ++u)
                for (std::size_t v = 0; v < 6; ++v)
                    if (rng(r) % 100 < 30)
                        g.connect(u, v, {rng(r) % 10, rng(r) % 10});
            compare(g, false);
        }
        in_flight();
        require(heuristic_value({99, 81}, Heuristic::uncertain, 0) == Cost{49, 40},
                "uncertainty lower bound");
        require(heuristic_value({99, 81}, Heuristic::dynamic, 1) == Cost{24, 20}, "dynamic epoch");
        bool caught = false;
        try {
            add(infinity - 1, 1);
        } catch (const std::overflow_error &) {
            caught = true;
        }
        require(caught, "checked cost overflow");
    });
}
