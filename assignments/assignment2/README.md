# Assignment 2: A*, Concurrent Sorted Lists và Parallel Search

C++20 implementation cho [yêu cầu Ass2](docs/requirements.md): A* tuần tự và song song trên road graph thật; heuristic static/dynamic/uncertain; chi phí scalar distance/time hoặc **tập nghiệm Pareto**; concurrent sorted-list sets theo coarse-grained và fine-grained locking. Có correctness tests, oracle Python độc lập, benchmark, plots, report và source ZIP.

Slide, PDF đề và notebook mẫu **không được upload GitHub**. GitHub giữ code và ghi chú tự viết; Báo cáo tiếng Anh: [Assignment 2 PDF](report/Assignment2_Report_EN.pdf) (8 trang). OSM extracts, dữ liệu đo, logs và ZIP giữ cục bộ. Mốc thực nghiệm tham chiếu và giới hạn ở [verification.md](docs/verification.md).

## Đọc theo kiến thức môn học trước

[Bản review cả hai bài theo slide](../../docs/course-review.md) chỉ rõ phần trực tiếp từ slide, phần điều chỉnh theo đề và phần mở rộng. Ưu tiên Ch06 coarse/fine sorted lists → A* discussion tr.7-10 (`f=g+h`, relaxation/predecessor và câu hỏi mở) → Ch04 condition synchronization/termination.

**ALT/landmark là optimization ngoài slide**, được đề cho phép ở phần tùy chọn; code đã đo vẫn mặc định landmark. Dynamic/uncertain lấy bound từ ALT và các công thức epoch/band/Pareto là choices được ghi rõ, không phải công thức giảng viên quy định sẵn. Để theo dõi scalar control trước, chạy `--heuristic zero --objective distance`; sau khi hiểu logic mới đọc phần ALT. Policy zero vẫn dùng chung setup/preprocessing, không gọi đó là end-to-end run không có preprocessing.

## 1. Build và chạy nhanh

Mọi lệnh dưới đây chạy từ **gốc repo**, nơi có `CMakeLists.txt` và `assignments/`. Cần CMake >=3.20, compiler/standard library C++20 (GCC 13.3 đã được kiểm tra), Python >=3.10. C++ và pipeline đo/validate chỉ dùng standard libraries; Matplotlib/ReportLab dùng cho hình/PDF.

```bash
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release
cmake --build build/release -j 4
ctest --test-dir build/release --output-on-failure

build/release/assignments/assignment2/a2_route --graph assignments/assignment2/data/tradeoff.road --engine sequential --objective pareto --heuristic landmark --source 0 --target 3
build/release/assignments/assignment2/a2_route --graph assignments/assignment2/data/tradeoff.road --engine fine --threads 4 --objective pareto --heuristic dynamic --dynamic-period 1 --source 0 --target 3
build/release/assignments/assignment2/a2_bench_set --implementation coarse --threads 4 --operations 20000 --key-range 512 --mix read_heavy
```

`tradeoff.road` là **graph tổng hợp tự tạo để test**, không phải road data thật. Frontier đúng gồm `(2,18)`, `(12,12)`, `(18,2)`, một path cho mỗi vector. Phần road network thật ở bước 3.

Mỗi executable nhận `--help`, trả JSON/exit 0 khi thành công; `--output FILE.json` ghi ra file. Tham số hoặc kết quả sai trả exit khác 0. Generator multi-config có thể thêm `Release/` vào đường dẫn binary; dùng `ctest -C Release`. Root CTest kiểm cả Ass1; bản ZIP riêng Ass2 chỉ build/test Ass2.

## 2. Cấu trúc file và thứ tự đọc code

