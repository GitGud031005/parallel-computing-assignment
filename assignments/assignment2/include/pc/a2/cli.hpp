#pragma once
#include <charconv>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#ifndef PC_A2_SOURCE_SHA256
#define PC_A2_SOURCE_SHA256 "unconfigured"
#endif
#ifndef PC_A2_BUILD_TYPE
#define PC_A2_BUILD_TYPE "unknown"
#endif
#ifndef PC_A2_SANITIZER
#define PC_A2_SANITIZER "unknown"
#endif
namespace pc::a2 {
class Options {
    std::map<std::string, std::string> values_;

  public:
    Options(int argc, char **argv, std::initializer_list<std::string> allowed) {
        std::set<std::string> names(allowed);
        for (int i = 1; i < argc; ++i) {
            std::string name = argv[i];
            if (name == "--help") {
                values_["help"] = "1";
                continue;
            }
            if (!name.starts_with("--"))
                throw std::invalid_argument("expected --option value");
            name.erase(0, 2);
            if (!names.contains(name) || values_.contains(name) || ++i >= argc)
                throw std::invalid_argument("unknown/duplicate/missing option: " + name);
            values_[name] = argv[i];
        }
    }
    bool has(const std::string &key) const { return values_.contains(key); }
    std::string text(const std::string &key, const std::string &fallback = "") const {
        auto it = values_.find(key);
        return it == values_.end() ? fallback : it->second;
    }
    std::uint64_t number(const std::string &key, std::uint64_t fallback, bool zero = false) const {
        auto raw = text(key, std::to_string(fallback));
        std::uint64_t n = 0;
        auto r = std::from_chars(raw.data(), raw.data() + raw.size(), n);
        if (r.ec != std::errc{} || r.ptr != raw.data() + raw.size() || (!zero && n == 0))
            throw std::invalid_argument("invalid number: " + key);
        return n;
    }
    double real(const std::string &key) const {
        auto raw = text(key);
        double x = 0;
        auto r = std::from_chars(raw.data(), raw.data() + raw.size(), x);
        if (r.ec != std::errc{} || r.ptr != raw.data() + raw.size() || !std::isfinite(x))
            throw std::invalid_argument("invalid coordinate: " + key);
        return x;
    }
    void emit(const std::string &json) const {
        if (!has("output")) {
            std::cout << json << '\n';
            return;
        }
        std::ofstream out(text("output"));
        out << json << '\n';
        if (!out)
            throw std::runtime_error("cannot write JSON output");
    }
};
inline void build_fields(std::ostream &out) {
    out << ",\"source_sha256\":\"" << PC_A2_SOURCE_SHA256 << "\",\"build_type\":\""
        << PC_A2_BUILD_TYPE << "\",\"sanitizer\":\"" << PC_A2_SANITIZER << '"';
}
} // namespace pc::a2
