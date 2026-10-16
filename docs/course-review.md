# Review Ass1 và Ass2 theo slide môn học

Ngày review: 16/10/2026. Bản code được review: commit `f521f5b941d3155c98ca22b0eff43a931fa7f1de`. Lượt này dùng slide và đề đã cung cấp làm chuẩn chính, không tìm thêm thuật toán trên web. Số trang bên dưới là thứ tự trang PDF từ 1. Không đưa slide/đề/notebook gốc lên GitHub.

## Kết luận và thứ tự ưu tiên

**Chưa phát hiện sai lệch thuật toán cốt lõi so với kiến thức slide trong phạm vi các contracts đã ghi.** Ass1 đi trực tiếp từ TAS/TTAS/MCS, sense reversal, atomic CAS/FAA và acquire/release. Ass2 dùng đúng coarse/fine-grained sorted list; phần A* tiếp nối `f=g+h`, relaxation, predecessor và các câu hỏi mở ở trang 10. Không có căn cứ thay lõi đã kiểm chỉ để làm code trông giống từng dòng pseudocode.

Có điểm phải nói rõ hơn: **ALT/landmark không nằm trong bộ slide đã cung cấp**. Đây là optimization thêm, được phép bởi phần 4 của đề Ass2, không được trình bày như nội dung đã học hoặc điều kiện bắt buộc. Dynamic/uncertain policies và Pareto là các mô hình repo lựa chọn để trả lời phần mở của đề, không phải công thức được slide quy định sẵn.

Khi học/trình bày: đi từ slide → invariant/specification → code C++ → lý do điều chỉnh → test → kết quả đo. Trình bày ALT và tooling ở phần bổ sung sau cùng.

## 1. Ass1: đối chiếu từng nội dung

| Nội dung | Slide gốc | Code | Review |
| --- | --- | --- | --- |
| TAS | Ch02a tr.9-10; Ch03 tr.17 | [tas_lock.hpp](../assignments/assignment1/include/pc/locks/tas_lock.hpp) | `test_and_set(acquire)` chỉ vào CS khi old flag=false; `clear(release)` nhả lock. Đúng mẫu atomic_flag trong slide. |
| TTAS | Ch03 tr.18 | [ttas_lock.hpp](../assignments/assignment1/include/pc/locks/ttas_lock.hpp) | Poll bằng load khi đang bận, sau đó RMW để tranh quyền. Load relaxed chỉ là hint, không cho vào CS; successful exchange acquire mới nhận quyền. |
| MCS | Ch03 tr.20-28, đặc biệt tr.25-27 | [mcs_lock.hpp](../assignments/assignment1/include/pc/locks/mcs_lock.hpp) | Tail exchange, nối next, chờ flag của chính node, handoff cho successor. Có đủ queue-empty và enqueue-gap release paths. Node/context ổn định và riêng từng worker/lock. |
| MCS dùng strong CAS | Ch02a tr.16-18; Ch03 tr.25-27 | Nhánh tail→null trong `release` | CAS ở đây chỉ thử một lần. Weak spurious failure không chứng minh có successor; chờ next sau lỗi giả có thể kẹt. Dùng strong là ánh xạ đúng sang API C++. |
| Memory ordering | Ch01; Ch02b tr.9-18,21-24 | Các locks/barrier headers | Chỉ ra đúng publication/observation. Không dùng coherence/x86 hoặc riêng một relaxed flag để bảo vệ plain payload. |
| Sense-Reversing Barrier | Ch04 tr.8-15, đặc biệt tr.14 | [sense_reversing_barrier.hpp](../assignments/assignment1/include/pc/barriers/sense_reversing_barrier.hpp) | Local sense, counter arrivals và global sense riêng; reset counter trước publish sense. Reusable phases không bị lẫn. |
| Mutex counter | Ch05 tr.3,5-6 | [mutex_counter.hpp](../assignments/assignment1/include/pc/counters/mutex_counter.hpp) | Cùng một lock bao toàn bộ state operation, trả giá trị trước khi tăng. `value()` cũng khóa khi cho phép đọc đồng thời. |
| CAS counter | Ch02a tr.16-18 | [cas_counter.hpp](../assignments/assignment1/include/pc/counters/cas_counter.hpp) | Weak CAS được retry; failure cập nhật expected; desired được tính lại từ expected mới. Successful CAS là điểm cập nhật số đếm. |
| FAA counter | Ch02a tr.19-21 | [faa_counter.hpp](../assignments/assignment1/include/pc/counters/faa_counter.hpp) | `fetch_add` trả old value đúng semantics slide; RMW là một operation atomic. |
| Progress/fairness | Ch03 tr.7-9; Ch05 tr.18-19 | Contracts trong [Ass1 README](../assignments/assignment1/README.md) | Spinlock vẫn blocking; TAS/TTAS không hứa FIFO; MCS FIFO theo enqueue, có giả định tiến triển. Không gọi toàn bộ chương trình lock-free chỉ vì có CAS. |
| Baselines và workload | Ch04 tr.28-31; đề Ass1 tr.1-3 | [benchmarks](../assignments/assignment1/benchmarks/) | std::mutex/std::barrier là baseline được đề cho phép. Prime workload giữ naive division và một call trong CS, W calls ngoài CS. Barrier không useful work. |

