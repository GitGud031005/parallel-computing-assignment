"""Generate the Vietnamese PDF and Markdown report from real, validated measurements."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, Preformatted


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
        self.story.append(Paragraph(escape(text), self.styles[style]))
        self.md.append("#" * (level + 1) + " " + text + "\n")

    def paragraph(self, text):
        self.story.append(Paragraph(escape(text), self.styles["PCBody"]))
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
        (self.output / "report.md").write_text("\n".join(self.md))
        def page(canvas, doc):
            canvas.setStrokeColor(colors.HexColor("#b8ccd6"))
            canvas.line(42, 42, A4[0] - 42, 42)
            canvas.setFont("Body", 7)
            canvas.setFillColor(colors.HexColor("#526671"))
            canvas.drawString(42, 28, "Parallel Computing | Assignment 1 | GitGud031005")
            canvas.drawRightString(A4[0] - 42, 28, str(doc.page))
        document = SimpleDocTemplate(str(self.output / "report.pdf"), pagesize=A4,
                                     rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=55,
                                     title="Parallel Computing - Assignment 1", author="GitGud031005")
        document.build(self.story, onFirstPage=page, onLaterPages=page)


def generate(args):
    fonts(args.font_dir)
    manifest = json.loads((args.run_dir / "manifest.json").read_text())
    env = json.loads((args.run_dir / "environment.json").read_text())
    measured = json.loads((args.summary.parent / "validation.json").read_text())
    checks = json.loads(args.checks.read_text())
    if measured["failed_samples"] or not measured["all_groups_complete"]: raise ValueError("incomplete performance data")
    if checks["kernel_source_sha256"] != manifest["source_sha256"]: raise ValueError("tests and benchmark source mismatch")
    if any(c["status"] == "failed" for c in checks["checks"]): raise ValueError("unresolved validation failure")
    rows = list(csv.DictReader(args.summary.open()))
    find = lambda **fields: [r for r in rows if all(r.get(k) == str(v) for k, v in fields.items())]
    peak = max(int(r["threads"]) for r in rows)
    fmt = lambda x: f"{float(x):,.3f}"
    doc = Report(args.output)
    date = datetime.fromisoformat(env["timestamp_utc"]).astimezone(timezone(timedelta(hours=7))).strftime("%d/%m/%Y")

    doc.heading("Parallel Computing\nAssignment 1", 0)
    doc.paragraph(f"Báo cáo triển khai và thực nghiệm | {date} | Repository: GitGud031005/parallel-computing-assignment")
    doc.heading("Phạm vi và kết quả bàn giao", 1)
    doc.paragraph("Bài làm triển khai đầy đủ ba phần shared-memory bắt buộc bằng C++20: TAS/TTAS/MCS mutex locks, Sense-Reversing Barrier và concurrent counters dùng mutex, compare-and-swap, fetch-and-add. Standard mutex và standard barrier làm đối chứng. Có thêm TTAS/CAS exponential backoff để quan sát trade-off. Distributed MPI-3 RMA là phần tùy chọn và không triển khai trong bản này.")
    doc.table(["Yêu cầu từ đề [1]", "Sản phẩm và bằng chứng"], [
        ["Locks và workload prime", "3 custom locks + std::mutex + TTAS-backoff; cùng naive is_prime và OUTSIDE_WORK"],
        ["Barrier reusable", "Sense-Reversing + std::barrier; episode/s toàn cục, không useful work giữa episodes"],
        ["Counters", "4 lock-based counters + CAS + FAA + CAS-backoff; trả old value, đọc dưới cùng cơ chế bảo vệ"],
        ["Correctness / scalability", "Source, tests định hướng interleaving, SC đối chiếu, log kiểm tra, raw CSV, median/IQR, biểu đồ"],
        ["Báo cáo và source ZIP", "report.pdf, report.md, CMake, headers/source/tests/scripts/config và dữ liệu thí nghiệm"]
    ], [4.8 * cm, 12.6 * cm])
    doc.paragraph("Phép đo trong báo cáo là dữ liệu thật từ môi trường Linux được cấp cho phiên làm việc này. Đây không phải laptop cá nhân của sinh viên. Danh sách các máy cá nhân đang sở hữu chưa được cung cấp; yêu cầu đo trên những máy đó cần thực hiện bằng cùng scripts trước khi người nộp chốt báo cáo theo điều kiện của lớp. Không thay thế bằng kết quả phần cứng giả định.")
    doc.paragraph(f"Run ID: {manifest['run_id']}. Revision mã triển khai: {manifest['revision']}. Kernel/build source SHA-256: {manifest['source_sha256']}. Mỗi executable và raw sample đều lưu fingerprint để phát hiện binary cũ.")

    doc.page(); doc.heading("1. Memory model và mutex locks")
    doc.paragraph("Cache coherence không tự đảm bảo quan sát đúng giữa nhiều biến. C++ data race trên dữ liệu không atomic dẫn tới undefined behavior. Lock cần bảo vệ cả mutual exclusion và khả năng nhìn thấy payload của owner trước đó. Release khi unlock đồng bộ với acquire nhận publication tương ứng; relaxed polling chỉ là tối ưu chờ, không phải quyền vào critical section [2].")
    doc.table(["Lock", "Cơ chế", "Ordering và progress"], [
        ["TAS", "atomic_flag test_and_set lặp lại", "Acquire RMW thành công; release clear. Central RMW, không FIFO."],
        ["TTAS", "Load khi cờ bận, sau đó exchange", "Polling relaxed; exchange acquire; store release. Giảm RMW lúc đang chờ, vẫn có tranh chấp lúc mở khóa."],
        ["MCS", "Queue node riêng cho mỗi worker/context", "FIFO theo tail exchange; chờ trên cờ riêng. Owner bị preempt vẫn có thể chặn queue."],
        ["std::mutex", "Standard library adapter", "Dùng cùng workload/harness; đây là baseline chứ không phải giả định cùng cơ chế spin."]
    ], [2.4 * cm, 5.4 * cm, 9.6 * cm])
    doc.heading("MCS: hai đường trao quyền và nhánh dễ sai", 2)
    doc.paragraph("Node có atomic next/waiting; tail là atomic pointer. Context không copy/move trong lúc dùng và sống đến sau release. Worker reset node trước tail.exchange(acq_rel), nối predecessor.next bằng release-store rồi acquire-load waiting. Predecessor release-store waiting=false cho successor. Chuỗi này truyền payload qua handoff.")
    doc.paragraph("Nếu next còn null, owner thử strong CAS tail từ chính node của mình về null. CAS thành công có release semantics; lần tail.exchange(acq_rel) tiếp theo nhận null sẽ acquire publication của owner cũ. Đây là đường queue-rỗng, phải được xét riêng với handoff có successor.")
    doc.paragraph("Nếu CAS thất bại, successor đã đổi tail nhưng có thể chưa nối next. Owner phải chờ next xuất hiện rồi handoff. Dùng strong CAS vì weak CAS có thể thất bại giả ngay khi chưa có successor, khiến owner chờ vô hạn. Expected là biến pointer riêng để CAS không ghi đè định danh node cần unlock. Test hook giữ successor đúng tại gap này và chỉ mở sau khi owner đi qua nhánh CAS-fail.")
    doc.paragraph("FIFO là thứ tự enqueue vào tail, không phải timestamp bên ngoài trước acquire. Spinlock vẫn là blocking synchronization: thread giữ lock ngừng chạy có thể ngăn người khác tiến triển. Không suy luận starvation freedom từ một lần stress test thành công.")

    doc.page(); doc.heading("2. Barrier và concurrent counters")
    doc.heading("Sense-Reversing Barrier", 2)
    doc.paragraph("Barrier có participant count cố định dương, remaining khởi tạo P và global sense=false. Mỗi worker giữ local sense=false riêng cho từng barrier instance. Mỗi lượt đảo local sense, fetch_sub(1, acq_rel). Thread nhận old remaining=1 là người cuối: reset remaining=P bằng relaxed-store, sau đó release-store global sense. Người khác acquire-load sense cho đến khi khớp local sense.")
    doc.paragraph("Các RMW acq_rel trên remaining nối các arrivals theo modification order, tích lũy writes của threads đã đến. Thread cuối đã acquire mọi writes trước đó rồi publish qua sense; người chờ acquire publication đó. Thread cuối không cần chờ sense vì nó đã nhận chuỗi arrivals. Reset counter được sequenced-before release sense, nên lần đến kế tiếp không mất updates. Chưa thể toggle sense lần thứ hai cho tới khi mọi participant của vòng trước đã đi vào vòng tiếp theo; một thread chưa quan sát xong vòng cũ do đó không bị bỏ qua generation.")
    doc.paragraph("Một thread_local bool dùng chung cho mọi barrier là sai thiết kế vì phase counts giữa hai instance có thể khác nhau. API dùng context tường minh. Test viết slot, barrier, đọc tất cả slot rồi barrier lần hai trước vòng mới; barrier thứ hai ngăn chính test tự gây data race. Standard baseline dùng std::barrier::arrive_and_wait [3].")
    doc.heading("Counter contract và linearization", 2)
    doc.table(["Biến thể", "State / điểm có hiệu lực", "Lý do memory order"], [
        ["Mutex TAS/TTAS/MCS/std", "uint64_t dưới lock; lệnh tăng trong CS", "Acquire/release trao quyền; value(context) cũng giữ lock nếu có readers đồng thời."],
        ["CAS", "CAS thành công thay x bằng x+1", "Expected cập nhật khi fail; desired tính lại. Relaxed hợp lệ vì chỉ đếm số, không publish payload khác."],
        ["FAA", "fetch_add(1) trả giá trị cũ", "Một atomic RMW relaxed; không biến load + store thành phép tăng giả nguyên tử."],
        ["CAS-backoff", "Cùng CAS, thêm pause sau fail", "Policy deterministic 1..1024 pause steps, reset sau operation; không nhầm đơn vị nanosecond."]
    ], [3.6 * cm, 6.2 * cm, 7.6 * cm])
    doc.paragraph("Increment trả old value, counter khởi tạo 0; tổng operations được validation để không wrap uint64_t. CAS/FAA không dùng để cấp phép truy cập dữ liệu thường khác. Lock-free phụ thuộc atomic thực tế; CAS retry loop không đảm bảo mỗi thread wait-free. Tập returned values [0,K) và final K là oracle thực nghiệm, còn linearization point là lập luận cho mọi execution hợp lệ.")

    doc.page(); doc.heading("3. Kiểm tra và đối chiếu kiến thức")
    doc.paragraph("Suite CTest gồm workload, locks, barriers, counters, CLI validation và analysis validation. Assertions kiểm tra vẫn hoạt động trong Release vì dùng runtime checks, không dựa vào assert bị NDEBUG tắt. Test process có timeout; không coi timeout là bằng chứng tính đúng.")
    doc.table(["Nhóm", "Oracle / tình huống chủ động"], [
        ["Workload", "Naive prime đối chiếu oracle sqrt độc lập với N=0..10009; quotient/remainder giữ đủ K, kể cả K<P; overflow input."],
        ["Locks", "Occupancy atomic không overlap; plain protected count; payload invariant ở một lượt riêng không thêm telemetry RMW che lỗi ordering; RAII và 2 instances."],
        ["MCS", "Gap sau tail exchange trước nối next; owner phải chờ link; FIFO enqueue có điều khiển; queue-rỗng và tái dùng node."],
        ["Barrier", "1/2/3/4/5/8 participants, 5 seeds; nhiều phase; A-A-B giữa 2 instances; visibility; giữ last participant sau arrival thật; reject P=0."],
        ["Counters", "Không lost update; returned values không trùng/thiếu; concurrent value >= increment trước đó của cùng thread; post-join precedence; boundary và instances."],
        ["Executable / analysis", "Đối chiếu checksum cho prime/composite; K không chia hết và K<P; input invalid; known-answer episode/s, IQR, speedup và phát hiện raw data hỏng."],
        ["SC / stress", "TAS/TTAS/MCS/barrier có SC reference; CAS/FAA có SC reference. Stress tăng 10 lần work; bounded oversubscription tách khỏi kết luận progress tổng quát."]
    ], [3.0 * cm, 14.4 * cm])
    doc.table(["Kiểm tra thực tế", "Kết quả"], [[c["mode"], c["status"] + (": " + c["reason"] if "reason" in c else "") + (". " + c["limitations"] if "limitations" in c else "")] for c in checks["checks"]], [4.3 * cm, 13.1 * cm])
    doc.paragraph("Finite tests, TSan hay ASan đều không phải chứng minh đầy đủ mọi interleaving. Báo cáo giữ riêng kết quả công cụ và lập luận happens-before. Nếu một sanitizer không khởi tạo được trong môi trường, trạng thái unavailable được ghi đúng; không suy ra race-free từ lần không chạy được đó.")

    doc.page(); doc.heading("4. Môi trường và protocol đo")
    cache = env["build_cache"]
    doc.table(["Thuộc tính", "Giá trị thực tế"], [
        ["Platform ID / OS", env["platform_id"] + " / " + env["os"]],
        ["CPU model", env["cpu_model"]],
        ["Logical CPU / affinity / topology", f"OS={env['os_logical_cpus']}, affinity={env['affinity_logical_cpus']}, cores theo topology={env['physical_cores_in_affinity']} (môi trường ảo hóa)"],
        ["CPU quota / memory limit", str(env["cpu_quota"]) + " / " + str(env["memory_limit_bytes"])],
        ["Compiler", (env["compiler_version"] or "unknown").splitlines()[0]],
        ["Release flags", cache.get("CMAKE_CXX_FLAGS_RELEASE", "unknown") + " | no LTO, no sanitizer"],
        ["Atomic uint64/bool/pointer lock-free", "/".join(str(env["capabilities"][k]) for k in ["atomic_uint64_lock_free", "atomic_bool_lock_free", "atomic_pointer_lock_free"])],
        ["Wait hint / alignment", env["capabilities"]["spin_hint"] + " / 64 bytes (lựa chọn layout)"],
        ["Affinity / power", env["affinity_policy"] + "; " + env["power_mode"]]
    ], [5.1 * cm, 12.3 * cm])
    doc.paragraph("Naive is_prime thử mọi divisor từ 2 đến N-1 và dừng sớm nếu tìm thấy ước. N đọc từ CLI; implementation nằm ở translation unit riêng và benchmark tắt IPO/LTO. Checksum cục bộ được dùng sau join; compiler không biết hàm pure qua declaration. Đã kiểm tra optimized disassembly để xác nhận external primality calls còn trong vòng lặp, ở trong/ngoài CS tương ứng. Không dùng volatile làm primitive đồng bộ.")
    doc.paragraph("Program time bắt đầu ngay trước spawn và kết thúc sau join, gồm gate/khởi tạo thread theo metric đề. Work/context allocations ở trước timer. Worker interval = max(end)-min(start), bắt đầu sau standard latch gate độc lập. Barrier loop chỉ gọi arrive_and_wait E lần; episode/s = E / worker_seconds, không nhân thêm P.")
    doc.paragraph(f"Matrix gồm {measured['configurations']} cấu hình, {manifest['matrix']['warmup_repetitions']} warmup và {manifest['matrix']['measured_repetitions']} measured repetitions mỗi cấu hình; {measured['raw_samples']} raw rows, {measured['failed_samples']} lỗi. Thứ tự cấu hình xáo theo seed cố định {manifest['matrix']['order_seed']}, chạy tuần tự. Median và IQR là thống kê mô tả, không phải confidence interval. Raw rows và manifest giữ nguyên để tái lập.")
    doc.paragraph("Core N=997, W=0/1/2/4/8, P=1/2/3/4/8; fixed-total K=20000 và per-thread I=5000. Sensitivity N=97/K=200000, N=10007/K=2000, W=0/4; K được giữ cố định trong từng panel. Barrier E=20000; counters K=1000000. Các workload ngắn phục vụ reference sweep rộng; startup/scheduling và host contention vẫn ảnh hưởng, đặc biệt ở serial/counter nhanh. Không gọi per-thread timing ratio là strong-scaling speedup.")

    doc.page(); doc.heading("5. Kết quả mutex locks")
    doc.image(args.figures / "locks_fixed_total.png", "Hình 1. N=997, fixed-total K=20000; median và IQR; cùng K,N,W trong mỗi comparison.")
    selected = find(suite="locks", mode="fixed_total", prime_n=997, outside_work=0, threads=peak)
    doc.table([f"P={peak}, W=0", "Median (ms)", "IQR (ms)", "Speedup S(P)"], [[r["implementation"], fmt(r["median_program_ms"]), f"{fmt(r['q1_program_ms'])} - {fmt(r['q3_program_ms'])}", fmt(r["speedup"])] for r in selected], [4.1 * cm, 3.8 * cm, 6.1 * cm, 3.4 * cm])
    winner = min(selected, key=lambda r: float(r["median_program_ms"]))
    doc.paragraph(f"Ở cấu hình được trích bảng, {winner['implementation']} có median thấp nhất: {fmt(winner['median_program_ms'])} ms. Đây là kết quả của đúng workload/platform này, không là thứ hạng phổ quát. Tăng threads không đảm bảo giảm thời gian vì useful work trong CS vẫn tuần tự và contenders phải trao quyền sở hữu cache line/queue.")
    doc.paragraph("S(P)=T(1)/T(P) được tính với cùng implementation và cùng K,N,W, dùng program time. Các giá trị trong bảng là thống kê median mô tả; chênh lệch nhỏ vài phần trăm không tự chứng minh ưu thế có ý nghĩa thống kê. Không áp công thức strong scaling cho đồ thị per-thread có tổng việc thay đổi.")
    doc.paragraph("TAS tạo RMW liên tục trên cờ chung; TTAS đọc khi bận; MCS đổi chi phí tranh chấp cờ chung thành node và handoff theo queue. Đây là giải thích cấu trúc dựa trên thuật toán, chưa phải phép đo hardware cache misses. Khi CS dài hoặc owner bị preempt, spin/queue và standard mutex có trade-off khác nhau. Chỉ elapsed time không đủ khẳng định nguyên nhân cache/NUMA chính xác.")

    doc.page(); doc.heading("6. Workload ngoài CS và sensitivity")
    doc.image(args.figures / "locks_per_thread.png", "Hình 2. Per-thread I=5000: P tăng cũng làm tổng CS=P×I tăng; không dùng đồ thị này để suy ra strong scaling.")
    doc.paragraph("OUTSIDE_WORK=k nghĩa là 1/(k+1) số prime calls ở trong CS. Đó không phải tỷ lệ thời gian vì còn lock/spin và chi phí scheduler. Work ngoài CS tăng có thể giảm contention, nhưng cũng tăng tổng lượng tính toán. Các raw samples luôn kiểm checksum bằng tổng calls dự kiến.")
    doc.image(args.figures / "locks_sensitivity.png", "Hình 3. Sensitivity N ngắn/dài; K khác giữa hai panel để giữ thời lượng hợp lý. Chỉ so algorithms/P trong cùng panel.")
    doc.paragraph("Backoff dùng 1..1024 pause steps sau thất bại, không phải sleep_for nanoseconds. So sánh TTAS-backoff với TTAS trong cùng panel giúp thấy chi phí retry giảm hay tăng ở workload thực; không mặc định exponential backoff luôn cải thiện performance.")

    doc.page(); doc.heading("7. Barrier throughput")
    doc.image(args.figures / "barriers.png", "Hình 4. Throughput là global episodes/s; không useful work giữa các lần barrier, không nhân với số participants.")
    selected = find(suite="barriers", threads=peak)
    doc.table([f"P={peak}", "Median global episodes/s", "Median latency/episode (µs)"], [[r["implementation"], fmt(r["median_throughput"]), fmt(float(r["median_worker_ms"]) * 1000 / int(r["episodes"]))] for r in selected], [4.9 * cm, 6.0 * cm, 6.5 * cm])
    doc.paragraph("Mỗi worker gọi barrier E lần nên chương trình có E episode, nhưng P×E arrival calls. Việc tính P×E/t sẽ cho arrival throughput khác đơn vị và phóng đại episode throughput. Timer chỉ đọc ở hai đầu worker, không trong mỗi phase. Standard barrier có implementation/platform trade-off riêng; custom centralized remaining/sense vẫn có điểm tranh chấp chung.")
    doc.paragraph("Với nhiều participants, một worker tới chậm làm cả phase chờ. Với hơn tài nguyên CPU khả dụng, busy waiting có thể bị ảnh hưởng mạnh bởi preemption. Bản reference sweep giới hạn tới 8 threads theo quota CPU; bounded oversubscription chỉ là correctness stress, không thay cho nghiên cứu performance trên laptop thật.")

    doc.page(); doc.heading("8. Concurrent counter performance")
    doc.image(args.figures / "counters.png", "Hình 5. Cùng tổng K=1000000 increments; program time từ spawn tới join; median và IQR.")
    selected = find(suite="counters", threads=peak)
    doc.table([f"P={peak}", "Median program (ms)", "Median increments/s"], [[r["implementation"], fmt(r["median_program_ms"]), fmt(r["median_throughput"])] for r in selected], [5.5 * cm, 5.3 * cm, 6.6 * cm])
    best = min(selected, key=lambda r: float(r["median_program_ms"]))
    doc.paragraph(f"Trong bảng này, {best['implementation']} nhanh nhất theo median, {fmt(best['median_program_ms'])} ms. Mọi biến thể đều kiểm final value K và checksum của returned old values. Counter CAS có thể retry khi xung đột; FAA biểu diễn trực tiếp RMW tăng; lock-based counters thêm acquire/release. Tất cả vẫn chia sẻ một giá trị cần cập nhật nên tăng P không đồng nghĩa tăng parallel useful work.")
    doc.paragraph("CAS-backoff thay đổi thời điểm retry, có thể giảm cạnh tranh nhưng thêm thời gian chờ. Không dùng diagnostic shared retry counter trong performance hot loop để tránh làm sai comparison. Lock-free của atomic được ghi riêng theo môi trường; kết quả nhanh/chậm không chứng minh wait-free hay starvation-free.")

    doc.page(); doc.heading("9. Tái lập, giới hạn và kết luận")
    doc.paragraph("Chạy từ root repo sau khi có compiler C++20 và CMake >=3.20. C++ code không cần thư viện ngoài; Python >=3.10 dùng cho runner và analysis. Cài requirements để vẽ hình/xuất PDF. Run directory phải mới; runner từ chối ghi đè dữ liệu cũ.")
    doc.code("cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release\ncmake --build build/release -j 4\nctest --test-dir build/release --output-on-failure\npython3 -m pip install -r assignments/assignment1/scripts/requirements.txt")
    doc.code("python3 assignments/assignment1/scripts/run_benchmarks.py \\\n  --bin-dir build/release/assignments/assignment1 \\\n  --matrix assignments/assignment1/config/benchmark_matrix.json \\\n  --platform-id my-computer --output results-local/run-01")
    doc.paragraph("Sau đó dùng summarize.py, plot_results.py, create_report.py với các đường dẫn run/summary/figures/checks thực tế. Hướng dẫn chính xác nằm trong README. Chạy lại verify.py và giữ checks.json cùng source fingerprint trước khi tạo report. ZIP được tạo bằng package_submission.py, chứa report, source, tests, config, scripts và dữ liệu; giải nén ở thư mục mới rồi build/test lại.")
    doc.paragraph("Giới hạn: một môi trường managed/ảo hóa, host power và tải ngoài không kiểm soát; chưa đo laptop hay ARM của người nộp; workload serial ngắn chịu ảnh hưởng startup; không có hardware counters hoặc proof bằng model checker. Số liệu không được ngoại suy thành kết quả của máy khác. TSan unavailable nếu được ghi ở bảng kiểm thử là hạn chế công cụ thực tế, không là chứng nhận không có race.")
    doc.paragraph("Bản triển khai dùng đúng atomic/HB để trao payload qua locks và barrier; tests định hướng các lỗi đặc trưng, SC reference và stress bổ sung bằng chứng. Hiệu năng được đối chiếu trên cùng workload/metric thay vì giả định custom luôn hơn standard. Phần người nộp còn cần xác nhận trước nộp lớp là thông tin định danh theo quy định, phiên bản đề/giờ LMS và thí nghiệm trên những máy cá nhân thực có.")
    doc.heading("Nguồn tham khảo", 2)
    for text in [
        "[1] Assignment1_v1_16092026.pdf, 16/09/2026, trang 1-4; hạn trong bản đề: 29/10/2026. Bản gốc trong archive đã cung cấp, checksum ở references/source-manifest.json.",
        "[2] Slides Ch00-Ch07 (gồm Ch02a/Ch02b), 234 trang; Ch03 trang 17-28 cho locks/MCS; Ch04 trang 8-15 cho barrier; Ch02a/Ch02b cho atomics/HB. Trang PDF tính từ 1.",
        "[3] C++20 working draft N4861: atomics.order; atomics.types.operations; thread.barrier.class. https://timsong-cpp.github.io/cppwp/n4861/ (đối chiếu 16/10/2026).",
        "[4] Mellor-Crummey & Scott, Algorithms for Scalable Synchronization on Shared-Memory Multiprocessors, ACM TOCS 1991; pseudocode: https://www.cs.rochester.edu/research/synchronization/pseudocode/ss.html"
    ]: doc.paragraph(text)
    doc.save()
    print(json.dumps({"report_pdf": str((args.output / 'report.pdf').resolve()), "report_md": str((args.output / 'report.md').resolve())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--figures", type=Path, required=True)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font-dir", type=Path)
    generate(parser.parse_args())
