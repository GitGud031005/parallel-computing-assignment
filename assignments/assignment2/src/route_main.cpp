#include "pc/a2/cli.hpp"
#include "pc/a2/search.hpp"
#include <chrono>
#include <sstream>
using namespace pc::a2;
int main(int argc, char **argv) {
    try {
        auto start = std::chrono::steady_clock::now();
        Options o(argc, argv,
                  {"graph", "engine", "heuristic", "objective", "threads", "source", "target",
                   "source-osm-id", "target-osm-id", "source-lat", "source-lon", "target-lat",
                   "target-lon", "dynamic-period", "max-labels", "output"});
        if (o.has("help")) {
            std::cout << "a2_route --graph FILE --engine sequential|coarse|fine --heuristic "
                         "zero|landmark|dynamic|uncertain --objective distance|time|pareto "
                         "--threads P [--source INDEX --target INDEX | --source-osm-id ID "
                         "--target-osm-id ID | --source-lat LAT --source-lon LON --target-lat LAT "
                         "--target-lon LON] [--dynamic-period K --max-labels K --output JSON]\n";
            return 0;
        }
        auto g = Graph::read(o.text("graph"));
        auto loaded = std::chrono::steady_clock::now();
        auto endpoint = [&](const std::string &name, std::size_t fallback) {
            bool gps = o.has(name + "-lat") || o.has(name + "-lon");
            int modes = static_cast<int>(o.has(name)) + static_cast<int>(o.has(name + "-osm-id")) +
                        static_cast<int>(gps);
            if (modes > 1 || (gps && (!o.has(name + "-lat") || !o.has(name + "-lon"))))
                throw std::invalid_argument("conflicting/incomplete endpoint: " + name);
            if (gps)
                return g.nearest(o.real(name + "-lat"), o.real(name + "-lon"));
            if (o.has(name + "-osm-id"))
                return g.osm_index(o.number(name + "-osm-id", 0, true));
            return static_cast<std::size_t>(o.number(name, fallback, true));
        };
        auto source = endpoint("source", 0), target = endpoint("target", g.vertices.size() - 1);
        SearchOptions options;
        options.engine = o.text("engine", "sequential");
        auto heuristic = o.text("heuristic", "landmark"),
             objective = o.text("objective", "distance");
        options.heuristic = heuristic_from_string(heuristic);
        options.objective = objective_from_string(objective);
        options.threads = o.number("threads", 1);
        options.dynamic_period = o.number("dynamic-period", 64);
        options.max_labels = o.number("max-labels", 1000000);
        if (options.threads > 1024)
            throw std::invalid_argument("threads exceeds 1024");
        LandmarkBounds bounds(g);
        auto preprocessed = std::chrono::steady_clock::now();
        auto result = search(g, bounds, source, target, options);
        auto end = std::chrono::steady_clock::now();
        auto ns = [](auto a, auto b) {
            return std::chrono::duration_cast<std::chrono::nanoseconds>(b - a).count();
        };
        std::ostringstream out;
        out << "{\"suite\":\"routes\",\"engine\":\"" << options.engine << "\",\"heuristic\":\""
            << heuristic << "\",\"objective\":\"" << objective
            << "\",\"threads\":" << options.threads << ",\"vertices\":" << g.vertices.size()
            << ",\"edges\":" << g.edge_count << ",\"source\":" << source << ",\"target\":" << target
            << ",\"dynamic_period\":" << options.dynamic_period
            << ",\"max_labels\":" << options.max_labels
            << ",\"load_elapsed_ns\":" << ns(start, loaded)
            << ",\"preprocess_elapsed_ns\":" << ns(loaded, preprocessed)
            << ",\"query_elapsed_ns\":" << ns(preprocessed, end)
            << ",\"end_to_end_ns\":" << ns(start, end) << ",\"generated\":" << result.generated
            << ",\"expanded\":" << result.expanded << ",\"stale\":" << result.stale
            << ",\"pruned\":" << result.pruned << ",\"max_epoch\":" << result.max_epoch
            << ",\"paths\":[";
        bool first = true;
        for (const auto &p : result.paths) {
            if (!first)
                out << ',';
            first = false;
            out << "{\"cost\":[" << p.cost[0] << ',' << p.cost[1] << "],\"vertices\":[";
            for (std::size_t i = 0; i < p.vertices.size(); ++i) {
                if (i)
                    out << ',';
                out << p.vertices[i];
            }
            out << "],\"edge_ids\":[";
            for (std::size_t i = 0; i < p.edge_ids.size(); ++i) {
                if (i)
                    out << ',';
                out << p.edge_ids[i];
            }
            out << "]}";
        }
        out << ']';
        build_fields(out);
        out << '}';
        o.emit(out.str());
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
