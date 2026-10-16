"""Create exact scientific figures from a validated Ass2 summary and actual road graph."""

import argparse, csv, json
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from oracle import read_graph

COLORS = {"sequential": "#334155", "coarse": "#0284c7", "fine": "#ea580c"}


def plots(run_dir, processed, output):
    validation = json.loads((processed / "validation.json").read_text())
    if not validation["complete"] or not validation["quality_exact"]:
        raise ValueError("validated complete input required")
    rows = list(csv.DictReader((processed / "summary.csv").open()))
    for row in rows:
        for key in ["threads", "median_ms", "q1_ms", "q3_ms"]:
            row[key] = float(row[key])
    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update(
        {"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 160}
    )
    query = next(r["query"] for r in rows if r["suite"] == "routes")
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
    for ax, objective in zip(axes, ["distance", "time", "pareto"]):
        for engine in COLORS:
            selected = sorted(
                [
                    r
                    for r in rows
                    if r["suite"] == "routes"
                    and r["query"] == query
                    and r["objective"] == objective
                    and r["heuristic"] == "landmark"
                    and r["engine"] == engine
                ],
                key=lambda r: r["threads"],
            )
            if not selected:
                continue
            if engine == "sequential":
                ax.axhline(
                    selected[0]["median_ms"], color=COLORS[engine], ls="--", label="Sequential heap"
                )
            else:
                ax.errorbar(
                    [r["threads"] for r in selected],
                    [r["median_ms"] for r in selected],
                    yerr=[
                        [r["median_ms"] - r["q1_ms"] for r in selected],
                        [r["q3_ms"] - r["median_ms"] for r in selected],
                    ],
                    fmt="o-",
                    capsize=3,
                    color=COLORS[engine],
                    label=engine,
                )
        ax.set(title=objective, xlabel="Workers", ylabel="Query time (ms)")
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Road query {query}; landmark heuristic; median and IQR", fontsize=12)
    fig.tight_layout()
    fig.savefig(output / "routes.png")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    for ax, mix in zip(axes, ["read_heavy", "update_heavy"]):
        for engine in ["coarse", "fine"]:
            for key_range in sorted(
                {r["key_range"] for r in rows if r["suite"] == "sets"}, key=int
            ):
                selected = sorted(
                    [
                        r
                        for r in rows
                        if r["suite"] == "sets"
                        and r["mix"] == mix
                        and r["engine"] == engine
                        and r["key_range"] == key_range
                    ],
                    key=lambda r: r["threads"],
                )
                ax.plot(
                    [r["threads"] for r in selected],
                    [r["median_ms"] for r in selected],
                    "o-" if key_range == "64" else "s--",
                    color=COLORS[engine],
                    label=f"{engine}, keys={key_range}",
                )
        ax.set(title=mix, xlabel="Workers", ylabel="Program time (ms)")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle("Concurrent sorted sets; fixed total operations; median", fontsize=12)
    fig.tight_layout()
    fig.savefig(output / "sets.png")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 3.4))
    policies = ["zero", "landmark", "dynamic", "uncertain"]
    for i, engine in enumerate(COLORS):
        selected = []
        for h in policies:
            options = [
                r
                for r in rows
                if r["suite"] == "routes"
                and r["query"] == query
                and r["objective"] == "pareto"
                and r["heuristic"] == h
                and r["engine"] == engine
            ]
            selected.append(max(options, key=lambda r: r["threads"]))
        ax.bar(
            [x + (i - 1) * 0.24 for x in range(4)],
            [r["median_ms"] for r in selected],
            width=0.24,
            color=COLORS[engine],
            label=f"{engine}, P={int(selected[0]['threads'])}",
        )
    ax.set(
        xticks=range(4),
        xticklabels=policies,
        ylabel="Query time (ms)",
        title=f"Pareto query {query}; heuristic policies",
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "heuristics.png")
    plt.close(fig)
    manifest = json.loads((run_dir / "manifest.json").read_text())
    nodes, edges = read_graph(run_dir / "network.road")
    example = None
    for line in (run_dir / "raw.jsonl").read_text().splitlines():
        row = json.loads(line)
        sample = row.get("sample", {})
        if (
            sample.get("objective") == "pareto"
            and sample.get("engine") == "sequential"
            and sample.get("heuristic") == "landmark"
        ):
            example = sample
            break
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for u, row in enumerate(edges):
        for v, _, _ in row:
            ax.plot(
                [nodes[u][2], nodes[v][2]],
                [nodes[u][1], nodes[v][1]],
                color="#cbd5e1",
                lw=0.45,
                zorder=1,
            )
    for i, path in enumerate(example["paths"]):
        vs = path["vertices"]
        cost = path["cost"]
        ax.plot(
            [nodes[v][2] for v in vs],
            [nodes[v][1] for v in vs],
            lw=1.6,
            label=f"{cost[0]/1e6:.3f} km, {cost[1]/60000:.2f} min",
        )
    ax.set(
        xlabel="Longitude",
        ylabel="Latitude",
        title="One real-road query: nondominated routes in the modeled network",
    )
    ax.legend(fontsize=8, loc="best")
    ax.ticklabel_format(useOffset=False)
    fig.text(
        0.5,
        0.005,
        "© OpenStreetMap contributors | ODbL | openstreetmap.org/copyright",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(output / "road_routes.png")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    costs = sorted(tuple(p["cost"]) for p in example["paths"])
    ax.plot([c[0] / 1e6 for c in costs], [c[1] / 60000 for c in costs], "o-", color="#0284c7")
    ax.set(
        xlabel="Distance (km)",
        ylabel="Estimated travel time (min)",
        title="Exact Pareto cost vectors; static road-class time model",
    )
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output / "pareto.png")
    plt.close(fig)
    print(json.dumps({"figures": 5, "output": str(output.resolve())}))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["run-dir", "processed", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    plots(a.run_dir, a.processed, a.output)
