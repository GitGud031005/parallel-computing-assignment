# Thiết kế và lập luận correctness

Các choices cụ thể hóa điều kiện mở của đề, xem [requirements](requirements.md). Đối chiếu Ch06 PDF trang 4-24, Ch05 trang 15-19, Ch02a/b atomics và A* discussion trang 7-10. Không copy pseudocode mẫu có lỗi thành code chạy.

## Nguồn kiến thức và thứ tự ưu tiên

Xem [review theo slide](../../../docs/course-review.md). Coarse/fine lists và khung f=g+h là nội dung môn; reopen, priority labels và active-work accounting là điều chỉnh được giải thích để đáp ứng phần mở/song song. ALT/landmark là optimization thêm ngoài slide, không phải yêu cầu bắt buộc. Công thức dynamic/uncertain và Pareto objectives là mô hình đã chọn, cần công khai giả định. Code/default đã đo được giữ nguyên; đọc phần ALT sau khi nắm list và A* core.

## Graph và heuristic

Directed finite graph, hai nonnegative integer costs. Các phép cộng kiểm finite domain, infinity không tham gia arithmetic thường. Landmark distances được tính trên graph và reverse graph cho từng component. Triangle inequality cho `d(L,t)-d(L,v)` và `d(v,L)-d(t,L)` là lower bounds, max với 0 vẫn admissible; hạng chứa infinity bỏ qua. Bound của mỗi component có thể đến từ landmark khác, vẫn là componentwise lower bound, không cần cùng một path tối ưu cả hai.

Dynamic scale luôn trong [0,1], làm tròn floor theo integer nên từng snapshot vẫn admissible. Queue key immutable; không đột ngột sửa một key làm hỏng sorted invariant. Giá trị h mới không buộc mọi snapshot cũ được rekey để giữ correctness: chúng vẫn lower bounds, nhưng thứ tự search có thể khác một scheduler dùng h mới nhất. Không dùng permanent closed set, vì dynamic snapshots có thể inconsistent.

Uncertain interval [floor(L/2),ceil(3L/2)] là mô hình estimate band; chỉ lower end được chứng nhận. Upper không được dùng prune hoặc tuyên bố bound được true remaining cost. Nếu không có certified lower endpoint thì dùng 0. Không giả định một stochastic model mà chưa được cung cấp.

## Labels và Pareto

Label immutable chứa vertex, g pair, parent và incoming edge ID. Registry của một vertex giữ antichain dưới objective đang chọn. Check dominance, đánh dấu dominated labels và thêm mới xảy ra trong cùng node mutex. Bằng cost thì dedup, nên zero cycles không sinh vô hạn nhãn tương đương. Đường có cycle không âm bị prefix trước cycle dominate tại cùng vertex; mỗi nondominated vector có đại diện simple path. Graph hữu hạn có hữu hạn simple paths, dù số nhãn có thể exponential. Budget là error/cancellation, không approximate frontier.

Scalar dominance chỉ xét component objective. Pareto xét cả hai. Lexicographic f + unique ticket chỉ là processing order, không quyết định mục tiêu. Task key có ticket để hai paths/epochs tại cùng vertex không bị loại nhầm bởi sorted set uniqueness. Cải thiện prefix reopen; immutable parent tránh ghép parent chain không nhất quán. Path replay kiểm directed edge ID và cộng cả hai components.

Feasible goal q weakly dominating g+h của label l có nghĩa mọi extension của l không cải thiện q trong objective tương ứng. Prune như vậy an toàn, kể cả goal q sau đó bị goal tốt hơn dominate. Với vector, không dừng ở goal đầu; giữ goal antichain. Goal set được cập nhật dưới mutex riêng, đọc bound cũng giữ mutex, không có plain-data race.

## Concurrent lists và reclamation

Coarse: một lock bảo vệ mọi state; mutation của link là linearization point. Fine: mọi đọc next đều giữ node lock; giữ predecessor trong khi khóa current; bước tới successor vẫn giữ current. Các locks được lấy theo chiều tăng thứ tự list. Insert giữ predecessor/current; erase giữ cả hai, unlink, unlock victim mutex, delete trong khi predecessor còn khóa. Không thể có traversal khác giữ một pointer tới victim mà không có một trong các locks ngăn erase lấy đủ hai lock. Không có lock-free traversal nên không cần deferred reclamation/hazard pointers.

Structural head sentinel không chiếm INT64_MIN/MAX. Tail là null được kiểm trước dereference. Destructor iterative, chỉ sau join. Snapshot chỉ sau join; không tuyên bố snapshot concurrent linearizable. Comparator/key immutable là precondition. Lists là blocking, fairness của mutex/scheduler không được tăng thành guarantee starvation-free.

## Parallel work accounting và publication

`outstanding = queued + active + reserved`.

- Push reserve bằng atomic increment trước khi queue publication.
- Pop chuyển queued sang active nên không đổi count.
- Active parent chỉ complete sau khi toàn bộ con đã reserve/publish.
- Count về 0 nghĩa không còn task hoặc parent có thể phát sinh task: quiescence.

Empty queue với outstanding>0 phải chờ. First parallel goal không chứng minh optimality khi có task in-flight với lower bound thấp hơn. Solver dùng safe incumbent pruning và tiếp tục tới quiescence, không cần lấy min đồng thời của toàn bộ active tasks.

Queue insert/pop dùng chính locks của list, không được bao một global scheduler mutex. Wait mutex chỉ bảo vệ version và CV coordination; version được lấy trước thử pop, check lại dưới lock trước wait để không mất notification. Publication của task payload qua list mutex; outstanding atomic không thay thế bảo vệ list hoặc label registry. Dead-end/unreachable search làm task count hết và đánh thức mọi waiter.

Exception trong worker hoặc enqueue làm cancel và notify_all; mọi thread được join trước rethrow. Start gate độc lập queue, thread creation failure mở gate và joins các threads đã tạo. Không có abandon làm các waiter chờ vô hạn. Các test ép in-flight/first-goal và failure paths; tests hữu hạn không thay formal model checker.

## Mẫu được điều chỉnh

Notebook mẫu trộn graph multiedge attrs, g/f và thời gian của các branches, heuristic tính từ degree coordinates so với length meters, và closed set không reopen. Bản mới dùng explicit typed graph, per-label costs, matching heuristic units/lower bounds và immutable paths. Hàm h động được mô phỏng theo accepted-task epochs, không được gọi là dynamic edge-cost/traffic solver.

Nguồn bổ sung về landmark bounds: [Goldberg & Harrelson](https://www.microsoft.com/en-us/research/publication/computing-the-shortest-path-a-search-meets-graph-theory/). Về multiobjective shortest paths: [T-MDA paper](https://arxiv.org/abs/2110.10978); implementation này là label-correcting A* reference, không tuyên bố tái hiện T-MDA.