| File/thư mục trong Ass2 | Vai trò |
| --- | --- |
| [graph.hpp](include/pc/a2/graph.hpp), [graph.cpp](src/graph.cpp) | Directed graph, parser, integer cost, GPS snap, Dijkstra và directed landmark bounds |
| [sorted_list.hpp](include/pc/a2/sorted_list.hpp) | `CoarseList<T>` và `FineList<T>`, safe unlink/reclamation, priority pop |
| [search.hpp](include/pc/a2/search.hpp), [search.cpp](src/search.cpp) | Public search options/results, label registry, priorities, goal pruning, work pool |
| [workers.hpp](include/pc/a2/workers.hpp), [cli.hpp](include/pc/a2/cli.hpp) | Start gate, spawn/join, exception handling, strict CLI và build identity |
| [route_main.cpp](src/route_main.cpp), [set_main.cpp](src/set_main.cpp) | Hai CLI và timers/JSON |
| [tests](tests/) | Sorted-set histories, exhaustive path oracle, directed concurrency tests, CLI và analysis |
| [scripts](scripts/) | OSM download/convert; independent oracle; verification; đo/summary/hình/PDF/ZIP |
| [config](config/) | Smoke, pilot, reference matrices |
| [docs](docs/) | Requirements, design, testing, benchmarking, review cuối |
| [data](data/) | Synthetic fixture; hướng dẫn road data thật |

Để học theo slide: đọc `sorted_list.hpp` với Ch06 trước; tiếp theo `graph.hpp` (data model) và `search.hpp/cpp` với A* discussion; sau đó entry points/tests. Phần `LandmarkBounds` trong `graph.cpp` đọc sau cùng như mở rộng. [Design](docs/design.md) giải thích invariants, admissibility, dominance và termination.

## 3. Dữ liệu đường thật và truy vấn tùy ý

Đã thử một OSM extract TP.HCM trong bbox `south=10.770, west=106.685, north=10.785, east=106.705`; đây là một vùng nhỏ, **không phải toàn TP.HCM**. Download/convert mới:

```bash
python3 assignments/assignment2/scripts/download_osm.py --bbox 10.770 106.685 10.785 106.705 --output results-local/hcm.osm
python3 assignments/assignment2/scripts/prepare_data.py --osm-xml results-local/hcm.osm --output results-local/ass2-hcm-data --name "HCM OSM extract bbox 10.770,106.685,10.785,106.705"
```

Overpass cần Internet, snapshot có thể thay đổi. Giữ `network.road`, metadata, raw XML và SHA của lần đo để tái lập. Script từ chối ghi đè output. Có thể chuyển một file OSM XML/XML.bz2 đã tải sẵn qua `--osm-xml`. Bỏ `--osm-xml` để tải fixture **West Oakland** của OSMnx, kiểm pinned Git blob SHA trước khi dùng; đó là dataset riêng, không được gọi là TP.HCM.

Output gồm `network.road`, `metadata.json`, `queries.json`. Ba query mặc định chọn các node cực trị trong largest strongly connected component để tránh chỉ đo unreachable pairs. Parser/search vẫn xử lý graph disconnected và one-way.

Ví dụ GPS trong vùng extract:

```bash
build/release/assignments/assignment2/a2_route --graph results-local/ass2-hcm-data/network.road --engine coarse --threads 4 --objective time --heuristic uncertain --source-lat 10.773 --source-lon 106.688 --target-lat 10.782 --target-lon 106.702
```

Mỗi endpoint có ba cách chọn, không trộn cho cùng endpoint:

| Cách | Cờ |
| --- | --- |
| Index nội bộ `0..V-1` | `--source INDEX`, `--target INDEX`; mặc định 0 và V-1 |
| OSM node ID có trong graph | `--source-osm-id ID`, `--target-osm-id ID` |
| Tọa độ snap tới node gần nhất | `--source-lat LAT --source-lon LON`, tương tự target |

GPS snap chỉ tìm node gần nhất trong graph, không snap vào giữa edge; JSON trả index thực đã chọn. Không có đường thì `paths=[]`; source=target trả path một node, cost `(0,0)`.

