# Thiết kế triển khai và memory ordering

Thiết kế này đã được cài đặt và đối chiếu bằng directed tests, SC reference, stress và các sanitizer chạy được. Kết quả ở [verification.md](verification.md), logs sinh cục bộ; kiểm thử hữu hạn không thay thế lập luận tính đúng. Kết hợp [slide notes](../../../docs/slide-notes.md), yêu cầu gốc và các contracts dưới đây. Mỗi thay đổi thuật toán phải cập nhật lập luận và test liên quan.

## 1. Công nghệ và ranh giới module

- C++20, `std::thread`, `std::atomic`, `std::chrono::steady_clock`; CMake cho build.
- Header thuộc namespace `pc`, đặt trong `include/pc/{locks,barriers,counters,common}`.
- `src/workload.cpp` chứa naive primality workload. Không bật LTO cho benchmark chính; giữ workload ở translation unit riêng.
- Benchmarks và tests là các executable riêng. Chọn implementation trước hot loop bằng template/dispatch bên ngoài, tránh virtual call theo mỗi operation.
- `std::mutex` và `std::barrier` qua adapter dùng cùng harness và workload.
- Thư viện bên ngoài chỉ cần cho plotting sau M4; không thêm dependency runtime C++ nếu chưa có lý do.

## 2. Contract cho locks

API thống nhất đang dùng:

```cpp
using ThreadContext = /* context riêng của worker cho lock này */;
void acquire(ThreadContext& context);
void release(ThreadContext& context);
```

TAS/TTAS/standard mutex dùng context rỗng; MCS có `Node`. `ScopedLock<Lock>` giữ tham chiếu lock và context, acquire ở constructor và release ở destructor. MCS không bị ép vào một node static dùng chung cho nhiều lock.

Quy ước: lock không recursive; cùng worker/context thực hiện acquire-release tương ứng; không copy/move object đang dùng; không hủy lock khi còn worker. Context và node được cấp phát trước khi spawn threads, địa chỉ ổn định đến sau join. Tránh resize/move container chứa node atomic trong khi chạy.

### TAS và TTAS

| Biến thể | State | Lấy lock | Trả lock |
| --- | --- | --- | --- |
| TAS | `atomic_flag`, khởi tạo clear | `test_and_set(acquire)` cho tới khi giá trị cũ là false | `clear(release)` |
| TTAS | `atomic<bool>{false}` | Load relaxed khi bận; `exchange(true, acquire)` để tranh lock; retry khi thất bại | `store(false, release)` |
| Standard adapter | `std::mutex` | `lock()` | `unlock()` |

Load relaxed của TTAS chỉ giúp quyết định có nên thử, không tự trao quyền vào CS. Chỉ RMW thành công mới là bước acquire. TAS/TTAS không hứa FIFO.

### MCS: state, lifetime và ba đường release

`tail` là atomic pointer tới node cuối. Mỗi node có atomic `next` và atomic `waiting`. Khởi tạo node trước khi publish; dùng vùng nhớ riêng cho mỗi worker và từng lock/context cần tồn tại đồng thời.

| Bước | Memory order đã cài | Lý do |
| --- | --- | --- |
| Reset `node.next=nullptr`, `node.waiting=true` | relaxed, trước publish | Worker sở hữu context; chuẩn bị node cho lần acquire mới |
| `tail.exchange(&node)` | acq_rel | Publish node; acquire từ lần unlock làm tail về null nếu queue rỗng |
| `predecessor->next.store(&node)` | release | Cho predecessor thấy node đã khởi tạo |
| Poll `node.waiting` | acquire | Nhận quyền CS và payload từ predecessor |
| Đọc/poll `node.next` ở release | acquire | Quan sát publication của successor |
| CAS `tail` từ node hiện tại thành null | success release, failure relaxed | Publish CS trên đường queue trở rỗng; dùng expected pointer riêng |
| `successor->waiting.store(false)` | release | Handoff CS cho successor |

Release xử lý đúng cả ba trường hợp:

1. `next != nullptr`: đã biết successor → publish handoff.
2. `next == nullptr` và CAS tail về null **thành công**: queue rỗng → return.
3. `next == nullptr` và CAS **thất bại**: successor đã enqueue nhưng chưa nối link → chờ `next` rồi handoff.

Dùng `compare_exchange_strong` cho nhánh CAS một lần này. Không coi spurious failure của weak CAS là bằng chứng có successor rồi chờ vô hạn. Không truyền con trỏ node gốc vào tham số expected để nó bị CAS ghi đè ngoài ý muốn.

Hai đường publication cần giải thích trong report: (a) owner → successor qua waiting release/acquire; (b) owner làm tail rỗng → người acquire tiếp qua tail release-CAS/acquire-exchange. Chỉ giải thích đường (a) là chưa đủ.

MCS FIFO theo thứ tự tail exchange trong các giả định tiến triển phù hợp. Không cam kết thời gian chờ hữu hạn thực tế dưới mọi lịch CPU. Alignment/padding node có thể giảm false sharing; nếu dùng 64 bytes phải ghi đó là lựa chọn cấu hình, không giả định mọi CPU có cache line 64 bytes.

## 3. Sense-Reversing Barrier

Contract: `participants > 0`, số participant cố định; mỗi worker tham gia đúng một lần trong mỗi phase. Không hỗ trợ drop/cancel ở custom barrier trong bản bắt buộc. Barrier chỉ bị hủy sau khi các workers dừng.

State đã cài đặt:

