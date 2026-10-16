#pragma once
#include "pc/a2/graph.hpp"
#include <functional>
#include <string>
namespace pc::a2 {
enum class Heuristic { zero, landmark, dynamic, uncertain };
Heuristic heuristic_from_string(const std::string &value);
Cost heuristic_value(Cost certified, Heuristic policy, std::uint64_t epoch);
struct SearchOptions {
    std::string engine = "sequential"; // sequential | coarse | fine
    Objective objective = Objective::distance;
    Heuristic heuristic = Heuristic::landmark;
    std::size_t threads = 1;
    std::uint64_t dynamic_period = 64, max_labels = 1000000;
    std::function<void(std::size_t)> after_pop; // Empty outside directed tests.
};
struct Path {
    Cost cost;
    std::vector<std::size_t> vertices, edge_ids;
};
struct SearchResult {
    std::vector<Path> paths;
    std::uint64_t generated = 0, expanded = 0, stale = 0, pruned = 0, max_epoch = 0;
};
SearchResult search(const Graph &graph, const LandmarkBounds &bounds, std::size_t source,
                    std::size_t target, const SearchOptions &options = {});
void validate_path(const Graph &graph, const Path &path, std::size_t source, std::size_t target);
} // namespace pc::a2