Road converter giữ directed segments, one-way `yes/-1`, roundabout, lọc road classes/access đơn giản. Distance là độ dài đoạn cầu làm tròn lên mm; time là ước lượng theo speed road class làm tròn lên ms. **Không phải travel time quan sát hoặc live traffic**; chưa xét turn restrictions. Xem speeds/model trong metadata và [data README](data/README.md). Dữ liệu: © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright).

## 4. Sorted-list API và memory safety

```cpp
#include "pc/a2/sorted_list.hpp"

pc::a2::FineList<int> set; // shared giữa workers
bool added = set.insert(7);
bool present = set.contains(7);
bool removed = set.erase(7);
int smallest;
bool popped = set.try_pop_min(smallest);
```

Set không chứa duplicates. `insert`/`erase` trả liệu trạng thái có thay đổi; `contains` trả membership; `try_pop_min` lấy và xóa min như một operation atomic, false khi rỗng. Comparator phải ổn định và là strict weak ordering. Không trả node pointer ra ngoài.

Coarse dùng một mutex cho mỗi method. Fine dùng lock coupling: giữ current node trong khi lấy successor lock, rồi mới nhả predecessor. Unlink khóa predecessor/current và unlock mutex của victim trước khi delete. `contains` cũng lock coupling; đọc `next` không khóa sẽ là data race. Không cần hazard pointers vì không có traversal không khóa. Khóa theo chiều head→tail; không cam kết fairness/starvation freedom của `std::mutex`.

`snapshot_after_join()` và destructor yêu cầu mọi worker đã dừng/join; snapshot không phải concurrent operation. Không copy/move list đang dùng. Destructor giải phóng chain bằng vòng lặp để tránh recursive deletion của linked nodes.

## 5. A* options, heuristic và vector objective

`a2_route` hỗ trợ mọi tổ hợp sau:

| Option | Giá trị / contract |
| --- | --- |
| `--engine` | `sequential` (heap, threads=1), `coarse`, `fine` (concurrent priority lists) |
| `--threads` | `1..1024`, mặc định 1; thread count thực nên theo máy |
| `--objective` | `distance`, `time`, `pareto` |
| `--heuristic` | `zero`, `landmark`, `dynamic`, `uncertain` |
| `--dynamic-period` | Số accepted-task tickets mỗi epoch, mặc định 64, phải >0 |
| `--max-labels` | Tổng nhãn accepted tối đa, mặc định 1000000, phải >0; vượt thì báo lỗi và cancel |

Graph có cost nguyên không âm; không đổi edge costs trong query. `infinity=UINT64_MAX/4`; các phép cộng kiểm miền finite và báo lỗi nếu vượt. Hai cost components luôn được giữ để replay path, dù chỉ tối ưu một component.

Directed landmark bound cho từng component:

`L(v,t) = max(0, d(l,t)-d(l,v), d(v,l)-d(t,l))` qua hai landmarks, chỉ dùng hạng có cả hai khoảng cách hữu hạn. Preprocessing gồm 8 lần Dijkstra (2 landmarks × 2 hướng × 2 components). Đây là lower bound dùng triangle inequality, không lấy hiệu infinity hay dùng tọa độ độ làm mét.

- `zero`: h=0.
- `landmark`: h=L.
- `dynamic`: h luân phiên `L, floor(L/4), floor(3L/4), floor(L/2)` theo epoch. Key chụp tại khi tạo task; snapshot luôn admissible, không mutate key đang nằm trong list/heap.
- `uncertain`: mô hình khoảng estimate `[floor(L/2), ceil(3L/2)]`, dùng lower endpoint được chứng nhận. Upper estimate không được coi là upper bound của shortest path, không dùng pruning. Đây không phải confidence interval hay stochastic routing.

Đây là cách cụ thể hóa điều kiện mở của đề: h động/uncertain, **edge costs tĩnh**. Muốn mô hình traffic làm costs thay đổi theo departure time cần state/time/FIFO và oracle khác; không tái sử dụng bảo đảm hiện tại cho mô hình đó.

