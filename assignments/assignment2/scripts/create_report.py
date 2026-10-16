"""Write a Vietnamese PDF/Markdown report using verified tests and measured results only."""

import shutil
import argparse, csv, json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)
from reportlab.lib.enums import TA_CENTER
from common import kernel_digest, sha256


def report(args):
    manifest = json.loads((args.run_dir / "manifest.json").read_text())
    validation = json.loads((args.processed / "validation.json").read_text())
    checks = json.loads(args.checks.read_text())
    if (
        not validation["complete"]
        or not validation["quality_exact"]
        or validation["raw_sha256"] != sha256(args.run_dir / "raw.jsonl")
    ):
        raise ValueError("input validation stale/incomplete")
    if (
        len(
            {
                manifest["source_sha256"],
                validation["source_sha256"],
                checks["source_sha256"],
                kernel_digest(),
            }
        )
        != 1
    ):
        raise ValueError("test/data/current source mismatch")
    if any(c["status"] == "failed" for c in checks["checks"]):
        raise ValueError("unresolved failed validation")
    for name in ["routes", "sets", "heuristics", "road_routes", "pareto"]:
        if not (args.figures / (name + ".png")).exists():
            raise ValueError("missing figure")
    rows = list(csv.DictReader((args.processed / "summary.csv").open()))
    route = [r for r in rows if r["suite"] == "routes"]
    first_query = route[0]["query"]
    font_dir = Path("/usr/share/fonts/truetype/dejavu") if args.font_dir is None else args.font_dir
    pdfmetrics.registerFont(TTFont("DV", str(font_dir / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DV-B", str(font_dir / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV", boldItalic="DV-B")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyV", fontName="DV", fontSize=9.4, leading=14, spaceAfter=7))
    styles.add(
        ParagraphStyle(name="TitleV", fontName="DV-B", fontSize=21, leading=27, spaceAfter=16)
    )
    styles.add(
        ParagraphStyle(name="HeadV", fontName="DV-B", fontSize=15, leading=21, spaceAfter=12)
    )
    styles.add(ParagraphStyle(name="SmallV", fontName="DV", fontSize=7.8, leading=11, spaceAfter=4))
    story = []
    md = []

    def title(text):
        story.append(Paragraph(escape(text), styles["TitleV"]))
        md.append("# " + text + "\n")

    def heading(text):
        story.append(Paragraph(escape(text), styles["HeadV"]))
        md.append("## " + text + "\n")

    def para(text):
        story.append(Paragraph(escape(str(text)), styles["BodyV"]))
        md.append(str(text) + "\n")

    def table(data, widths=None):
        formatted = [[Paragraph(escape(str(x)), styles["SmallV"]) for x in row] for row in data]
        t = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#94a3b8")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f8fafc")],
                    ),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 9))
        md.extend(["| " + " | ".join(map(str, row)) + " |" for row in data])
        md.append("")

    def image(name, width=480):
        p = args.figures / (name + ".png")
        w, h = ImageReader(str(p)).getSize()
        story.append(Image(str(p), width=width, height=width * h / w))
        asset = args.output / "figures" / p.name
        asset.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, asset)
        md.append(f"![{name}](figures/{p.name})\n")

    def page():
        story.append(PageBreak())

    title("Assignment 2: A* và Concurrent Sorted Lists")
    para("Parallel Computing | Bản đề 30/09/2026 | Kết quả thực nghiệm ngày 16/10/2026")
    para(
        "Tài khoản dự án: GitGud031005. Báo cáo tham chiếu trong môi trường thực thi hiện có; thông tin định danh người nộp và giờ LMS cần được đối chiếu trước nộp. Không dùng số liệu môi trường này để gắn nhãn là laptop cá nhân."
    )
    table(
        [
            ["Phần", "Sản phẩm"],
            [
                "A* tuần tự",
                "Heap priority, scalar distance/time và Pareto hai mục tiêu; bốn heuristic policies",
            ],
            [
                "Concurrent set",
                "Coarse mutex và fine-grained lock coupling; insert/erase/contains/pop-min",
            ],
            [
                "A* song song",
                "Priority list coarse/fine, node-label locks, reopen và quiescence accounting",
            ],
            [
                "Correctness",
                "Oracle độc lập, exhaustive small graphs, bounded histories, directed tests, sanitizers",
            ],
            [
                "Thực nghiệm",
                "OSM thật tại TP.HCM; quality và execution time, P sweep, raw records/summary/hình",
            ],
        ],
        [100, 380],
    )
    para(
        f"Có {validation['cases']} configurations, {validation['raw_samples']} samples gồm warmups; {validation['measured_samples']} measured samples. Mọi sample đã qua kiểm kết quả và đủ nhóm trước khi tổng hợp. Không triển khai contraction hierarchies."
    )
    para(
        "Phạm vi GitHub: code và tài liệu tự viết. Slide, PDF đề, notebook gốc, raw data và generated report được giữ ngoài phần source publish. ZIP nộp riêng gồm report, source và bằng chứng tái lập."
    )
    heading("1. Mô hình road network")
    meta = json.loads((args.run_dir / "road-metadata.json").read_text())
    para(
        f"Dữ liệu: {meta['name']}. Đồ thị có {meta['vertices']} node, {meta['directed_edges']} cạnh có hướng. Nguồn OpenStreetMap; © OpenStreetMap contributors, ODbL-1.0: https://www.openstreetmap.org/copyright."
    )
    para(
        "Mỗi đoạn nối hai OSM node có cost (distance_mm, estimated_time_ms). Khoảng cách cầu được làm tròn lên mm; thời gian được ước lượng từ speed theo road class rồi làm tròn lên ms. Đây là mô hình tĩnh, không phải dữ liệu giao thông đo thực tế; chưa xét turn restrictions. Giữ hướng one-way/roundabout và connectivity theo OSM node IDs. GPS snap tới node gần nhất, không tự nối hai đường khác cao độ."
    )
    page()
    heading("2. A*, heuristic động/uncertain và f vector")
    para(
        "g là cost thực của đường đã đi, h là lower bound còn lại, f=g+h. Tất cả cost là số nguyên không âm trong miền hữu hạn đã kiểm overflow. Không đóng node vĩnh viễn: nhãn tốt hơn được chấp nhận lại, nhãn cũ bị đánh dấu stale; mỗi nhãn giữ immutable parent và edge ID để tái tạo đúng đường, kể cả parallel edges."
    )
    table(
        [
            ["Policy", "Hàm h được dùng"],
            ["zero", "(0,0), control tương ứng uniform-cost ordering"],
            [
                "landmark",
                "Directed ALT bound: max(0, d(L,t)-d(L,v), d(v,L)-d(t,L)) với các hạng hữu hạn, cho từng mục tiêu",
            ],
            [
                "dynamic",
                "Theo epoch=ticket/period, nhân bound với 1, 1/4, 3/4, 1/2 luân phiên và lấy floor",
            ],
            [
                "uncertain",
                "Khoảng mô hình [floor(L/2), ceil(3L/2)]; chỉ lower endpoint được chứng nhận dùng để xếp/prune",
            ],
        ],
        [95, 385],
    )
    para(
        "Có hai landmarks, mỗi landmark dùng Dijkstra forward/reverse cho hai cost components (tổng tám lần preprocessing). Triangle inequality trên directed shortest distances cho bound nguyên admissible. Infinity không bị lấy hiệu. Dynamic h dùng snapshot khi tạo task; key trong queue không bị sửa. Mọi snapshot vẫn là lower bound nên admissibility không phụ thuộc key có cùng epoch hay không. Epoch mô phỏng thay đổi thông tin heuristic, không thay edge cost giữa query."
    )
    para(
        "Uncertain interval là khoảng ước lượng được chọn cho bài thực nghiệm, không phải xác suất hay confidence interval. Upper estimate không được khẳng định bao được shortest distance và không dùng pruning. Với h không có lower bound tin cậy, policy zero là lựa chọn an toàn. Không tuyên bố đã giải stochastic routing hay time-dependent traffic."
    )
    para(
        "Với f vector, lưu toàn bộ nhãn g không bị trội tại mỗi node. a weakly dominates b khi a_i<=b_i cho mọi component; bằng nhau chỉ giữ một đại diện. Goal frontier dùng cùng dominance. Priority lexicographic (f_distance,f_time,ticket) chỉ quyết định thứ tự xử lý. Không weighted-sum hóa và không dừng ở goal đầu: test (2,18),(12,12),(18,2) giữ cả nghiệm giữa không được weighted sum ưu tiên."
    )
    para(
        "Các lỗi tránh từ notebook mẫu: g_neighbor+h_neighbor phải được tính từ cùng nhánh; không làm thời gian nhánh này đổi nhánh khác; không lấy độ lat/lon rồi coi là mét; MultiDiGraph cần xử lý đúng từng cạnh; không suy optimality khi heuristic có thể overestimate hoặc khi không reopen. Code mới độc lập với notebook mẫu."
    )
    page()
    heading("3. Hai sorted lists và kết hợp song song")
    table(
        [
            ["Cấu trúc", "Đồng bộ và linearization"],
            [
                "CoarseList",
                "Một mutex bảo vệ traversal và thay đổi link. Insert/remove/pop tuyến tính hóa ở link mutation; contains ở so sánh dưới lock.",
            ],
            [
                "FineList",
                "Khóa predecessor/current theo thứ tự head tới tail, giữ current khi chuyển sang successor. Insert/remove khóa cả hai node; contains cũng lock coupling.",
            ],
            [
                "Memory",
                "Không trả node pointer ra ngoài. Unlink dưới hai locks, unlock mutex của victim trước delete; predecessor loại reader mới. Snapshot/destruction chỉ sau join.",
            ],
            [
                "Priority adapter",
                "Task gồm immutable f snapshot, unique ticket và shared immutable label; thêm atomic try_pop_min. Hai label cùng vertex không bị nhầm thành duplicate set key.",
            ],
        ],
        [95, 385],
    )
    para(
        "Sorted list một mình không làm A* đúng khi chạy song song. Registry theo vertex có mutex để dominance check, loại nhãn cũ và thêm nhãn mới là một transaction. Các nhãn immutable và alive atomic chỉ phục vụ bỏ stale work; nhãn bị loại sau khi pop vẫn có thể được expand dư mà không phá correctness. Goal frontier có mutex riêng. Không giữ vertex lock trong queue operation, và không có global scheduler mutex bao mọi insert/pop nên fine list vẫn có concurrency thực."
    )
    para(
        "Outstanding = queued + active + reserved-before-publication. Trước push tăng outstanding; cha chỉ complete sau khi publish hết con. Pop không giảm outstanding. Chỉ khi complete đưa count về 0 mới có quiescence: không còn cha có thể sinh công việc mới. Empty queue trong khi worker đang expand chỉ làm các worker khác chờ, không kết thúc query. Condition variable dùng version dưới wait mutex để tránh lost wakeup; mutex này không bao list traversal."
    )
    para(
        "Goal đầu ở parallel có thể đắt hơn một đường đang được expand. Chỉ prune bằng feasible incumbent weakly dominating g+h; tiếp tục tới quiescence. Với nonnegative costs, dominated prefix không tạo suffix tốt hơn theo cùng objective. Pareto equality loại zero-cost cycles; mỗi vector trả một path đại diện. Label budget báo lỗi và cancel/wake/join mọi worker, không xuất partial frontier như exact result."
    )
    para(
        "Hai lists và solver dùng mutex nên là blocking; không hứa starvation-free do std::mutex không cung cấp bảo đảm fairness chung. Lock order dọc list tránh vòng chờ trong các operation này. Kiểm thử hữu hạn không phải model checking toàn bộ C++ memory model."
    )
    page()
    heading("4. Kiểm chứng correctness và phạm vi chứng cứ")
    table(
        [
            ["Check", "Oracle / kết quả"],
            [
                "C++ lists",
                "So std::set tuần tự; extreme int64 keys; insert winner; pop no missing/duplicate; mixed stress; 12-operation histories duyệt mọi thứ tự hợp real-time.",
            ],
            [
                "C++ search",
                "Vét cạn simple paths trên random graphs nhỏ có cycle/zero edges/disconnected và unsupported Pareto point; so scalar Dijkstra; mọi policy/objective/engine.",
            ],
            [
                "Lịch ép",
                "Giữ worker trên đường rẻ trong khi queue cạn và goal đắt đã pop; solver phải chờ rồi trả cost 2 thay 20. Inject exception và label-budget cancellation.",
            ],
            [
                "Python",
                "Scalar heap Dijkstra và Pareto FIFO label-correcting độc lập với C++ A*/landmarks/lists. Replay node/edge IDs và tổng cost của mọi sample.",
            ],
            [
                "Tools",
                "Input/overflow, GPS/OSM IDs, one-way/access filter; known median/IQR; raw corruption, duplicate/missing sample rejection.",
            ],
        ],
        [95, 385],
    )
    table(
        [["Build/check", "Trạng thái"]] + [[c["mode"], c["status"]] for c in checks["checks"]],
        [240, 240],
    )
    para(
        "CMake root chạy cả Ass1 để phát hiện hồi quy. ASan dùng address+UB checks; LeakSanitizer bị tắt rõ ràng trên host đã biết chặn /proc/ptrace, không có kết luận leak-free từ LSan. TSan status trong bảng là trạng thái thực, unavailable không được tính là race-free. Các tests không chứng minh mọi history hoặc progress dưới mọi lịch CPU."
    )
    para(
        "Quality của mỗi scalar sample phải đúng cost Dijkstra và đường replay hợp lệ. Pareto sample phải bằng toàn bộ tập vector oracle, không chỉ cùng số nghiệm. Các Pareto vectors được đối chiếu với oracle theo từng query; nghiệm là exact trong cost model, không phải dự báo thời gian di chuyển thực."
    )
    para("Source/build SHA-256: " + manifest["source_sha256"])
    para("Graph SHA-256: " + manifest["graph_sha256"])
    page()
    heading("5. Execution time và scalability A*")
    env = manifest["environment"]
    para(
        f"Platform {manifest['platform_id']}: {env.get('cpu_model')}, {env.get('os')}; affinity {len(env.get('affinity') or [])} logical CPUs, cpu.max={env.get('cpu_quota')}. Power mode không kiểm soát. Đây là managed host, chưa thay thí nghiệm trên các máy cá nhân người nộp sở hữu."
    )
    para(
        "Mỗi sample là process riêng. query_elapsed_ns gồm state allocation, search, tạo/join workers và path validation trong solver; graph read và landmark preprocessing được ghi riêng. end_to_end_ns gồm parse/read/preprocess/query tới trước xuất JSON; process_elapsed_ns của runner còn gồm process startup và I/O. Không giấu preprocessing trong kết luận ứng dụng end-to-end."
    )
    image("routes")
    selected = [
        r
        for r in route
        if r["query"] == first_query
        and r["heuristic"] == "landmark"
        and (r["engine"] == "sequential" or r["threads"] == str(max(manifest["matrix"]["threads"])))
    ]
    table(
        [["Objective", "Engine/P", "Median ms", "IQR ms", "S so seq"]]
        + [
            [
                r["objective"],
                r["engine"] + "/" + r["threads"],
                f"{float(r['median_ms']):.3f}",
                f"{float(r['q1_ms']):.3f}-{float(r['q3_ms']):.3f}",
                f"{float(r['speedup_vs_sequential']):.3f}",
            ]
            for r in selected
        ],
        [75, 95, 85, 130, 95],
    )
    para(
        "Speedup so sequential heap và speedup so own P=1 được lưu riêng. Các query nhỏ có thể bị thread startup, list traversal và synchronization lấn át; không mặc định bản song song nhanh hơn. Overhead giải thích này là khả năng hợp lý, không phải đo hardware cache counters. Chỉ so các hàng cùng query/objective/heuristic/graph/source."
    )
    page()
    heading("6. Heuristic và concurrent-set workload")
    image("heuristics")
    para(
        "Heuristic mạnh thường giảm không gian tìm kiếm nhưng không bảo đảm thời gian luôn thấp hơn khi overhead và lịch worker thay đổi. Dynamic policy thay priority snapshots, có thể làm số expanded/generated khác nhau giữa P; quality vẫn phải exact. Không dùng thay đổi số nhãn hoặc frontier cardinality để che mất nghiệm."
    )
    image("sets")
    para(
        "Set benchmark dùng fixed total theo matrix (ghi trong manifest);  read-heavy 80/10/10 và update-heavy 20/40/40 cho contains/insert/erase. Key ranges 64 và 512, khởi tạo các key chẵn; cùng seed và workload giữa variants. RNG theo worker nên khi đổi P, stream partition thay đổi; expected mix giữ nguyên nhưng không khẳng định cùng toàn bộ operation order. Final sorted/unique/range/count là invariant check; semantic linearizability được kiểm riêng bằng histories nhỏ."
    )
    para(
        "Fine-grained locking cho phép operation trên các vùng khác nhau tiến hành đồng thời, đồng thời phải lock nhiều node khi traversal. Vì vậy fine có thể chậm hơn coarse trong workload này; đánh giá dựa vào số đo và IQR, không gán ưu thế tuyệt đối theo tên thuật toán. Các run ngắn có startup/scheduling noise; không tuyên bố hiệu quả cho toàn TP.HCM hoặc mọi road graph."
    )
    page()
    heading("7. Nghiệm đường đi và Pareto frontier")
    image("road_routes", 460)
    image("pareto", 460)
    para(
        "Mỗi đường trong hình đi theo directed edge IDs thật của extract. Cost vector được tính lại từ edges và so với oracle. Các đường có thể trùng phần lớn geometry nhưng khác tradeoff length/road-class speed. Bản đồ chỉ minh họa mô hình routing; OSM extract có ranh giới cắt và không có turn restrictions. © OpenStreetMap contributors, ODbL: https://www.openstreetmap.org/copyright."
    )
    page()
    heading("8. Tái lập, giới hạn và đối chiếu cuối")
    para(
        "README Ass2 ghi lệnh build/test, download/convert OSM, chọn node/OSM ID/GPS, smoke/pilot/reference, summary/plots/report/package. Raw records giữ warmups và mọi lỗi; không sửa tay hoặc xóa outlier theo thứ hạng. Median/inclusive IQR chỉ tính measured repetitions. Report bị chặn nếu source/checks/data không khớp hoặc thiếu sample, quality mismatch, lỗi/timeout."
    )
    para(
        f"Ma trận: P={manifest['matrix']['threads']}, heuristics={manifest['matrix']['heuristics']}, objectives={manifest['matrix']['objectives']}; {manifest['matrix']['warmups']} warmup + {manifest['matrix']['repetitions']} repetitions, timeout {manifest['matrix']['timeout_seconds']} giây/sample, seed {manifest['matrix']['seed']}. Không chạy sanitizer trong performance measurements."
    )
    para(
        "Hạn chế còn lại: một managed hardware platform; cần chạy trên mọi shared-memory machine thực sở hữu. OSM là một extract nhỏ TP.HCM, không phải network toàn thành phố; tốc độ ước lượng theo road class, không giao thông thời gian thực. Dynamic/uncertain là mô hình heuristic đã định nghĩa, không edge-cost dynamics. Pareto labels có thể tăng rất lớn; giới hạn label báo lỗi thay vì cắt frontier im lặng. Chưa model-check và chưa chứng minh progress độc lập scheduler."
    )
    para(
        "Bản đề yêu cầu làm cá nhân, ZIP chứa PDF và Python/C++ source, hạn 26/11/2026. Chưa tự nộp LMS; người nộp đối chiếu giờ đóng cổng và thông tin định danh. Code đã có đủ phần bắt buộc trong mô hình đã nêu; các lựa chọn heuristic/vector là cách cụ thể hóa điều kiện mở của đề."
    )
    heading("Tài liệu tham chiếu")
    for text in [
        "[1] Assignment2_v1_30092026.pdf, trang 1-2; A* discussion PDF, trang 4,7-10,12; notebook osm-astar.ipynb. Bản gốc do môn học cung cấp, giữ ngoài repo.",
        "[2] Ch06 Blocking Concurrency, PDF trang 4-24: sorted-list set, coarse/fine locks và reclamation; Ch05 Concurrent Objects, trang 15-19: linearizability/progress; Ch02a/Ch02b atomics và memory ordering.",
        "[3] Goldberg & Harrelson, Computing the Shortest Path: A* Search Meets Graph Theory, MSR-TR-2004-24 (2004). https://www.microsoft.com/en-us/research/publication/computing-the-shortest-path-a-search-meets-graph-theory/",
        "[4] Maristany de las Casas et al., Targeted Multiobjective Dijkstra Algorithm (2021), https://arxiv.org/abs/2110.10978. Implementation này là label-correcting reference, không tuyên bố tái hiện T-MDA.",
        "[5] OpenStreetMap contributors, ODbL-1.0. https://www.openstreetmap.org/copyright ; fixture West Oakland từ gboeing/osmnx tests/input_data, dùng smoke độc lập, không làm số liệu TP.HCM.",
        "[6] C++20 working draft N4861: mutex/thread/atomic requirements. https://isocpp.org/files/papers/N4861.pdf",
    ]:
        para(text)
    args.output.mkdir(parents=True, exist_ok=True)

    def footer(canvas, doc):
        canvas.setFont("DV", 7)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawString(44, 25, "Parallel Computing | Assignment 2 | managed-host reference")
        canvas.drawRightString(550, 25, str(doc.page))

    doc = SimpleDocTemplate(
        str(args.output / "report.pdf"),
        pagesize=(595.28, 841.89),
        leftMargin=44,
        rightMargin=44,
        topMargin=40,
        bottomMargin=42,
        title="Assignment 2 - A* and Concurrent Sorted Lists",
        author="GitGud031005",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    (args.output / "report.md").write_text("\n".join(md) + "\n")
    print(
        json.dumps(
            {
                "pdf": str((args.output / "report.pdf").resolve()),
                "bytes": (args.output / "report.pdf").stat().st_size,
            }
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["run-dir", "processed", "figures", "checks", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--font-dir", type=Path)
    report(p.parse_args())