### Các khác biệt với pseudocode là hợp lý

| Slide | Code | Vì sao vẫn cùng thuật toán |
| --- | --- | --- |
| Barrier count tăng từ 0, FAI trả P-1 ở người cuối | Remaining giảm từ P, fetch_sub trả 1 ở người cuối | Cùng đếm đủ P arrivals trước reset và đổi sense. |
| Sense/local sense ban đầu true | Cả hai ban đầu false | Giá trị ban đầu tùy chọn; quan trọng là bằng nhau trước phase đầu và local sense đảo mỗi phase. |
| Reordering fences trong pseudocode | Acquire/release/acq_rel trên atomic operations phù hợp | Theo Ch02a/b; cần chứng minh happens-before, không yêu cầu có một lệnh fence riêng cho mọi ký hiệu. |
| TTAS có thể thử TAS trước rồi mới poll | Repo poll trước rồi mới exchange | Cùng ý tưởng test trước khi RMW; successful RMW vẫn quyết định mutual exclusion. |
| Counter mẫu dùng SC mặc định | Bản số đếm độc lập dùng relaxed; có SC reference trong tests | Ch02b tr.10-18: atomicity của số đếm khác publication của payload. Không dùng relaxed counter này như cờ hoàn thành dữ liệu khác. |

MCS có **hai** đường truyền protected payload: waiting release/acquire khi handoff, và tail release-CAS/acquire-exchange khi queue đã về rỗng. Barrier thread cuối nhận dữ liệu trước arrivals qua chuỗi acq_rel RMW, rồi release sense cho các thread khác. Không chỉ viện dẫn “mọi biến đều atomic”.

Backoff pause tăng theo cấp số nhân là lựa chọn implementation; ví dụ sleep trong đề không phải yêu cầu bắt buộc dùng đúng sleep_for. Bounded delay, reset per operation và tên policy đã ghi rõ; không đồng nhất số pause với số nanosecond.

## 2. Ass2: đối chiếu từng nội dung

| Nội dung | Slide/đề gốc | Code | Review |
| --- | --- | --- | --- |
| Đồ thị, g/h/f | A* discussion tr.4,7-9 | [graph.cpp](../assignments/assignment2/src/graph.cpp), [search.cpp](../assignments/assignment2/src/search.cpp) | g cộng edge cost của đúng path; task key là g+h; parent/edge IDs tái tạo path. Không trộn cost giữa các branches. |
| Dijkstra control | A* discussion tr.8 | `dijkstra`, policy `zero`, Python oracle | h=0 cho uniform-cost ordering; control so chất lượng, không thay thế toàn bộ yêu cầu A*. |
| Sorted-set invariant | Ch06 tr.4-13 | [sorted_list.hpp](../assignments/assignment2/include/pc/a2/sorted_list.hpp) | Sorted/unique, membership qua reachability; API không lộ pointer nội bộ. Structural head và null tail thay numeric sentinels, vẫn kiểm null và giữ invariant. |
| Coarse locking | Ch06 tr.14-16 | `CoarseList` | Một mutex giữ trong toàn bộ mỗi method. Link mutation và read membership nằm dưới lock. |
| Fine locking | Ch06 tr.17-24 | `FineList::locate/insert/erase/contains` | Khóa predecessor/current, lock coupling theo head→tail. `contains` cũng khóa; không để pointer gap không bảo vệ. |
| Lifetime khi remove | Ch06 tr.13,18-23 | Fine-list erase/pop-min | Unlink dưới hai locks, unlock victim mutex trước destroy, giữ predecessor để ngăn traversal mới. Không áp dụng delete tức thì cho một traversal không khóa. |
| Linearizability | Ch05 tr.15-17 | [test_lists.cpp](../assignments/assignment2/tests/test_lists.cpp) | Bounded-history checker so sequential set/pop-min spec và real-time precedence. Final sorted list một mình chưa đủ chứng minh linearizability. |
| Priority adaptation | Đề Ass2 tr.2; A* discussion tr.12 | Task `(f,ticket,label)`, `try_pop_min` | Pop+remove atomic; hai labels cùng vertex được phân biệt. Unique ticket dùng ý tưởng atomic next_id ở Ch02a tr.21. |
| Điều kiện kết thúc song song | Ch04 tr.2-4,26 và đề yêu cầu sửa A* khi kết hợp list | `WorkPool` | Vận dụng condition synchronization/termination detection, đếm queued+active+reserved. Không chỉ nhìn queue rỗng. |
| Shared state | Ch02b và Ch06 | Node-state locks, goal lock, immutable labels | Dominance check/update là một transaction dưới lock; immutable parent tránh chain bị worker khác sửa. Queue thread-safe không tự làm registry thread-safe. |
| h động/uncertain, f vector | A* discussion tr.10; đề tr.1 | `heuristic_value`, `dominates`, registry/goal frontier | Cần mô hình cụ thể và điều chỉnh thuật toán. Công thức epoch scale, estimate band, objectives distance/time và Pareto là choices của repo; slide không quy định sẵn chúng. |

