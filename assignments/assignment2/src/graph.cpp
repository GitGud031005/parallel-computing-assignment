#include "pc/a2/graph.hpp"
#include <algorithm>
#include <charconv>
#include <cmath>
#include <fstream>
#include <queue>
#include <set>
#include <stdexcept>
namespace pc::a2 {
Weight add(Weight a, Weight b) {
    if (a >= infinity || b >= infinity || a > infinity - 1 - b)
        throw std::overflow_error("cost exceeds finite integer domain");
    return a + b;
}
Cost add(Cost a, Cost b) { return {add(a[0], b[0]), add(a[1], b[1])}; }
Objective objective_from_string(const std::string &v) {
    if (v == "distance")
        return Objective::distance;
    if (v == "time")
        return Objective::time;
    if (v == "pareto")
        return Objective::pareto;
    throw std::invalid_argument("objective must be distance|time|pareto");
}
bool dominates(Cost a, Cost b, Objective o) {
    if (o == Objective::distance)
        return a[0] <= b[0];
    if (o == Objective::time)
        return a[1] <= b[1];
    return a[0] <= b[0] && a[1] <= b[1];
}
Graph::Graph(std::size_t n) : vertices(n), edges(n) {
    for (std::size_t i = 0; i < n; ++i)
        vertices[i] = {i, 0, 0};
}
void Graph::connect(std::size_t from, std::size_t to, Cost cost) {
    if (from >= vertices.size() || to >= vertices.size() || cost[0] >= infinity ||
        cost[1] >= infinity)
        throw std::invalid_argument("invalid edge endpoint/cost");
    edges[from].push_back({to, cost, edge_count++});
}
static std::uint64_t integer(std::istream &input) {
    std::string text;
    if (!(input >> text))
        throw std::invalid_argument("truncated graph");
    std::uint64_t value = 0;
    auto r = std::from_chars(text.data(), text.data() + text.size(), value);
    if (r.ec != std::errc{} || r.ptr != text.data() + text.size())
        throw std::invalid_argument("invalid unsigned graph integer");
    return value;
}
Graph Graph::read(const std::filesystem::path &path) {
    std::ifstream in(path);
    std::string magic;
    if (!(in >> magic) || magic != "PCROAD1")
        throw std::invalid_argument("cannot read PCROAD1 graph");
    auto n = integer(in), m = integer(in);
    if (n == 0 || n > 2000000 || m > 20000000)
        throw std::invalid_argument("graph resource limit");
    Graph g(n);
    std::set<std::uint64_t> ids;
    for (auto &v : g.vertices) {
        v.osm_id = integer(in);
        if (!(in >> v.latitude >> v.longitude) || !std::isfinite(v.latitude) ||
            !std::isfinite(v.longitude) || std::abs(v.latitude) > 90 ||
            std::abs(v.longitude) > 180 || !ids.insert(v.osm_id).second)
            throw std::invalid_argument("invalid/duplicate graph vertex");
    }
    for (std::size_t i = 0; i < m; ++i) {
        auto u = integer(in), v = integer(in), a = integer(in), b = integer(in);
        g.connect(u, v, {a, b});
    }
    std::string extra;
    if (in >> extra)
        throw std::invalid_argument("trailing graph data");
    return g;
}
std::size_t Graph::nearest(double lat, double lon) const {
    if (vertices.empty() || !std::isfinite(lat) || !std::isfinite(lon) || std::abs(lat) > 90 ||
        std::abs(lon) > 180)
        throw std::invalid_argument("invalid coordinates");
    constexpr double pi = 3.14159265358979323846;
    auto xyz = [&](double a, double b) {
        a *= pi / 180;
        b *= pi / 180;
        return std::array<double, 3>{std::cos(a) * std::cos(b), std::cos(a) * std::sin(b),
                                     std::sin(a)};
    };
    auto p = xyz(lat, lon);
    double best = std::numeric_limits<double>::infinity();
    std::size_t found = 0;
    for (std::size_t i = 0; i < vertices.size(); ++i) {
        auto q = xyz(vertices[i].latitude, vertices[i].longitude);
        double d = 0;
        for (int k = 0; k < 3; ++k)
            d += (p[k] - q[k]) * (p[k] - q[k]);
        if (d < best) {
            best = d;
            found = i;
        }
    }
    return found;
}
std::size_t Graph::osm_index(std::uint64_t id) const {
    for (std::size_t i = 0; i < vertices.size(); ++i)
        if (vertices[i].osm_id == id)
            return i;
    throw std::invalid_argument("OSM id absent from graph");
}
std::vector<Weight> dijkstra(const Graph &graph, std::size_t source, std::size_t component,
                             bool reverse) {
    if (source >= graph.vertices.size() || component > 1)
        throw std::invalid_argument("invalid Dijkstra source/component");
    std::vector<std::vector<std::pair<std::size_t, Weight>>> adjacency(graph.vertices.size());
    for (std::size_t u = 0; u < graph.edges.size(); ++u)
        for (const auto &e : graph.edges[u])
            adjacency[reverse ? e.to : u].push_back({reverse ? u : e.to, e.cost[component]});
    std::vector<Weight> dist(adjacency.size(), infinity);
    dist[source] = 0;
    using Item = std::pair<Weight, std::size_t>;
    std::priority_queue<Item, std::vector<Item>, std::greater<Item>> q;
    q.push({0, source});
    while (!q.empty()) {
        auto [d, u] = q.top();
        q.pop();
        if (d != dist[u])
            continue;
        for (auto [v, w] : adjacency[u]) {
            auto candidate = add(d, w);
            if (candidate < dist[v]) {
                dist[v] = candidate;
                q.push({candidate, v});
            }
        }
    }
    return dist;
}
LandmarkBounds::LandmarkBounds(const Graph &graph, std::size_t count) {
    if (graph.vertices.empty() || count == 0)
        return;
    count = std::min(count, graph.vertices.size());
    for (std::size_t i = 0; i < count; ++i) {
        auto landmark = count == 1 ? 0 : i * (graph.vertices.size() - 1) / (count - 1);
        Table t;
        for (std::size_t c = 0; c < 2; ++c) {
            t.forward[c] = dijkstra(graph, landmark, c);
            t.reverse[c] = dijkstra(graph, landmark, c, true);
        }
        tables_.push_back(std::move(t));
    }
}
Cost LandmarkBounds::estimate(std::size_t v, std::size_t target) const {
    Cost bound{0, 0};
    for (const auto &t : tables_)
        for (std::size_t c = 0; c < 2; ++c) {
            auto a = t.forward[c][target], b = t.forward[c][v];
            if (a < infinity && b < infinity && a > b)
                bound[c] = std::max(bound[c], a - b);
            a = t.reverse[c][v];
            b = t.reverse[c][target];
            if (a < infinity && b < infinity && a > b)
                bound[c] = std::max(bound[c], a - b);
        }
    return bound;
}
} // namespace pc::a2