`pareto` giữ mọi cost vector không bị trội, một path đại diện mỗi vector. Không scalar hóa bằng weighted sum. Priority lexicographic chỉ chọn task tiếp theo; dominance là componentwise. Nhãn tốt hơn luôn được reopen, không permanent closed set. Immutable parent/edge IDs tránh đường đi bị thay đổi khi worker khác cải thiện vertex.

## 6. Vì sao queue thread-safe vẫn chưa đủ

Parallel search dùng lock theo vertex để check dominance và publish label cùng nhau; goal frontier có lock riêng. Task key gồm `f snapshot + unique ticket`, không chỉ vertex ID. Stale work có thể bị bỏ hoặc expand dư mà không làm mất nhãn tốt.

**Không dừng ở goal đầu hoặc chỉ vì queue rỗng.** `outstanding` đếm queued + active + reserved-before-publish: tăng trước enqueue, cha chỉ giảm sau khi đã enqueue hết con. Chỉ 0 mới là quiescence. Condition variable dùng version tránh lost wakeup; không có global scheduler lock bao các list operations. Worker exception/label-budget failure cancel, đánh thức người chờ và join trước báo lỗi.

Incumbent pruning chỉ loại nhãn có lower bound bị feasible goal weakly dominate. Các goal được tiếp tục cập nhật tới quiescence. Với integer nonnegative costs và equality dedup, chu trình không tạo thêm nghiệm Pareto cần thiết. Frontier có thể rất lớn; budget không âm thầm xóa bớt nghiệm.

## 7. JSON và thời gian đo

| Field | Ý nghĩa |
| --- | --- |
| `paths` | Cost vector, vertex sequence và edge IDs cho từng nghiệm; scalar có tối đa một path |
| `generated`, `expanded`, `stale`, `pruned`, `max_epoch` | Lượng việc thực tế; thứ tự parallel có thể làm số lượng khác giữa run |
| `query_elapsed_ns` | Allocation/state/search, thread spawn/join, path reconstruction/validation bên trong solver |
| `load_elapsed_ns` | Từ đầu main tới load xong graph; gồm parse CLI |
| `preprocess_elapsed_ns` | Endpoint resolution và landmark preprocessing |
| `end_to_end_ns` | Từ đầu main tới trước xuất JSON; runner còn ghi process wall time gồm startup/I/O |
| `source_sha256`, `build_type`, `sanitizer` | C++/CMake fingerprint và build identity |

Report giữ query time và end-to-end/preprocess riêng. Không dùng Debug/sanitizer để kết luận performance. So `T_seq/T_parallel(P)` và `T_same_engine(1)/T_same_engine(P)` là hai baseline khác nhau, đã tách cột trong summary.

## 8. Correctness, stress và sanitizer

```bash
ctest --test-dir build/release --output-on-failure -R '^a2_'
python3 assignments/assignment2/scripts/verify.py --output validation-local/ass2-check --modes debug release address undefined thread --stress
```

| Test | Oracle |
| --- | --- |
| `a2_lists` | std::set spec, INT64 extremes, insert winner, no lost/duplicate pop, mixed updates, exhaustive serialization của history 12 operations hợp real-time |
| `a2_search` | Exhaustive simple paths trên graph nhỏ, Dijkstra scalar, full Pareto equality; all policy/objective/engine combinations; zero cycles, disconnected, source=target |
| Directed concurrency | Giữ worker trên đường rẻ, cho goal đắt được pop khi queue hết; phải chờ và trả đường tốt hơn; inject exception/budget failure |
| `a2_cli` | 36 tổ hợp logic trên fixture, endpoint/GPS/OSM IDs, input/overflow/invalid graph, K<P cho set workload |
| `a2_tools` | OSM direction/access/missing refs, independent oracle, path corruption; known median/IQR, warmup exclusion, duplicate/missing/corrupt raw rejection |

Default random search tests có 15 seeded graphs, stress tăng lên 60; list histories 20 seeds, stress 100, mixed workload cũng tăng. Runtime checks hoạt động ở Release. History checker không duyệt mọi execution có thể xảy ra; không có exhaustive memory-model checker.

