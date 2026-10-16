#include "pc/a2/search.hpp"
#include "pc/a2/sorted_list.hpp"
#include "pc/a2/workers.hpp"
#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <memory>
#include <mutex>
#include <queue>
#include <stdexcept>
#include <tuple>
namespace pc::a2 {
Heuristic heuristic_from_string(const std::string &v) {
    if (v == "zero")
        return Heuristic::zero;
    if (v == "landmark")
        return Heuristic::landmark;
    if (v == "dynamic")
        return Heuristic::dynamic;
    if (v == "uncertain")
        return Heuristic::uncertain;
    throw std::invalid_argument("heuristic must be zero|landmark|dynamic|uncertain");
}
Cost heuristic_value(Cost h, Heuristic policy, std::uint64_t epoch) {
    if (policy == Heuristic::zero)
        return {0, 0};
    // Integer floors preserve a certified lower bound. No floating-point admissibility assumptions.
    auto scale = [](Weight x, Weight numerator, Weight denominator) {
        return x / denominator * numerator + (x % denominator) * numerator / denominator;
    };
    if (policy == Heuristic::dynamic) {
        constexpr Weight numerators[] = {4, 1, 3, 2};
        for (auto &x : h)
            x = scale(x, numerators[epoch % 4], 4);
    } else if (policy == Heuristic::uncertain) {
        // Estimate band [floor(L/2), ceil(3L/2)]; ONLY the certified lower end is used.
        for (auto &x : h)
            x /= 2;
    }
    return h;
}
namespace {
struct Label {
    const std::size_t vertex;
    const Cost cost;
    const std::shared_ptr<const Label> parent;
    const std::size_t edge_id;
    std::atomic<bool> alive{true};
    Label(std::size_t v, Cost g, std::shared_ptr<const Label> p, std::size_t edge)
        : vertex(v), cost(g), parent(std::move(p)), edge_id(edge) {}
};
using LabelPtr = std::shared_ptr<Label>;
struct Task {
    Cost key{0, 0};
    std::uint64_t ticket = 0, epoch = 0;
    LabelPtr label;
};
struct TaskLess {
    bool operator()(const Task &a, const Task &b) const {
        return std::tie(a.key, a.ticket) < std::tie(b.key, b.ticket);
    }
};
class Heap {
    struct Greater {
        bool operator()(const Task &a, const Task &b) const { return TaskLess{}(b, a); }
    };
    std::priority_queue<Task, std::vector<Task>, Greater> queue_;