### Vì sao không chép nguyên closed set và first-goal stop

Trang 10 của tài liệu A* yêu cầu kiểm correctness của pseudocode và đặt câu hỏi cho h dynamic/uncertain, f vector. Vì vậy các điều chỉnh sau có cơ sở trong chính tài liệu môn:

- Reopen khi có g tốt hơn; không bỏ vĩnh viễn một node chỉ vì từng được expand. Admissible h chưa đủ để suy consistent h, nhất là khi h thay đổi.
- Immutable label/parent và stale-entry handling là cách thực hiện relaxation khi có nhiều labels/threads.
- Với vector objective, lựa chọn ở đây là componentwise Pareto dominance; lexicographic queue chỉ quyết định thứ tự task, không thay Pareto bằng mục tiêu scalar.
- Bản parallel không dừng ở goal đầu: worker khác có thể giữ task thuộc đường tốt hơn. Hoàn tất khi không còn queued, active hoặc reserved task; incumbent pruning chỉ dựa trên lower bound hợp lệ.

Ví dụ scalar cho nhu cầu reopen, không cần thuật toán từ nguồn ngoài: cạnh `s→a=3`, `s→b=1`, `b→a=1`, `a→t=3`; đặt `h(a)=0`, `h(b)=3`, `h(t)=0`. h admissible nhưng inconsistent. A* có thể expand a (g=3) trước b (f=4); sau b, a được cải thiện thành g=2. Đóng a vĩnh viễn sẽ bỏ đường tốt giá5 và giữ đường giá6. Reopen xử lý đúng cải thiện này.

`outstanding` của solver là **số work items**, còn ví dụ termination detection ở Ch04 tr.26 đếm active threads. Đây là vận dụng điều kiện “không còn nguồn sinh việc”, không phải chép y hệt ví dụ. Mutex/CV/version là chi tiết thực hiện C++ bổ sung. Quiescence trong scheduler cũng không tự chứng minh quiescent consistency/linearizability của một object; hai khái niệm không được đánh đồng.

## 3. Phần nào được học, phần nào được chọn/thêm

| Nhóm | Phạm vi | Cách trình bày |
| --- | --- | --- |
| Trực tiếp từ slide | TAS/TTAS/MCS; sense reversal; atomic CAS/FAA; acquire/release; coarse/fine sorted list; f=g+h, relaxation/predecessor; safety/progress/linearizability | Nội dung chính của bài và phần giải thích/bảo vệ |
| Điều chỉnh để đáp ứng đề và đúng C++ | Stable contexts, strong CAS một lần, reopen/stale labels, multi-label Pareto, priority pop-min, active-work accounting, mutex/CV, integer costs | Nêu invariant, giả định và vì sao pseudocode cần điều chỉnh |
| Mô hình do repo lựa chọn | Dynamic theo search epochs; uncertain estimate band; static edge costs; distance/time, Pareto interpretation | Công khai giả định; không nói giảng viên đã quy định đúng các công thức này |
| Mở rộng ngoài slide | ALT/landmark bounds | Bonus theo phần optional của đề Ass2; không gọi là kiến thức slide, không thay nội dung A*/concurrent-list chính |
| Công cụ thực hiện | OSM import/snap, CLI, hashes, CMake, sanitizers, oracle scripts, plotting/PDF | Giúp chạy và kiểm chứng; không tự chứng minh thuật toán đúng |

Cụ thể với code hiện tại, `SearchOptions` và CLI vẫn mặc định `landmark`, và các policy dynamic/uncertain lấy L từ landmark bounds. **Đây là lựa chọn tối ưu hóa của phiên bản đã đo**, không phải default được slide chỉ định. Có policy `zero` để học đường điều khiển g/relaxation độc lập với công thức ALT. CLI vẫn precompute bounds ở policy zero do dùng chung setup; không được nói run zero không chịu preprocessing cost ở metric end-to-end.

