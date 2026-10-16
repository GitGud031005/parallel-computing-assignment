#pragma once
#include <functional>
#include <memory>
#include <mutex>
#include <optional>
#include <utility>
#include <vector>

namespace pc::a2 {
// No exposed node pointers. Destruction/snapshot require all workers to have joined.
template <class T, class Less = std::less<T>> class CoarseList {
    struct Node {
        T value;
        std::unique_ptr<Node> next;
        explicit Node(T v) : value(std::move(v)) {}
    };
    std::unique_ptr<Node> first_;
    std::mutex mutex_;
    Less less_;
    bool equal(const T &a, const T &b) const { return !less_(a, b) && !less_(b, a); }

  public:
    CoarseList() = default;
    CoarseList(const CoarseList &) = delete;
    ~CoarseList() {
        while (first_) {
            auto next = std::move(first_->next);
            first_ = std::move(next);
        }
    }
    bool insert(const T &value) {
        auto node = std::make_unique<Node>(value);
        std::lock_guard lock(mutex_);
        auto *link = &first_;
        while (*link && less_((*link)->value, value))
            link = &(*link)->next;
        if (*link && equal((*link)->value, value))
            return false;
        node->next = std::move(*link);
        *link = std::move(node);
        return true;
    }
    bool erase(const T &value) {
        std::lock_guard lock(mutex_);
        auto *link = &first_;
        while (*link && less_((*link)->value, value))
            link = &(*link)->next;
        if (!*link || !equal((*link)->value, value))
            return false;
        auto victim = std::move(*link);
        *link = std::move(victim->next);
        return true;
    }
    bool contains(const T &value) {
        std::lock_guard lock(mutex_);
        auto *node = first_.get();
        while (node && less_(node->value, value))
            node = node->next.get();
        return node && equal(node->value, value);
    }
    bool try_pop_min(T &value) {
        std::lock_guard lock(mutex_);
        if (!first_)
            return false;
        value = first_->value;
        auto victim = std::move(first_);
        first_ = std::move(victim->next);
        return true;
    }
    std::vector<T> snapshot_after_join() const {
        std::vector<T> out;
        for (auto *p = first_.get(); p; p = p->next.get())
            out.push_back(p->value);
        return out;
    }
};

template <class T, class Less = std::less<T>> class FineList {
    struct Node {
        std::optional<T> value;
        std::unique_ptr<Node> next;
        std::mutex mutex;
        Node() = default;
        explicit Node(const T &v) : value(v) {}
    };
    Node head_; // Structural sentinel, so every value of T (incl. INT64_MIN/MAX) is legal.
    Less less_;
    bool equal(const T &a, const T &b) const { return !less_(a, b) && !less_(b, a); }
    struct Window {
        Node *predecessor;
        Node *current;
        std::unique_lock<std::mutex> previous_lock, current_lock;
    };
    Window locate(const T &value) {
        Node *pred = &head_;
        std::unique_lock previous(pred->mutex);
        Node *curr = pred->next.get();
        std::unique_lock<std::mutex> current;
        if (curr)
            current = std::unique_lock(curr->mutex);
        while (curr && less_(*curr->value, value)) {
            // Hold curr until its successor has been locked: no unprotected pointer gap.
            previous.unlock();
            pred = curr;
            previous = std::move(current);
            curr = pred->next.get();
            if (curr)
                current = std::unique_lock(curr->mutex);
        }
        return {pred, curr, std::move(previous), std::move(current)};
    }

  public:
    FineList() = default;
    FineList(const FineList &) = delete;
    ~FineList() {
        while (head_.next) {
            auto next = std::move(head_.next->next);
            head_.next = std::move(next);
        }
    }
    bool insert(const T &value) {
        auto node = std::make_unique<Node>(value);
        auto w = locate(value);
        if (w.current && equal(*w.current->value, value))
            return false;
        node->next = std::move(w.predecessor->next);
        w.predecessor->next = std::move(node);
        return true;
    }
    bool erase(const T &value) {
        auto w = locate(value);
        if (!w.current || !equal(*w.current->value, value))
            return false;
        auto victim = std::move(w.predecessor->next);
        w.predecessor->next = std::move(victim->next);
        // Unlock before destroying this mutex. The predecessor lock excludes new readers.
        w.current_lock.unlock();
        victim.reset();
        return true;
    }
    bool contains(const T &value) {
        auto w = locate(value);
        return w.current && equal(*w.current->value, value);
    }
    bool try_pop_min(T &value) {
        std::unique_lock previous(head_.mutex);
        auto *curr = head_.next.get();
        if (!curr)
            return false;
        std::unique_lock current(curr->mutex);
        value = *curr->value;
        auto victim = std::move(head_.next);
        head_.next = std::move(victim->next);
        current.unlock();
        victim.reset();
        return true;
    }
    std::vector<T> snapshot_after_join() const {
        std::vector<T> out;
        for (auto *p = head_.next.get(); p; p = p->next.get())
            out.push_back(*p->value);
        return out;
    }
};
} // namespace pc::a2
