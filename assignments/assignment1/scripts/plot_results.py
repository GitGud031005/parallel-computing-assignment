"""Create static scientific plots exclusively from validated summary.csv."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 11.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .2, "savefig.dpi": 180})
COLORS = ["#1a5678", "#15807c", "#ba5b2c", "#715b9b", "#bc8b1d", "#bd405c", "#485861"]


def series(axis, rows, metric, scale=1):
    prefix = metric
    for index, impl in enumerate(sorted({r["implementation"] for r in rows})):
        data = sorted((r for r in rows if r["implementation"] == impl), key=lambda r: int(r["threads"]))
        x = [int(r["threads"]) for r in data]
        y = [float(r[f"median_{prefix}"]) / scale for r in data]
        low = [(float(r[f"median_{prefix}"]) - float(r[f"q1_{prefix}"])) / scale for r in data]
        high = [(float(r[f"q3_{prefix}"]) - float(r[f"median_{prefix}"])) / scale for r in data]
        axis.errorbar(x, y, yerr=[low, high], marker="o", markersize=3, capsize=2,
                      label=impl, color=COLORS[index % len(COLORS)], linewidth=1.3)
    axis.set_xlabel("Threads")
    if rows: axis.set_xticks(sorted({int(r["threads"]) for r in rows}))
    axis.set_ylim(bottom=0)


def save(fig, path):
    handles, labels = fig.axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=min(len(labels), 4), frameon=False, fontsize=10)
    fig.tight_layout(rect=(0, .15, 1, .92))
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def plot(summary_path, output):
    rows = list(csv.DictReader(summary_path.open()))
    if any(r["complete"] != "1" for r in rows): raise ValueError("cannot plot incomplete measured groups")
    output.mkdir(parents=True, exist_ok=True)
    for mode in ["fixed_total", "per_thread"]:
        selected = [r for r in rows if r["suite"] == "locks" and r["prime_n"] == "997" and r["mode"] == mode]
        if not selected: continue
        works = [w for w in ["0", "1", "4"] if any(r["outside_work"] == w for r in selected)]
        fig, axes = plt.subplots(1, len(works), figsize=(10, 3.7), squeeze=False)
        for axis, work in zip(axes[0], works):
            data = [r for r in selected if r["outside_work"] == work]
            series(axis, data, "program_ms")
            axis.set_title(f"OUTSIDE_WORK = {work}")
            axis.set_ylabel("Program time (ms)")
        fig.suptitle(f"Locks | N=997 | {mode} | median and IQR")
        save(fig, output / f"locks_{mode}.png")
    selected = [r for r in rows if r["suite"] == "locks" and r["prime_n"] in ["97", "10007"] and r["outside_work"] == "0"]
    if selected:
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.7))
        for axis, n in zip(axes, ["97", "10007"]):
            data = [r for r in selected if r["prime_n"] == n]
            series(axis, data, "program_ms")
            totals = sorted({r["total_operations"] for r in data})
            axis.set_title(f"N={n}, K={','.join(totals)}"); axis.set_ylabel("Program time (ms)")
        fig.suptitle("Critical-section cost sensitivity | W=0 | fixed total within each panel")
        save(fig, output / "locks_sensitivity.png")
    for suite, metric, scale, label in [("barriers", "throughput", 1e6, "Million global episodes/s"),
                                        ("counters", "program_ms", 1, "Program time (ms)")]:
        data = [r for r in rows if r["suite"] == suite]
        if not data: continue
        fig, axis = plt.subplots(figsize=(8, 4))
        series(axis, data, metric, scale)
        axis.set_ylabel(label)
        # Barrier/counter rates can span orders of magnitude. Preserve visibility
        # of the slower series without truncating the data at a linear baseline.
        if suite == "barriers":
            axis.set_yscale("log")
            axis.set_ylim(min(float(r["q1_throughput"]) / scale for r in data) * .6,
                          max(float(r["q3_throughput"]) / scale for r in data) * 1.6)
            axis.set_ylabel(label + " (log scale)")
        fig.suptitle(f"{suite.capitalize()} | median and IQR")
        save(fig, output / f"{suite}.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plot(args.summary, args.output)