`verify.py` lưu logs/checks.json cho từng mode, CTest gồm cả Ass1 khi có source Ass1. Nếu host thực sự chặn LSan do `/proc`/ptrace, thêm `--disable-leak-detection` để chỉ bỏ leak checks và ghi rõ giới hạn; giữ mặc định trên host hỗ trợ đầy đủ. TSan unavailable không được gọi là đã kiểm race-free.

## 9. Đo, validate, report và ZIP

Chạy smoke trước (không kết luận performance), output directory phải mới:

```bash
python3 assignments/assignment2/scripts/benchmark.py --bin-dir build/release/assignments/assignment2 --graph results-local/ass2-hcm-data/network.road --queries results-local/ass2-hcm-data/queries.json --matrix assignments/assignment2/config/smoke.json --platform-id my-computer --revision working-tree --output results-local/ass2-smoke
python3 assignments/assignment2/scripts/summarize.py --run-dir results-local/ass2-smoke --output results-local/ass2-smoke-summary
```

Reference gồm 324 route configurations + 32 set configurations = 356 cases, mỗi case 1 warmup + 5 measured reps = 2136 samples. Có đủ 4 heuristics × 3 objectives × sequential/P=1 và coarse/fine/P=1,2,4,8 trên 3 query. Điều chỉnh threads theo physical/logical CPUs/quota máy trước khi đo. `pilot.json` chỉ là diagnostic.

```bash
python3 -m pip install -r assignments/assignment2/scripts/requirements.txt
python3 assignments/assignment2/scripts/benchmark.py --bin-dir build/release/assignments/assignment2 --graph results-local/ass2-hcm-data/network.road --queries results-local/ass2-hcm-data/queries.json --matrix assignments/assignment2/config/reference.json --platform-id my-computer --revision working-tree --output results-local/ass2-reference
python3 assignments/assignment2/scripts/summarize.py --run-dir results-local/ass2-reference --output results-local/ass2-processed
python3 assignments/assignment2/scripts/plot_results.py --run-dir results-local/ass2-reference --processed results-local/ass2-processed --output results-local/ass2-figures
python3 assignments/assignment2/scripts/create_report.py --run-dir results-local/ass2-reference --processed results-local/ass2-processed --figures results-local/ass2-figures --checks validation-local/ass2-check/checks.json --output assignments/assignment2/report
python3 assignments/assignment2/scripts/package_submission.py --run-dir results-local/ass2-reference --processed results-local/ass2-processed --figures results-local/ass2-figures --checks-dir validation-local/ass2-check
```

Thay revision bằng Git commit SHA khi đo bản đã chốt. Runner kiểm fingerprint C++/CMake và Release/no sanitizer, giữ mọi failed/timeout sample. Scalar so Python Dijkstra; Pareto so FIFO label-correcting oracle độc lập, replay mọi edge/cost. Summary kiểm lại tất cả rows, warmups, duplicates/completeness; median/inclusive IQR chỉ dùng measured samples. Report bị chặn khi validation/source/checks không khớp. PDF cần DejaVu fonts (hoặc `--font-dir` trỏ tới thư mục DejaVuSans*.ttf).

Set workload read-heavy = 80/10/10, update-heavy = 20/40/40 cho contains/insert/erase, fixed total K, key ranges 64/512. RNG theo worker nên P thay đổi stream partition; không khẳng định cùng operation order. Final invariant không thay semantic correctness histories.

ZIP mặc định `dist/Assignment2_GitGud031005.zip`, gồm source/build/tests/scripts, report, graph input, raw/summary/figures/checks và SHA manifest. Giải nén ở thư mục mới và build/test trước nộp. Chưa tự nộp LMS; bản đề ghi hạn **26/11/2026**. Cần đối chiếu giờ LMS/định danh và chạy benchmark trên các máy cá nhân thực sở hữu. Managed-host reference không thay thế yêu cầu phần cứng đó.