  public:
    bool insert(const Task &t) {
        queue_.push(t);
        return true;
    }
    bool try_pop_min(Task &t) {
        if (queue_.empty())
            return false;
        t = queue_.top();
        queue_.pop();
        return true;
    }
};
// Waiting coordination does not wrap insert/pop: concurrent list operations remain concurrent.
template <class Queue> class WorkPool {
    Queue queue_;
    std::atomic<std::uint64_t> outstanding_{
        0}; // queued + being expanded + reserved-before-publication
    std::atomic<bool> cancelled_{false};
    std::mutex wait_mutex_;
    std::condition_variable changed_;
    std::uint64_t version_ = 0;
    void signal(bool all) {
        {
            std::lock_guard lock(wait_mutex_);
            ++version_;
        }
        if (all)
            changed_.notify_all();
        else
            changed_.notify_one();
    }

  public:
    void push(const Task &task) {
        outstanding_.fetch_add(1, std::memory_order_acq_rel); // Reserve BEFORE making task visible.
        try {
            if (!queue_.insert(task))
                throw std::logic_error("priority ticket collision");
        } catch (...) {
            cancel();
            throw;
        }
        signal(false);
    }
    bool pop(Task &task) {
        for (;;) {
            std::uint64_t observed;
            {
                std::lock_guard lock(wait_mutex_);
                observed = version_;
            }
            if (cancelled_.load(std::memory_order_acquire))
                return false;
            if (queue_.try_pop_min(task))
                return true;
            std::unique_lock lock(wait_mutex_);
            changed_.wait(lock, [&] {
                return cancelled_.load() || outstanding_.load() == 0 || version_ != observed;
            });
            if (cancelled_.load() || outstanding_.load() == 0)
                return false;
        }
    }
    void complete() {
        if (outstanding_.fetch_sub(1, std::memory_order_acq_rel) == 1)
            signal(true);
    }
    void cancel() {
        cancelled_.store(true, std::memory_order_release);
        signal(true);
    }
};
struct State {
    std::mutex mutex;
    std::vector<LabelPtr> labels;
};
class Query {
    const Graph &graph_;
    const LandmarkBounds &bounds_;
    std::size_t source_, target_;
    const SearchOptions &options_;
    std::unique_ptr<State[]> states_;
    std::mutex goals_mutex_;
    std::vector<LabelPtr> goals_;
    std::atomic<std::uint64_t> generated_{0}, expanded_{0}, stale_{0}, pruned_{0}, ticket_{0},
        max_epoch_{0};
    bool bounded(Cost lower) {
        std::lock_guard lock(goals_mutex_);
        for (const auto &g : goals_)
            if (dominates(g->cost, lower, options_.objective))
                return true;
        return false;
    }
    void goal(const LabelPtr &label) {
        std::lock_guard lock(goals_mutex_);
        for (const auto &g : goals_)
            if (dominates(g->cost, label->cost, options_.objective))
                return;
        std::erase_if(goals_, [&](const auto &g) {
            return dominates(label->cost, g->cost, options_.objective);
        });
        goals_.push_back(label);
    }
    LabelPtr accept(std::size_t vertex, Cost g, std::shared_ptr<const Label> parent,
                    std::size_t edge_id) {
        auto &state = states_[vertex];
        std::lock_guard lock(state.mutex);
        for (const auto &l : state.labels)
            if (dominates(l->cost, g, options_.objective))
                return {};
        auto label = std::make_shared<Label>(vertex, g, std::move(parent), edge_id);
        auto previous = generated_.fetch_add(1);
        if (previous >= options_.max_labels)
            throw std::runtime_error("label budget exhausted; no exact result returned");
        std::erase_if(state.labels, [&](const auto &l) {
            if (dominates(g, l->cost, options_.objective)) {
                l->alive.store(false, std::memory_order_release);
                return true;
            }
            return false;
        });
        state.labels.push_back(label);
        return label;
    }
    Task task(LabelPtr label) {
        auto ticket = ticket_.fetch_add(1);
        auto epoch = ticket / options_.dynamic_period;
        auto previous = max_epoch_.load();
        while (previous < epoch && !max_epoch_.compare_exchange_weak(previous, epoch)) {
        }
        auto h =
            heuristic_value(bounds_.estimate(label->vertex, target_), options_.heuristic, epoch);
        auto key = add(label->cost, h);
        if (options_.objective == Objective::distance)
            key = {key[0], 0};
        if (options_.objective == Objective::time)
            key = {key[1], 0};
        return {key, ticket, epoch, std::move(label)};
    }
    template <class Push> void expand(const Task &t, Push &&push) {
        const auto &label = t.label;
        if (options_.after_pop)
            options_.after_pop(label->vertex);
        if (!label->alive.load(std::memory_order_acquire)) {
            ++stale_;
            return;
        }
        auto lower = add(label->cost, heuristic_value(bounds_.estimate(label->vertex, target_),
                                                      options_.heuristic, t.epoch));
        if (bounded(lower)) {
            ++pruned_;
            return;
        }
        if (label->vertex == target_) {
            goal(label);
            return;
        }
        ++expanded_;
        for (const auto &edge : graph_.edges[label->vertex]) {
            auto g = add(label->cost, edge.cost);
            auto safe_lower = add(g, heuristic_value(bounds_.estimate(edge.to, target_),
                                                     options_.heuristic, t.epoch));
            if (bounded(safe_lower)) {
                ++pruned_;
                continue;
            }
            auto next = accept(edge.to, g, label, edge.id);
            if (next)
                push(task(std::move(next)));
        }
    }
    SearchResult result() {
        SearchResult r;
        r.generated = generated_.load();
        r.expanded = expanded_.load();
        r.stale = stale_.load();
        r.pruned = pruned_.load();
        r.max_epoch = max_epoch_.load();
        for (const auto &label : goals_) {
            Path p;
            p.cost = label->cost;
            for (std::shared_ptr<const Label> l = label; l; l = l->parent) {
                p.vertices.push_back(l->vertex);
                if (l->parent)
                    p.edge_ids.push_back(l->edge_id);
            }
            std::reverse(p.vertices.begin(), p.vertices.end());
            std::reverse(p.edge_ids.begin(), p.edge_ids.end());
            validate_path(graph_, p, source_, target_);
            r.paths.push_back(std::move(p));
        }
        std::sort(r.paths.begin(), r.paths.end(),
                  [](const auto &a, const auto &b) { return a.cost < b.cost; });
        return r;
    }