- `const participants`: số thread tham gia.
- Atomic `remaining`, khởi tạo bằng participants.
- Atomic `global_sense`, khởi tạo false.
- Context riêng của mỗi worker **cho từng barrier instance**, `local_sense=false` ban đầu.

Thuật toán đang dùng:

1. Đảo local sense.
2. `remaining.fetch_sub(1, acq_rel)`; giá trị cũ bằng 1 cho biết đây là thread cuối.
3. Thread cuối: reset remaining về participants (relaxed), rồi `global_sense.store(local_sense, release)`.
4. Các thread khác: chờ `global_sense.load(acquire) == local_sense`.

Chuỗi RMW acq_rel trên remaining tập hợp các ghi trước khi arrivals; release-store sense truyền chúng tới acquire-load của người chờ. Reset counter đi trước publication của sense, để lượt kế tiếp không mất arrivals. Cần giải thích cả trường hợp thread cuối tự tiếp tục mà không poll sense.

Không dùng một `thread_local bool` static duy nhất cho mọi instance: cùng thread có thể xen kẽ hai barrier với lịch phase khác nhau. Context tường minh tránh nhầm này.

Adapter standard dùng `std::barrier<>` và `arrive_and_wait()`; context rỗng, cùng tập worker. Mục tiêu custom là cùng ý nghĩa reusable phase và visibility cần cho workload, không tái hiện mọi API/drop/completion của standard barrier.

## 4. Concurrent counters

Contract dùng cho cả tests và benchmark:

```cpp
std::uint64_t increment(ThreadContext& context); // trả giá trị TRƯỚC khi tăng
std::uint64_t value(ThreadContext& context);
```

Khởi tạo 0. Nếu cần reset thì chỉ được reset khi không còn operation chạy đồng thời. Validation đầu vào đảm bảo tổng tăng và phép nhân tính tổng không overflow; phép đo không chạy tới wraparound.

| Counter | Cách làm | Điểm tuyến tính hóa / ordering |
| --- | --- | --- |
| `mutex_tas` | `uint64_t` thường dưới TAS | Lệnh tăng trong CS; lock acquire/release |
| `mutex_ttas` | Tương tự với TTAS | Lệnh tăng trong CS |
| `mutex_mcs` | Tương tự với MCS context | Lệnh tăng trong CS |
| `mutex_std` | `std::mutex` | Lệnh tăng trong CS |
| `cas` | Load + CAS weak loop tăng 1 | CAS thành công; relaxed/relaxed cho counter số thuần |
| `faa` | `fetch_add(1, relaxed)` | RMW đó; trả old value |

`value(context)` của counter lock-based cũng phải giữ lock nếu cho phép đọc khi đang tăng; context phải có lifetime đủ cho acquire-release, kể cả khi caller là main. Atomic counter bỏ qua context và đọc bằng atomic load. Đọc kết quả cuối sau join không cần ordering để publish payload khác: join đã đồng bộ việc kết thúc worker.

CAS: khi thất bại, expected được cập nhật; desired phải tính lại từ expected mới. Relaxed ở đây là lựa chọn cho counter không bảo vệ dữ liệu phụ; không tái sử dụng nguyên thiết kế này làm cờ publish một object khác.

Ghi `is_lock_free()` cho atomic integer, bool và pointer liên quan trên từng máy. Không gọi toàn bộ chương trình lock-free chỉ vì một biểu thức dùng CAS. Counter CAS có thể phải retry vô hạn ở một thread; không suy ra wait-free từ benchmark.

## 5. Backoff và các mở rộng

Sau correctness gate, ưu tiên thêm `ttas_backoff` và `cas_backoff` như biến thể tách riêng. `delay = min(max_delay, 2*delay)` phải được viết tránh overflow; reset delay sau operation thành công. Log initial/max delay, policy, seed nếu randomized.

Tách tên policy: busy pause/yield và `sleep_for` có tác động khác nhau; ví dụ sleep nanosecond trong đề không đảm bảo OS ngủ đúng từng nanosecond. Không bật backoff ngầm cho mọi baseline và không mặc định nó luôn nhanh hơn.

Barrier-backoff, TAS-backoff, Pthreads/OpenMP, tree barrier, fairness diagnostic sâu hơn là mở rộng tùy thời gian. MPI-3 RMA chỉ nghiên cứu nếu M6 đã sẵn sàng: cần phân biệt put/get với completion/flush và memory model của window, rồi mới port từng cấu trúc. Không thay yêu cầu RMA bằng một lời gọi `MPI_Barrier` rồi coi là đã port thuật toán.

## 6. Cách triển khai memory orders có kiểm soát

1. Tạo bản correctness dễ kiểm tra với SC; ghi invariant và đường handoff.
2. Đưa memory orders đề xuất vào từng operation, kèm comment nói nó đồng bộ với operation nào.
3. Chạy lại cùng test/stress/sanitizer sau mỗi thay đổi. Nếu có ARM thật thì thêm vào máy test; không giả lập kết quả ARM từ x86.
4. Duy trì lập luận HB riêng với performance results. Finite tests không chứng minh đúng với mọi execution; sanitizer cũng không thay thế lập luận ordering.

Nguồn bổ sung: [atomic ordering N4861](https://timsong-cpp.github.io/cppwp/n4861/atomics.order), [atomic operations N4861](https://timsong-cpp.github.io/cppwp/n4861/atomics.types.operations), [Rochester pseudocode](https://www.cs.rochester.edu/research/synchronization/pseudocode/ss.html). Các memory orders ở trên là lựa chọn thiết kế C++ của project, cần được review khi cài đặt, không phải mã nguyên văn từ pseudocode.
