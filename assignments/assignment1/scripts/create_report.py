"""Generate the English PDF and Markdown report from real, validated measurements."""
import argparse
import csv
from datetime import datetime
from html import escape
import json
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Preformatted

PDF_NAME = "Assignment1_Report_EN.pdf"
FOOTER = "Parallel Computing | Assignment 1 | GitGud031005 | English edition"


def fonts(directory=None):
    choices = [Path(directory)] if directory else []
    choices += [Path("/usr/share/fonts/truetype/dejavu"), Path("C:/Windows/Fonts"),
                Path("/System/Library/Fonts/Supplemental")]
    for base in choices:
        for names in [("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSansMono.ttf"),
                      ("arial.ttf", "arialbd.ttf", "consola.ttf"), ("Arial.ttf", "Arial Bold.ttf", "Courier New.ttf")]:
            if all((base / name).exists() for name in names):
                for family, name in zip(["Body", "BodyBold", "Code"], names):
                    pdfmetrics.registerFont(TTFont(family, str(base / name)))
                return
    raise RuntimeError("A Unicode font is needed: install DejaVu fonts or pass --font-dir")


class Report:
    def __init__(self, output):
        self.output = output
        self.story, self.md = [], []
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(name="PCBody", fontName="Body", fontSize=10, leading=15, spaceAfter=7))
        self.styles.add(ParagraphStyle(name="PCSmall", fontName="Body", fontSize=8, leading=11, spaceAfter=3))
        self.styles.add(ParagraphStyle(name="PCTitle", fontName="BodyBold", fontSize=23, leading=30, textColor=colors.HexColor("#163a50"), spaceAfter=18))
        self.styles.add(ParagraphStyle(name="PCH1", fontName="BodyBold", fontSize=14, leading=20, spaceAfter=12, textColor=colors.HexColor("#163a50")))
        self.styles.add(ParagraphStyle(name="PCH2", fontName="BodyBold", fontSize=10, leading=15, spaceBefore=7, spaceAfter=7))
        self.styles.add(ParagraphStyle(name="PCCode", fontName="Code", fontSize=7, leading=10, backColor=colors.HexColor("#f1f5f7"), borderPadding=7, spaceAfter=10))

    def heading(self, text, level=1):
        style = "PCTitle" if level == 0 else "PCH1" if level == 1 else "PCH2"
        self.story.append(Paragraph(escape(text).replace("\n", "<br/>"), self.styles[style]))
        self.md.append("#" * (level + 1) + " " + text.replace("\n", " ") + "\n")

    def paragraph(self, text, small=False):
        self.story.append(Paragraph(escape(text).replace("\n", "<br/>"), self.styles["PCSmall" if small else "PCBody"]))
        self.md.append(text + "\n")

    def table(self, headers, rows, widths=None):
        cells = [[Paragraph(escape(str(c)), self.styles["PCSmall"]) for c in row] for row in [headers, *rows]]
        t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5eef3")),
                              ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fa")]),
                              ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                              ("LINEBELOW", (0, 0), (-1, 0), .5, colors.HexColor("#b7cbd6"))]))
        self.story.extend([t, Spacer(1, 9)])
        self.md += ["| " + " | ".join(map(str, headers)) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
        self.md += ["| " + " | ".join(str(c).replace("\n", " ") for c in row) + " |" for row in rows]
        self.md.append("")

    def image(self, path, caption):
        image = Image(str(path))
        image.drawHeight *= (17.4 * cm) / image.drawWidth
        image.drawWidth = 17.4 * cm
        self.story.append(image)
        self.story.append(Paragraph(escape(caption), self.styles["PCSmall"]))
        relative = os.path.relpath(path, self.output).replace(os.sep, "/")
        self.md.append(f"![{caption}]({relative})\n")

    def code(self, text):
        self.story.append(Preformatted(text, self.styles["PCCode"]))
        self.md.append("```bash\n" + text + "\n```\n")

    def page(self): self.story.append(PageBreak())

    def save(self):
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output / "report.md").write_text("\n".join(self.md), encoding="utf-8")
        def page(canvas, doc):
            canvas.setStrokeColor(colors.HexColor("#b8ccd6"))
            canvas.line(42, 42, A4[0] - 42, 42)
            canvas.setFont("Body", 7)
            canvas.setFillColor(colors.HexColor("#526671"))
            canvas.drawString(42, 28, FOOTER)
            canvas.drawRightString(A4[0] - 42, 28, str(doc.page))
        document = SimpleDocTemplate(str(self.output / PDF_NAME), pagesize=A4,
                                     rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=55,
                                     title="Parallel Computing Assignment 1 - Implementation and Experiments",
                                     author="GitGud031005")
        document.build(self.story, onFirstPage=page, onLaterPages=page)