  public:
    Query(const Graph &g, const LandmarkBounds &b, std::size_t s, std::size_t t,
          const SearchOptions &o)
        : graph_(g), bounds_(b), source_(s), target_(t), options_(o),
          states_(std::make_unique<State[]>(g.vertices.size())) {}
    SearchResult sequential() {
        Heap queue;
        queue.insert(task(accept(source_, {0, 0}, {}, 0)));
        Task t;
        while (queue.try_pop_min(t))
            expand(t, [&](const auto &x) { queue.insert(x); });
        return result();
    }
    template <class Queue> SearchResult parallel() {
        WorkPool<Queue> pool;
        pool.push(task(accept(source_, {0, 0}, {}, 0)));
        try {
            workers(options_.threads, [&](std::size_t) {
                try {
                    Task t;
                    while (pool.pop(t)) {
                        expand(t, [&](const auto &x) { pool.push(x); });
                        pool.complete();
                    }
                } catch (...) {
                    pool.cancel();
                    throw;
                }
            });
        } catch (...) {
            pool.cancel();
            throw;
        }
        return result();
    }
};
} // namespace
SearchResult search(const Graph &g, const LandmarkBounds &b, std::size_t s, std::size_t t,
                    const SearchOptions &o) {
    if (g.vertices.empty() || s >= g.vertices.size() || t >= g.vertices.size() || o.threads == 0 ||
        o.threads > 1024 || o.dynamic_period == 0 || o.max_labels == 0)
        throw std::invalid_argument("invalid query/options");
    Query query(g, b, s, t, o);
    if (o.engine == "sequential") {
        if (o.threads != 1)
            throw std::invalid_argument("sequential requires one thread");
        return query.sequential();
    }
    if (o.engine == "coarse")
        return query.parallel<CoarseList<Task, TaskLess>>();
    if (o.engine == "fine")
        return query.parallel<FineList<Task, TaskLess>>();
    throw std::invalid_argument("engine must be sequential|coarse|fine");
}
void validate_path(const Graph &g, const Path &p, std::size_t source, std::size_t target) {
    if (p.vertices.empty() || p.vertices.front() != source || p.vertices.back() != target ||
        p.edge_ids.size() + 1 != p.vertices.size())
        throw std::runtime_error("invalid path endpoints/length");
    Cost sum{0, 0};
    for (std::size_t i = 0; i < p.edge_ids.size(); ++i) {
        if (p.vertices[i] >= g.edges.size())
            throw std::runtime_error("invalid path vertex");
        const auto &edges = g.edges[p.vertices[i]];
        auto e = std::find_if(edges.begin(), edges.end(), [&](const auto &edge) {
            return edge.id == p.edge_ids[i] && edge.to == p.vertices[i + 1];
        });
        if (e == edges.end())
            throw std::runtime_error("invalid path edge");
        sum = add(sum, e->cost);
    }
    if (sum != p.cost)
        throw std::runtime_error("path cost does not match edges");
}
} // namespace pc::a2
