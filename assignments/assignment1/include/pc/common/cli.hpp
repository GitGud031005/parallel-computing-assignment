#pragma once
#include <charconv>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include "pc/common/worker_harness.hpp"
#include "pc/common/build_info.hpp"

namespace pc {
inline std::uint64_t checked_mul(std::uint64_t a, std::uint64_t b) {
    if (b && a > std::numeric_limits<std::uint64_t>::max() / b)
        throw std::invalid_argument("workload multiplication overflows uint64_t");
    return a * b;
}
inline std::uint64_t checked_add(std::uint64_t a, std::uint64_t b) {
    if (a > std::numeric_limits<std::uint64_t>::max() - b)
        throw std::invalid_argument("workload addition overflows uint64_t");
    return a + b;
}
class Options {
    std::map<std::string, std::string> values_;
public:
    Options(int argc, char** argv, std::initializer_list<std::string> allowed) {
        const std::set<std::string> names(allowed);
        for (int i = 1; i < argc; ++i) {
            std::string key(argv[i]);
            if (key == "--help") { values_["help"] = "1"; continue; }
            if (key.size() < 3 || key.substr(0, 2) != "--") throw std::invalid_argument("expected --option value");
            key.erase(0, 2);
            if (!names.contains(key)) throw std::invalid_argument("unknown option: " + key);
            if (values_.contains(key)) throw std::invalid_argument("duplicate option: " + key);
            if (++i >= argc) throw std::invalid_argument("missing value: " + key);
            values_[key] = argv[i];
        }
    }
    bool has(const std::string& key) const { return values_.contains(key); }
    std::string text(const std::string& key, const std::string& fallback = "") const {
        auto found = values_.find(key);
        return found == values_.end() ? fallback : found->second;
    }
    std::uint64_t number(const std::string& key, std::uint64_t fallback, bool zero = false) const {
        auto raw = text(key, std::to_string(fallback));
        std::uint64_t value = 0;
        auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), value);
        if (parsed.ec != std::errc{} || parsed.ptr != raw.data() + raw.size() || (!zero && value == 0))
            throw std::invalid_argument("invalid unsigned integer: " + key);
        return value;
    }
    std::size_t threads() const {
        auto count = number("threads", 1);
        if (count > 1024) throw std::invalid_argument("threads exceeds resource limit 1024");
        return static_cast<std::size_t>(count);
    }
};
struct Result {
    std::string suite, implementation, mode;
    std::size_t threads = 1;
    std::optional<std::uint64_t> iterations, total, episodes, prime_n, outside_work, checksum, final_value;
    RunTiming timing{};
    bool backoff = false;
};
inline void emit_result(const Options& options, const Result& r) {
    std::ostringstream out;
    out << "{\"suite\":\"" << r.suite << "\",\"implementation\":\"" << r.implementation
        << "\",\"mode\":\"" << r.mode << "\",\"threads\":" << r.threads;
    auto field = [&](std::string_view name, std::optional<std::uint64_t> value) {
        out << ",\"" << name << "\":";
        if (value) out << *value; else out << "null";
    };
    field("iterations_per_thread", r.iterations); field("total_operations", r.total);
    field("episodes", r.episodes); field("prime_n", r.prime_n); field("outside_work", r.outside_work);
    field("checksum", r.checksum); field("final_value", r.final_value);
    out << ",\"program_elapsed_ns\":" << r.timing.program_ns
        << ",\"worker_elapsed_ns\":" << r.timing.worker_ns
        << ",\"backoff_policy\":\"" << (r.backoff ? "pause_exponential" : "none")
        << "\",\"backoff_initial\":" << (r.backoff ? 1 : 0)
        << ",\"backoff_max\":" << (r.backoff ? 1024 : 0)
        << ",\"source_sha256\":\"" << PC_SOURCE_SHA256
        << "\",\"build_type\":\"" << PC_BUILD_TYPE
        << "\",\"sanitizer\":\"" << PC_SANITIZER_NAME << "\"}\n";
    if (options.has("output")) {
        std::ofstream file(options.text("output"));
        if (!file) throw std::runtime_error("cannot open output file");
        file << out.str();
        if (!file) throw std::runtime_error("cannot write output file");
    } else std::cout << out.str();
}
} // namespace pc
