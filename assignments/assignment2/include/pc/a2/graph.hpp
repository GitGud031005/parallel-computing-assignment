#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <limits>
#include <string>
#include <vector>
namespace pc::a2 {
using Weight = std::uint64_t;
inline constexpr Weight infinity = std::numeric_limits<Weight>::max() / 4;
using Cost = std::array<Weight, 2>; // millimetres, estimated milliseconds
Weight add(Weight a, Weight b);
Cost add(Cost a, Cost b);
enum class Objective { distance, time, pareto };
Objective objective_from_string(const std::string &value);
bool dominates(Cost a, Cost b, Objective objective); // weak dominance includes equality
struct Edge {
    std::size_t to;
    Cost cost;
    std::size_t id;
};
struct Vertex {
    std::uint64_t osm_id;
    double latitude, longitude;
};
struct Graph {
    std::vector<Vertex> vertices;
    std::vector<std::vector<Edge>> edges;
    std::size_t edge_count = 0;
    explicit Graph(std::size_t n = 0);
    void connect(std::size_t from, std::size_t to, Cost cost);
    static Graph read(const std::filesystem::path &path);
    std::size_t nearest(double latitude, double longitude) const;
    std::size_t osm_index(std::uint64_t id) const;
};
std::vector<Weight> dijkstra(const Graph &graph, std::size_t source, std::size_t component,
                             bool reverse = false);
class LandmarkBounds {
    struct Table {
        std::array<std::vector<Weight>, 2> forward, reverse;
    };
    std::vector<Table> tables_;

  public:
    explicit LandmarkBounds(const Graph &graph, std::size_t count = 2);
    Cost estimate(std::size_t vertex, std::size_t target) const;
};
} // namespace pc::a2