Không khẳng định đã dùng Euclidean heuristic trong bản hiện tại: tọa độ dùng để snap/plot, còn h là landmark-derived hoặc zero. Euclidean heuristic trong notebook mẫu không được lấy độ lat/lon rồi coi là mét. Nếu sau này thay bằng heuristic hình học phải làm rõ đơn vị và admissibility, không tự gắn tên “theo slide” cho một hàm chưa có.

Uncertain upper estimate không được bảo đảm chứa shortest distance thật; chỉ lower endpoint có bound hợp lệ. Code hiện tại chỉ materialize lower endpoint để search, không có phân phối xác suất hay sampling uncertainty. Dynamic h ở đây không làm road edge costs đổi theo traffic/time. Những giới hạn này đã được ghi, cần giữ trong báo cáo và khi giải thích bài.

Không chuyển nguyên phát biểu độ phức tạp scalar A* ở slide sang multi-label Pareto hoặc bản reopen: số labels có thể tăng rất lớn, không có bảo đảm O(E log V) cho mọi cấu hình hiện tại. Không khẳng định MCS/fine-grained/parallel luôn nhanh hơn chỉ từ lý thuyết.

## 4. Lộ trình học và giải thích ưu tiên slide

1. Ass1: đọc TAS → TTAS → MCS theo Ch03; giải thích cả enqueue gap và hai publication paths. Sau đó barrier theo Ch04 tr.10-15, rồi counter theo Ch02a/Ch05.
2. Ass2: đọc invariant và coarse/fine list theo Ch06 trước; giải thích tại sao một node lock hoặc contains không khóa không đủ.
3. Theo dõi scalar g, h, f, relaxation và predecessor theo A* tr.7-10. Chạy policy zero để thấy g và test oracle trước; sau đó xem h ảnh hưởng thứ tự task.
4. Từ câu hỏi mở ở trang10, nêu mô hình dynamic/uncertain và Pareto, vì sao cần reopen/multiple labels. Từ condition synchronization ở Ch04, giải thích active-work termination khi nhiều workers.
5. Cuối cùng mới giải thích ALT như một lựa chọn tạo admissible lower bound thêm. Không cần biết ALT để giải thích mutex/list correctness hay khung A*.

Ví dụ control chỉ dùng binary đã có, chạy từ gốc repo:

```bash
build/release/assignments/assignment2/a2_route --graph assignments/assignment2/data/tradeoff.road --engine sequential --threads 1 --objective distance --heuristic zero --source 0 --target 3
build/release/assignments/assignment2/a2_route --graph assignments/assignment2/data/tradeoff.road --engine fine --threads 4 --objective distance --heuristic zero --source 0 --target 3
```

Hai lệnh phải trả distance cost2 trên fixture. Chúng là control giúp hiểu scalar flow; không thay thế kiểm dynamic/uncertain/vector hoặc real-road requirements của đề.

## 5. Chứng cứ và phạm vi kết luận lượt này

Đã đọc lại code algorithms, tests, workload/timers và đối chiếu trực tiếp các trang nói trên. Source C++/headers/CMake giữ nguyên so với bản đã review; chỉ sửa tài liệu nguồn kiến thức và thứ tự đọc. Vì vậy số đo cũ vẫn gắn đúng kernel/build revision cũ; không đổi tên hay tái gán kết quả.

Kết quả chạy lại trong lượt review này:

| Kiểm tra | Kết quả |
| --- | --- |
| Configure/build/CTest Release | 10/10 groups passed, gồm 6 Ass1 và 4 Ass2 |
| Configure/build/CTest TSan | 10/10 groups passed, không có race finding |
| Scalar control h=0, sequential P1 và fine P4 | Cả hai trả đúng distance2 trên fixture |
| Ví dụ reopen trong mục2 | Tính độc lập: permanent-closed trả6, reopen trả5, shortest=5 |
| Fingerprint Ass1 hiện tại | `582f0be6e5f8aca6b8d197c0fc62b078c7d98e0a7dc23e011f9c24302311ea3f`; binary/source khớp |
| Fingerprint Ass2 hiện tại | `be4e1d367d9ed5b625172ad4189899b07672c8b877dfc13fe5347f0e3fa5727f`; binary/source khớp bản đã đo |

Logs/checks lưu cục bộ trong `validation-local/slides-review-20261016/`. Các mode sanitizer/stress đầy đủ trước đây được ghi trong verification của từng bài; không gọi chúng là vừa chạy lại ở lượt này. Tests hỗ trợ kiểm tra thực thi, không phải lý do duy nhất kết luận đúng kiến thức hoặc chứng minh mọi interleaving. Review logic/happens-before là bằng chứng riêng.

Những phần ngoài môi trường này vẫn chưa hoàn tất: đo trên mọi máy cá nhân thực có, đối chiếu định danh/giờ LMS và nộp bài. Mô hình mở của Ass2 cần được giải thích khi nộp; không có căn cứ khẳng định nó là cách duy nhất giảng viên mong muốn.