def generate(args):
    fonts(args.font_dir)
    manifest = json.loads((args.run_dir / "manifest.json").read_text())
    env = json.loads((args.run_dir / "environment.json").read_text())
    measured = json.loads((args.summary.parent / "validation.json").read_text())
    checks = json.loads(args.checks.read_text())
    if measured["failed_measured_samples"] or not measured["all_groups_complete"]: raise ValueError("incomplete performance data")
    if checks["kernel_source_sha256"] != manifest["source_sha256"]: raise ValueError("tests and benchmark source mismatch")
    if any(c["status"] == "failed" for c in checks["checks"]): raise ValueError("unresolved validation failure")
    rows = list(csv.DictReader(args.summary.open()))
    find = lambda **fields: [r for r in rows if all(r.get(k) == str(v) for k, v in fields.items())]
    saturation = list(csv.DictReader(args.saturation.open())) if args.saturation else []

    def saturation_table(suite, metric, label, scale=1.0):
        data = [r for r in saturation if r["suite"] == suite]
        if not data: return
        columns = sorted({int(r["threads"]) for r in data})
        digits = 1 if scale > 1 else 0
        number = lambda r, q: f"{float(r[q + '_' + metric]) / scale:,.{digits}f}"
        cell = lambda r: f"{number(r, 'median')} [{number(r, 'q1')}-{number(r, 'q3')}]"
        body = [[impl] + [next((cell(r) for r in data if r["implementation"] == impl and int(r["threads"]) == p), "") for p in columns]
                for impl in sorted({r["implementation"] for r in data})]
        doc.table([label] + [f"P={p}" for p in columns], body, [3.4 * cm] + [14.0 * cm / len(columns)] * len(columns))
    median = lambda r: float(r["median_program_ms"])
    peak = max(int(r["threads"]) for r in rows)
    threads = sorted({int(r["threads"]) for r in rows})
    fmt = lambda x: f"{float(x):,.3f}"
    matrix = manifest["matrix"]
    experiments = {e["name"]: e["parameters"] for e in matrix["experiments"]}
    core = experiments["core-fixed_total"]
    doc = Report(args.output)
    date = datetime.fromisoformat(env["timestamp_utc"]).strftime("%d %B %Y")
    cores, logical = env["physical_cores_in_affinity"], env["os_logical_cpus"]
    memory = f"{int(env['memory_total_bytes']) / 2**30:.1f} GiB RAM" if env.get("memory_total_bytes") else "memory not recorded"
    platform = f"{env['cpu_model']} ({cores} physical cores, {logical} logical CPUs, {memory})"
    if args.platform_note: platform += f"; {args.platform_note}"

    doc.heading("Parallel Computing\nAssignment 1", 0)
    doc.paragraph(f"Implementation and experimental report | Measurements: {date}\nRepository: GitGud031005/parallel-computing-assignment")
    doc.heading("Scope and deliverables", 1)
    doc.paragraph("The implementation covers all three required shared-memory parts in C++20: TAS/TTAS/MCS mutex locks, a reusable Sense-Reversing Barrier, and concurrent counters using mutexes, compare-and-swap (CAS), and fetch-and-add (FAA). Standard mutex/barrier implementations provide comparison baselines. TTAS/CAS exponential backoff are additional experiments. Optional MPI-3 one-sided RMA is not implemented.")
    doc.table(["Requirement", "Implementation / evidence"], [
        ["Locks and prime workload", "TAS, TTAS, MCS, std::mutex, TTAS-backoff; identical naive is_prime and outside-work contract."],
        ["Reusable barrier", "Sense reversal and std::barrier; global episodes per second without useful work between episodes."],
        ["Counters", "Four mutex counters, CAS, FAA, CAS-backoff; increments return the previous value."],
        ["Correctness and scaling", "Directed tests, SC reference variants, stress runs, raw records, median/IQR plots and reproducible scripts."]
    ], [4.8 * cm, 12.6 * cm])
    doc.paragraph(f"All measurements were taken on the submitter's own laptop: {platform}. This is the only shared-memory platform used in the study.")
    doc.paragraph(f"Run: {manifest['run_id']}. Revision: {manifest['revision']}. Kernel/build SHA-256: {manifest['source_sha256']}", small=True)

    doc.page(); doc.heading("1. Memory model and mutex locks")
    doc.paragraph("Cache coherence alone does not establish visibility across multiple variables. A C++ data race on ordinary shared data causes undefined behavior. A lock must establish both mutual exclusion and publication of the previous owner's payload. Unlock uses release semantics; the successful acquiring operation receives the corresponding publication. Relaxed polling is only a waiting optimization [2].")
    doc.table(["Lock", "Mechanism and ordering"], [
        ["TAS", "Repeated atomic_flag test_and_set(acquire); clear(release). Repeated central RMW traffic; no FIFO guarantee."],
        ["TTAS", "Poll with relaxed loads while busy, then exchange(acquire); store(release) on unlock. Reduces RMW traffic during waiting, with contention still possible at release."],
        ["MCS", "Stable per-worker queue nodes, atomic tail and local waiting flag. FIFO follows tail-exchange order. A preempted owner can block the queue."],
        ["std::mutex", "Standard-library baseline using the same workload and timing harness. Its internal implementation need not be a spinlock."]
    ], [4.8 * cm, 12.6 * cm])
    doc.paragraph("MCS initializes its node before tail.exchange(acq_rel). An enqueued worker publishes itself through predecessor.next with a release store and waits using acquire loads. Its predecessor releases the payload by storing waiting=false with release semantics. Node/context lifetime extends through unlock; a context is not copied or moved while in use.")
    doc.paragraph("There are two publication paths. With a successor, the waiting flag performs the handoff. With an apparently empty queue, the owner uses strong CAS to reset tail from its own node to null with release semantics. The next acquiring tail exchange receives that publication.")
    doc.paragraph("If CAS fails, a successor may have exchanged tail without linking next yet. The owner must wait for that link and then hand off. Weak CAS could fail spuriously when no successor exists and cause an indefinite wait here. A separate expected pointer prevents CAS from overwriting the identity of the node being unlocked. A directed test holds the successor exactly in this enqueue gap.")
    doc.paragraph("Spinlocks are blocking synchronization: progress can depend on a particular owner running. FIFO enqueue order is not invocation timestamp order, and a passing stress run does not prove starvation freedom.")

    doc.page(); doc.heading("2. Sense reversal and concurrent counters")
    doc.paragraph("The barrier has a fixed positive participant count P, remaining=P and global sense=false. Each worker has a separate local sense for each barrier instance. An arrival flips local sense and performs remaining.fetch_sub(1, acq_rel). The last arrival resets remaining=P with a relaxed store, then publishes global sense with release. Other participants wait with acquire loads.")
    doc.paragraph("The acq_rel RMW chain accumulates the writes preceding each arrival. The last thread receives this chain and publishes it through sense; waiting threads acquire that publication. Reset is sequenced before the release of sense. A second generation cannot finish until every participant has entered it, preventing a delayed participant from missing its previous generation.")
    doc.paragraph("One thread_local boolean shared by all barrier instances would be incorrect when instance phase counts differ. Explicit per-worker/per-instance contexts avoid this. Visibility tests use a second barrier before the next round of writes so that the test itself has no data race. The baseline calls std::barrier::arrive_and_wait [3].")
    doc.table(["Counter", "Linearization and ordering"], [
        ["Mutex TAS/TTAS/MCS/std", "An ordinary uint64_t increment while holding the lock. Concurrent value() calls acquire the same lock."],
        ["CAS", "A successful CAS changing x to x+1. Weak-CAS retries recompute desired from the updated expected value."],
        ["FAA", "fetch_add(1) is one atomic RMW and returns the previous value. Separate load/store would lose updates."],
        ["CAS-backoff", "The same CAS algorithm with deterministic 1..1024 pause steps after failure, reset after each operation."]
    ], [4.8 * cm, 12.6 * cm])
    doc.paragraph("CAS/FAA use relaxed ordering because the counter represents only a number; it does not publish other payload. Increment returns the old value. Validated total work prevents uint64_t wrap. Actual atomic lock-freedom is platform dependent; CAS retry is not a per-thread wait-free guarantee. Returned values [0,K) and final K are empirical oracles; linearization points supply the general operation argument.")

    doc.page(); doc.heading("3. Correctness and course alignment")
    doc.table(["Test group", "Oracle and directed cases"], [
        ["Workload", "Naive prime against an independent square-root oracle for N=0..10009; quotient/remainder work distribution including K<P; input overflow."],
        ["Locks", "Non-overlapping occupancy; protected counts; a separate plain-payload visibility test without telemetry RMW that could hide ordering errors; RAII and multiple instances."],
        ["MCS", "Controlled enqueue gap and FIFO order, empty-queue handoff and node reuse."],
        ["Barrier", "P=1/2/3/4/5/8, five seeds, many phases, A-A-B across instances, visibility and a delayed final participant; reject P=0."],
        ["Counters", "No lost updates, exact old-value range, concurrent reads respecting each thread's completed increments, post-join precedence and no-wrap boundaries."],
        ["CLI / analysis", "Prime/composite checksums, non-divisible work, invalid inputs; known-answer throughput, IQR/speedup and corrupted-row rejection."]
    ], [4.8 * cm, 12.6 * cm])
    describe = lambda c: c["status"] + (f" ({c['build_type']}, sanitizer={c['sanitizer']})" if "build_type" in c else "") \
        + (": " + c["reason"] if "reason" in c else "") + (". " + c["limitations"] if "limitations" in c else "")
    doc.table(["Check run for this report", "Result"], [[c["mode"], describe(c)] for c in checks["checks"]], [4.8 * cm, 12.6 * cm])
    doc.paragraph("All six CTest groups use runtime checks that stay active in Release. SC reference implementations supplement the acquire/release variants; stress increases work tenfold and includes bounded oversubscription. Test timeouts detect a failed run, not correctness. Finite tests and sanitizers do not prove every interleaving.")
    if args.checks_note: doc.paragraph(args.checks_note)
    doc.paragraph("The algorithms follow course material: TAS/TTAS/MCS in Ch03 pp.17-28, sense reversal in Ch04 pp.8-15, CAS/FAA in Ch02a pp.16-21, and C++ ordering in Ch02b. Spinlock progress and counter specifications follow Ch03/Ch05.")

    doc.page(); doc.heading("4. Platform and measurement protocol")
    cache = env["build_cache"]
    doc.table(["Property", "Recorded value"], [
        ["Platform / OS", env["platform_id"] + " / " + env["os"]],
        ["CPU", platform],
        ["Toolchain", (env["compiler_version"] or "unknown").splitlines()[0] + "; Release " + cache.get("CMAKE_CXX_FLAGS_RELEASE", "flags unknown") + "; no LTO or sanitizer."],
        ["Atomics / waiting", "uint64/bool/pointer lock-free: " + "/".join(str(env["capabilities"][k]) for k in ["atomic_uint64_lock_free", "atomic_bool_lock_free", "atomic_pointer_lock_free"]) + "; spin hint " + env["capabilities"]["spin_hint"] + "; 64-byte layout alignment."],
        ["Control", env["affinity_policy"] + "; " + env["power_mode"]]
    ], [4.8 * cm, 12.6 * cm])
    doc.paragraph("Naive is_prime tries divisors 2..N-1 and returns early on a divisor. Each lock iteration acquires, calls it once, releases, then performs W outside calls. The function is in a separate translation unit with IPO/LTO disabled, and local checksums are consumed after join, so the compiler cannot remove the work. volatile is not used as synchronization.")
    doc.paragraph("Program time starts immediately before thread spawn and ends after join, including the independent latch start gate. Context/work allocations precede this timer. Worker interval is max(end)-min(start) after the gate. The barrier executes E episodes with no useful work between; throughput is E/worker_seconds, not P*E/seconds.")
    warmups = measured["failed_warmups"]
    failures = f"{measured['failed_measured_samples']} failed measured samples"
    if warmups:
        failures += f" and {len(warmups)} failed warmup(s), excluded from statistics by design: " + "; ".join(
            f"{w['implementation']} P={w['threads']} {w['mode']} W={w['outside_work']} ({w['status']}: {w['error']})" for w in warmups)
    doc.paragraph(f"The matrix has {measured['configurations']} configurations, {matrix['warmup_repetitions']} warmups and {matrix['measured_repetitions']} measured repetitions each: {measured['raw_samples']} raw samples, {failures}. Each sample is a separate process with a {matrix['timeout_seconds']} s timeout; configuration order uses fixed shuffle seed {matrix['order_seed']}. Median and inclusive IQR are descriptive statistics, not confidence intervals.")
    above = [t for t in threads if t > cores]
    sweep = f"Threads P={'/'.join(map(str, threads))} on {cores} physical cores and {logical} logical CPUs"
    sweep += f"; P={'/'.join(map(str, above))} use Hyper-Threading siblings." if above else "."
    if saturation: sweep += " P values that fill every logical CPU are measured in a separate saturation run (sections 5 and 7)."
    doc.paragraph(f"{sweep} Core locks use N=997, W={'/'.join(map(str, core['outside_work']))}; fixed-total K={core['total_operations'][0]} or per-thread I={experiments['core-per_thread']['iterations_per_thread'][0]}. Sensitivity uses N=97/K={experiments['sensitivity-97']['total_operations'][0]} and N=10007/K={experiments['sensitivity-10007']['total_operations'][0]} with W=0/4. Barriers use E={experiments['barriers']['episodes'][0]}; counters K={experiments['counters']['total_operations'][0]}. Short runs remain sensitive to startup and scheduling. Per-thread ratios are not strong-scaling speedups.")

    doc.page(); doc.heading("5. Mutex lock results")
    doc.image(args.figures / "locks_fixed_total.png", f"Figure 1. Fixed total K={core['total_operations'][0]}, N=997; median and IQR. Each comparison holds K, N and W constant.")
    selected = find(suite="locks", mode="fixed_total", prime_n=997, outside_work=0, threads=peak)
    doc.table([f"P={peak}, W=0", "Median ms", "IQR ms", "S(P)"], [[r["implementation"], fmt(r["median_program_ms"]), f"{fmt(r['q1_program_ms'])}-{fmt(r['q3_program_ms'])}", fmt(r["speedup"])] for r in selected], [4.8 * cm, 3.6 * cm, 5.4 * cm, 3.6 * cm])
    winner = min(selected, key=median)
    doc.paragraph(f"{winner['implementation']} has the lowest median in this configuration ({fmt(winner['median_program_ms'])} ms). This is a workload/platform-specific observation, not a universal ranking. S(P)=T(1)/T(P) uses program time and the same implementation, K, N and W. Small percentage differences alone do not establish statistical significance.")
    best = []
    for w in core["outside_work"]:
        group = find(suite="locks", mode="fixed_total", prime_n=997, outside_work=w, threads=peak)
        fastest = min(group, key=median)
        speedups = {r["implementation"]: float(r["speedup"]) for r in group}
        best.append([str(w), f"1/{w + 1}", fastest["implementation"], fmt(median(fastest)), max(speedups, key=speedups.get), fmt(max(speedups.values()))])
    doc.table(["W", "Calls in CS", f"Fastest at P={peak}", "Median ms", f"Best S({peak})", "S(P)"], best, [1.6 * cm, 2.6 * cm, 3.6 * cm, 2.8 * cm, 3.6 * cm, 3.2 * cm])
    for text in args.lock_notes: doc.paragraph(text)
    saturation_table("locks", "program_ms", "Saturation, ms median [IQR]")
    doc.paragraph("Useful work inside the critical section remains serial. TAS repeatedly updates a shared flag; TTAS reads while busy; MCS replaces central flag contention with queued nodes and handoffs. These are algorithmic explanations, not measured cache-miss attribution.")

    doc.page(); doc.heading("6. Outside work and critical-section sensitivity")
    doc.image(args.figures / "locks_per_thread.png", f"Figure 2. Per-thread I={experiments['core-per_thread']['iterations_per_thread'][0]}. Total critical-section operations grow as P*I; these curves must not be interpreted as strong scaling.")
    doc.paragraph("OUTSIDE_WORK=k puts 1/(k+1) of prime calls inside the critical section. This is a fraction of calls, not elapsed time, because lock/spin/scheduler overhead also contributes. More outside work can reduce contention while increasing total computation. Every sample checks the expected total call checksum.")
    doc.image(args.figures / "locks_sensitivity.png", "Figure 3. Short/long N sensitivity; K differs between panels to keep durations practical. Compare implementations and P only within a panel.")
    for text in args.sensitivity_notes: doc.paragraph(text)
    doc.paragraph("Backoff uses 1..1024 pause instructions, not the nanosecond sleeps of the statement's example: a sleep hands the core to the OS scheduler and its minimum granularity is far longer than a short critical section. Backoff can help or hurt depending on retry and waiting costs.")

    doc.page(); doc.heading("7. Barrier throughput")
    doc.image(args.figures / "barriers.png", "Figure 4. Global episodes per second, median and IQR, without useful work between barriers.")
    selected = find(suite="barriers", threads=peak)
    doc.table([f"P={peak}", "Median episodes/s", "Latency/episode (us)"], [[r["implementation"], fmt(r["median_throughput"]), fmt(float(r["median_worker_ms"]) * 1000 / int(r["episodes"]))] for r in selected], [4.8 * cm, 6.3 * cm, 6.3 * cm])
    doc.paragraph("Each of P workers makes E calls, but the program completes E global episodes. P*E/t measures arrival throughput, a different unit. Timers are read at worker boundaries, not every phase. The standard library and centralized custom barrier have different implementation/platform tradeoffs; the custom remaining/sense state is still shared contention.")
    for text in args.barrier_notes: doc.paragraph(text)
    saturation_table("barriers", "throughput", "Saturation, thousand episodes/s", 1e3)

    doc.page(); doc.heading("8. Concurrent counter performance")
    doc.image(args.figures / "counters.png", f"Figure 5. Fixed K={experiments['counters']['total_operations'][0]} increments; spawn-to-join program time, median and IQR.")
    selected = find(suite="counters", threads=peak)
    doc.table([f"P={peak}", "Median ms", "Median increments/s"], [[r["implementation"], fmt(r["median_program_ms"]), fmt(r["median_throughput"])] for r in selected], [4.8 * cm, 5.0 * cm, 7.6 * cm])
    fastest = min(selected, key=median)
    doc.paragraph(f"{fastest['implementation']} has the lowest median in this table. All variants validate final K and the old-value checksum. CAS may retry; FAA directly expresses the increment RMW; mutex counters add lock/unlock. All still update one shared numeric location, so more workers do not create independent useful counter work.")
    for text in args.counter_notes: doc.paragraph(text)
    doc.paragraph("No diagnostic shared retry counter is added to the timed hot loop. Fast execution does not prove wait-freedom, fairness or starvation freedom.")

    doc.page(); doc.heading("9. Reproduction, limitations and references")
    doc.paragraph("Run from the repository root with CMake >=3.20, a C++20 compiler whose standard library has std::barrier, and Python >=3.10 with the packages in assignments/assignment1/scripts/requirements.txt. Use a fresh output directory; the runner rejects overwriting previous data.")
    doc.code("cmake -S . -B build/release -G Ninja -DCMAKE_BUILD_TYPE=Release\ncmake --build build/release -j 8\nctest --test-dir build/release --output-on-failure\npython assignments/assignment1/scripts/run_benchmarks.py \\\n  --bin-dir build/release/assignments/assignment1 \\\n  --matrix assignments/assignment1/config/benchmark_matrix.json \\\n  --platform-id my-computer --output results-local/run-01")
    doc.paragraph("Then run summarize.py, plot_results.py and create_report.py with the run, summary, figure and checks paths; package_submission.py builds the ZIP. Extract the ZIP into a fresh directory and build/test again.")
    doc.paragraph(args.limitations)
    doc.heading("References", 2)
    for text in [
        "[1] Assignment1_v1_16092026.pdf, pp.1-4, supplied course material.",
        "[2] Course slides Ch00-Ch07 (including Ch02a/Ch02b); Ch03 pp.17-28, Ch04 pp.8-15. Page numbers are one-based PDF pages.",
        "[3] C++20 draft N4861: atomics.order, atomics.types.operations, thread.barrier.class. https://timsong-cpp.github.io/cppwp/n4861/",
        "[4] Mellor-Crummey and Scott, Algorithms for Scalable Synchronization on Shared-Memory Multiprocessors, ACM TOCS (1991). https://www.cs.rochester.edu/research/synchronization/pseudocode/ss.html"
    ]: doc.paragraph(text, small=True)
    doc.save()
    print(json.dumps({"report_pdf": str((args.output / PDF_NAME).resolve()), "report_md": str((args.output / "report.md").resolve())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--figures", type=Path, required=True)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font-dir", type=Path)
    parser.add_argument("--saturation", type=Path, help="summary.csv of the separate saturation run")
    parser.add_argument("--notes", type=Path, help="JSON with platform_note, checks_note, limitations and lists lock_notes, sensitivity_notes, barrier_notes, counter_notes")
    args = parser.parse_args()
    notes = json.loads(args.notes.read_text(encoding="utf-8")) if args.notes else {}
    args.platform_note, args.checks_note = notes.get("platform_note"), notes.get("checks_note")
    args.limitations = notes.get("limitations", "Limitations: one platform, uncontrolled background load, short-run startup effects, no hardware counters or exhaustive model checking.")
    for key in ["lock_notes", "sensitivity_notes", "barrier_notes", "counter_notes"]: setattr(args, key, notes.get(key, []))
    generate(args)
