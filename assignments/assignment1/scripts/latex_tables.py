"""Write the LaTeX result tables and run facts of the report from validated measurements."""
import argparse
import csv
import json
from pathlib import Path

LOCKS = ["tas", "ttas", "ttas_backoff", "mcs", "std_mutex"]
COUNTERS = ["mutex_tas", "mutex_ttas", "mutex_mcs", "mutex_std", "cas", "cas_backoff", "faa"]
BARRIERS = ["sense_reversing", "std_barrier"]


def tt(name):
    return r"\texttt{" + name.replace("_", r"\_") + "}"


def grouped(value, digits):
    # Five-digit values (barrier rates) drop the decimal so they fit the column.
    text = f"{value:,.{0 if value >= 10000 else digits}f}"
    return text.replace(",", r"\,")


def matrix(rows, impls, metric, caption, label, digits=1, best=min, scale=1.0, unit="", skip_serial=False):
    threads = sorted({int(r["threads"]) for r in rows} - ({1} if skip_serial else set()))
    cell = {(r["implementation"], int(r["threads"])): float(r[metric]) / scale for r in rows}
    winners = {p: best(cell[(i, p)] for i in impls if (i, p) in cell) for p in threads}
    first = 0.20
    rest = (0.995 - first) / len(threads)
    column = lambda w, align: rf">{{{align}\arraybackslash}}p{{\dimexpr {w:.3f}\textwidth-2\tabcolsep-\arrayrulewidth\relax}}"
    spec = "|" + column(first, r"\raggedright") + "|" + "|".join(column(rest, r"\raggedleft") for _ in threads) + "|"
    head = r"\textbf{" + (unit or "Implementation") + "} & " + " & ".join(rf"\textbf{{P={p}}}" for p in threads) + r" \\ \hline"
    # Tables have at most seven rows, so they are kept on one page instead of using longtable.
    lines = [r"\begin{table}[H]", r"\centering", r"\footnotesize", r"\setlength{\tabcolsep}{3pt}",
             rf"\caption{{{caption}}}\label{{{label}}}", rf"\begin{{tabular}}{{{spec}}}", r"\hline", head]
    for impl in impls:
        values = []
        for p in threads:
            if (impl, p) not in cell:
                values.append("--")
                continue
            text = grouped(cell[(impl, p)], digits)
            values.append(rf"\textbf{{{text}}}" if cell[(impl, p)] == winners[p] else text)
        lines.append(tt(impl) + " & " + " & ".join(values) + r" \\ \hline")
    lines += [r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def select(rows, **fields):
    return [r for r in rows if all(r[k] == str(v) for k, v in fields.items())]


def generate(args):
    rows = list(csv.DictReader(args.summary.open()))
    saturation = list(csv.DictReader(args.saturation.open()))
    validation = json.loads((args.summary.parent / "validation.json").read_text())
    manifest = json.loads((args.run_dir / "manifest.json").read_text())
    env = json.loads((args.run_dir / "environment.json").read_text())
    experiments = {e["name"]: e["parameters"] for e in manifest["matrix"]["experiments"]}
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    tables = {}
    core = dict(suite="locks", mode="fixed_total", prime_n=997)
    for w in experiments["core-fixed_total"]["outside_work"]:
        tables[f"locks_fixed_w{w}"] = matrix(select(rows, outside_work=w, **core), LOCKS, "median_program_ms",
            rf"Median program time (ms), fixed total $K={experiments['core-fixed_total']['total_operations'][0]}$, $N=997$, $W={w}$. Bold: fastest at each $P$.",
            f"tab:locks-fixed-w{w}", unit="Lock (ms)")
        tables[f"speedup_w{w}"] = matrix(select(rows, outside_work=w, **core), LOCKS, "speedup",
            rf"Speedup $S(P)=T(1)/T(P)$, fixed total, $N=997$, $W={w}$ (Amdahl bound {w + 1}$\times$). Bold: highest at each $P$.",
            f"tab:speedup-w{w}", digits=2, best=max, unit="Lock", skip_serial=True)
    for w in experiments["core-per_thread"]["outside_work"]:
        tables[f"locks_per_thread_w{w}"] = matrix(select(rows, suite="locks", mode="per_thread", outside_work=w), LOCKS, "median_program_ms",
            rf"Median program time (ms), per-thread $I={experiments['core-per_thread']['iterations_per_thread'][0]}$, $N=997$, $W={w}$; total work grows with $P$.",
            f"tab:locks-per-thread-w{w}", unit="Lock (ms)")
    for name in ["sensitivity-97", "sensitivity-10007"]:
        n, k = experiments[name]["prime_n"][0], experiments[name]["total_operations"][0]
        for w in experiments[name]["outside_work"]:
            tables[f"sensitivity_n{n}_w{w}"] = matrix(select(rows, suite="locks", prime_n=n, outside_work=w), LOCKS, "median_program_ms",
                rf"Median program time (ms), $N={n}$, fixed total $K={k}$, $W={w}$.", f"tab:sens-n{n}-w{w}", unit="Lock (ms)")
    tables["barriers"] = matrix(select(rows, suite="barriers"), BARRIERS, "median_throughput",
        rf"Median global barrier episodes per second (thousands), $E={experiments['barriers']['episodes'][0]}$, no work between episodes. Bold: highest at each $P$.",
        "tab:barriers", best=max, scale=1e3, unit="Barrier (k/s)")
    tables["counters"] = matrix(select(rows, suite="counters"), COUNTERS, "median_program_ms",
        rf"Median program time (ms) for $K={experiments['counters']['total_operations'][0]}$ increments in total. Bold: fastest at each $P$.",
        "tab:counters", unit="Counter (ms)")
    tables["saturation_locks"] = matrix(select(saturation, suite="locks"), LOCKS, "median_program_ms",
        r"Saturation run: median program time (ms), $N=997$, $W=0$, $K=20000$, five measured runs. Bold: fastest at each $P$.",
        "tab:saturation-locks", unit="Lock (ms)")
    tables["saturation_locks_q3"] = matrix(select(saturation, suite="locks"), LOCKS, "q3_program_ms",
        r"Saturation run: third quartile of program time (ms), showing the tail of each distribution.",
        "tab:saturation-locks-q3", unit="Lock (ms)")
    tables["saturation_barriers"] = matrix(select(saturation, suite="barriers"), BARRIERS, "median_throughput",
        r"Saturation run: median global episodes per second (thousands). Bold: highest at each $P$.",
        "tab:saturation-barriers", best=max, scale=1e3, unit="Barrier (k/s)")
    for name, text in tables.items():
        (out / f"{name}.tex").write_text(text, encoding="utf-8")
    cache = env["build_cache"]
    facts = {
        "RunID": manifest["run_id"], "SourceSHA": manifest["source_sha256"], "NumConfigs": validation["configurations"],
        "NumSamples": validation["raw_samples"], "NumFailedMeasured": validation["failed_measured_samples"],
        "NumFailedWarmups": len(validation["failed_warmups"]), "Warmups": manifest["matrix"]["warmup_repetitions"],
        "Reps": manifest["matrix"]["measured_repetitions"], "TimeoutS": manifest["matrix"]["timeout_seconds"],
        "OrderSeed": manifest["matrix"]["order_seed"], "CPUModel": env["cpu_model"].replace("(R)", r"\textsuperscript{\textregistered}").replace("(TM)", r"\texttrademark"),
        "PhysCores": env["physical_cores_in_affinity"], "LogicalCPUs": env["os_logical_cpus"],
        "MemGiB": f"{int(env['memory_total_bytes']) / 2**30:.1f}", "OSName": env["os"].replace("_", r"\_"),
        "Compiler": (env["compiler_version"] or "").splitlines()[0].replace("_", r"\_"),
        "CMakeVersion": (env["cmake_version"] or "").splitlines()[0], "ReleaseFlags": cache.get("CMAKE_CXX_FLAGS_RELEASE", ""),
        "PowerScheme": env["power_mode"].split("(")[-1].split(")")[0] if "(" in env["power_mode"] else env["power_mode"],
        "ACState": env["power_mode"].rsplit(";", 1)[-1].strip(), "SpinHint": env["capabilities"]["spin_hint"].replace("_", r"\_"),
        "ThreadList": ", ".join(str(t) for t in sorted({int(r["threads"]) for r in rows})),
        "MeasureDate": env["timestamp_utc"][:10],
    }
    lines = [rf"\newcommand{{\{key}}}{{{value}}}" for key, value in facts.items()]
    (out / "facts.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"tables": sorted(tables), "facts": len(facts), "output": str(out.resolve())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--saturation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    generate(parser.parse_args())
