# Review cuối Ass2 - 16/10/2026

Đã đối chiếu lại cả 2 trang Assignment2_v1_30092026, 12 trang A* discussion, notebook mẫu và Ch06/Ch05/Ch02a/b. Bản gốc không đưa lên GitHub. Đây là code review theo invariants và bằng chứng thực thi, không phải formal model checking.

## Yêu cầu và kiến thức

| Điểm kiểm tra | Kết quả |
| --- | --- |
| A* sequential trên mạng đường thật | Directed OSM extract TP.HCM, chọn index/OSM ID/GPS; 3106 nodes, 5350 directed edges |
| h dynamic/uncertain | Admissible snapshots với epoch scale; uncertain chỉ dùng certified lower endpoint. Edge costs tĩnh trong query, không gọi đây là dynamic traffic solver |
| f vector | Full componentwise Pareto frontier, một path/vector; lexicographic queue không scalar hóa objective |
| Hai concurrent sorted sets | Coarse mutex và fine lock coupling theo Ch06 PDF trang 14-24; contains cũng khóa, hai-node deletion và safe lifetime |
| List thành priority structure | Immutable f/ticket/label key, atomic pop-min, uniqueness không chỉ theo vertex |
| Reopen/paths | Không permanent closed set, dominant labels được thay dưới node mutex; immutable parent và incoming edge ID, replay cả hai costs |
| Parallel termination | Queued+active+reserved accounting; không kết thúc bởi empty queue/first goal; CV version tránh lost wakeup |
| Pruning/overflow | Chỉ feasible incumbent dominance với admissible lower bound; finite integer arithmetic kiểm overflow; budget báo lỗi thay vì partial exact |
| Study quality + time/scalability | Mọi tổ hợp policy/objective/engine, 3 queries, P=1/2/4/8; query/preprocess/end-to-end riêng, oracle và medians/IQR |
| All personally owned machines | Chưa thay thế: mới đo managed Linux; pipeline chạy lại đã có |
| PDF/source ZIP, individual, deadline | Report/package script có; bản đề ghi 26/11/2026; chưa nộp LMS/đối chiếu định danh |

## Chứng cứ kiểm thử

Kernel/build source SHA-256: `be4e1d367d9ed5b625172ad4189899b07672c8b877dfc13fe5347f0e3fa5727f`. Đây là hash C++/headers/root+Ass2 CMake, không phải Git commit SHA. Python pipeline được ghi digest riêng trong manifest; README/notes không đổi kernel digest.

| Check | Kết quả thực tế |
| --- | --- |
| Debug, Release, UBSan | Mỗi mode 10/10 CTest groups passed, gồm 6 Ass1 regression groups |
| ASan+UBSan | 10/10 passed sau rebuild các binary build lỗi; LSan tắt rõ ràng do host /proc/ptrace limitation |
| TSan | 10/10 passed sau rebuild một binary build lỗi, không race finding; không skip |
| Release stress lists/search | 2/2 passed |
| Exhaustive search oracle | Tất cả policy/objective/engine combos, 15 random seeds mặc định; stress 60, thêm graph đặc biệt |
| Bounded linearizability histories | 12 ops/history, 20 seeds/list; stress 100; negative fixture kiểm checker |
| Directed in-flight / early goal / exceptions | Giữ đường giá2 khi goal20 đã pop và queue cạn; phải chờ và trả2; budget/exception cancellation passed |
| Independent real-road oracle | Scalar Python Dijkstra, Pareto FIFO label-correcting; replay mọi edge ID và costs |
| Oakland smoke | 68/68 cases, 0 failures; fixture thật riêng, không dùng làm performance HCM |
| HCM diagnostic pilot | 38 cases ×2 reps=76 samples, 0 failures |
| HCM reference | 356 cases, 2136 samples (1780 measured), 0 failures, complete, mọi quality check exact |
| PDF visual QA | 8/8 trang render và kiểm tra: chữ/bảng/hình/citations rõ, không overflow hoặc overlap |
| ZIP độc lập | Kiểm mọi SHA manifest; fresh configure/build Release và 4/4 Ass2 CTest groups passed |
| ZIP offline real-data check | Binary fingerprint khớp; HCM Pareto query khớp oracle; summary lại 2136 raw records offline vẫn complete/exact |

Đợt sanitizer ban đầu có 3 generated executable files không thực thi được (mode0644), trong đó một file rỗng. Đã loại riêng các build artifacts đó, link lại rồi chạy lại toàn bộ 10 groups cho ASan và TSan; C++ source không đổi. Initial-checks/logs được giữ cùng recheck logs, final checks tham chiếu cả hai lần. Đây là lỗi thực thi binary build quan sát được, không bỏ qua sanitizer finding. Không có kết luận leak-free từ LSan.

Raw logs/data/generated PDF không publish GitHub; nằm trong deliverable riêng. Không gắn kết quả cũ với code khác: runner/summary/report kiểm source fingerprint, graph SHA và completeness.

## Kết quả và giới hạn

Trên query west-east, landmark heuristic, median query time (ms):

| Objective | Sequential heap P1 | Coarse P8 | Fine P8 |
| --- | --- | --- | --- |
| Distance | 0.318 | 1.910 | 2.400 |
| Time | 0.652 | 3.080 | 3.240 |
| Pareto | 1.484 | 4.450 | 5.849 |

Cả ba query HCM có lần lượt 5,2,5 Pareto vectors. Tất cả scalar costs/full Pareto sets khớp oracle. Dataset nhỏ và queries ngắn; thread/list synchronization overhead có thể lấn át useful work. Không tuyên bố parallel/fine-grained nhanh hơn, không đo hardware cache counters để khẳng định nguyên nhân phần cứng.

Graph SHA-256: `8a2a67e36e1b010f578b5ec438153c12c0a72c7ac4375ab88e0d06a951297e9a`. Raw reference SHA-256: `5b86da66290c778a8eafeb432076ae4f6ca651a638010219d973abc8b4137cf6`. OSM nguồn thật, © OpenStreetMap contributors, ODbL; estimated travel time theo road class, không live/observed traffic. Extract nhỏ, có clipping boundary, chưa turn restrictions.

Platform: managed Linux x86_64, affinity9 logical CPUs, quota tương đương8 CPUs, power mode không kiểm soát; không gọi là laptop cá nhân. Chưa có ARM/hardware-independent exhaustive proof, chưa chạy các máy cá nhân người nộp. Dynamic/uncertain h là mô hình được chọn, không bao quát mọi mô hình stochastic/time-dependent graph. Label sets có thể exponential; vượt budget/timeout là failed run.
