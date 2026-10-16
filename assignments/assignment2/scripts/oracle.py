"""Independent Python FIFO label-correcting oracle, without A*, landmarks, or C++ lists."""

from collections import deque
from pathlib import Path
import heapq


def read_graph(path):
    tokens = iter(Path(path).read_text().split())
    if next(tokens) != "PCROAD1":
        raise ValueError("graph format")
    n, m = int(next(tokens)), int(next(tokens))
    vertices = []
    edges = [[] for _ in range(n)]
    for _ in range(n):
        vertices.append((int(next(tokens)), float(next(tokens)), float(next(tokens))))
    for edge_id in range(m):
        u, v, d, t = (int(next(tokens)) for _ in range(4))
        edges[u].append((v, (d, t), edge_id))
    if next(tokens, None) is not None:
        raise ValueError("trailing graph input")
    return vertices, edges


def scalar_dijkstra(edges, source, target, component):
    dist = [None] * len(edges)
    dist[source] = 0
    queue = [(0, source)]
    while queue:
        d, u = heapq.heappop(queue)
        if d != dist[u]:
            continue
        if u == target:
            return [(d,)]
        for v, w, _ in edges[u]:
            candidate = d + w[component]
            if dist[v] is None or candidate < dist[v]:
                dist[v] = candidate
                heapq.heappush(queue, (candidate, v))
    return []


def frontier(edges, source, target, objective):
    if objective in {"distance", "time"}:
        return scalar_dijkstra(edges, source, target, 0 if objective == "distance" else 1)

    def dominates(a, b):
        if objective == "distance":
            return a[0] <= b[0]
        if objective == "time":
            return a[1] <= b[1]
        return a[0] <= b[0] and a[1] <= b[1]

    labels = [set() for _ in edges]
    labels[source].add((0, 0))
    q = deque([(source, (0, 0))])
    while q:
        u, g = q.popleft()
        if g not in labels[u] or u == target:
            continue
        # A feasible goal can only prune a prefix it weakly dominates (h=0).
        if any(dominates(c, g) for c in labels[target]):
            continue
        for v, w, _ in edges[u]:
            candidate = (g[0] + w[0], g[1] + w[1])
            if any(dominates(c, candidate) for c in labels[v]):
                continue
            labels[v] = {c for c in labels[v] if not dominates(candidate, c)}
            labels[v].add(candidate)
            q.append((v, candidate))
    costs = sorted(labels[target])
    if objective == "distance":
        return sorted({(c[0],) for c in costs})
    if objective == "time":
        return sorted({(c[1],) for c in costs})
    return costs


def check_paths(edges, paths, source, target, objective, expected):
    got = []
    for p in paths:
        vs, ids = p["vertices"], p["edge_ids"]
        if not vs or vs[0] != source or vs[-1] != target or len(ids) + 1 != len(vs):
            raise ValueError("path endpoints/length")
        cost = [0, 0]
        for u, v, edge_id in zip(vs, vs[1:], ids):
            if not 0 <= u < len(edges):
                raise ValueError("path vertex")
            candidates = [w for dst, w, eid in edges[u] if dst == v and eid == edge_id]
            if len(candidates) != 1:
                raise ValueError("path edge id/direction")
            cost = [a + b for a, b in zip(cost, candidates[0])]
        if cost != p["cost"]:
            raise ValueError("path sum mismatch")
        got.append(
            (cost[0],)
            if objective == "distance"
            else (cost[1],) if objective == "time" else tuple(cost)
        )
    if sorted(got) != [tuple(x) for x in expected]:
        raise ValueError(f"quality mismatch: {got} != {expected}")
