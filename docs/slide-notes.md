# Ghi chú slide phục vụ Assignment 1

Đã đọc **9 bộ slide, 234 trang PDF**, từ archive người dùng cung cấp. Số trang dưới đây là **thứ tự trang trong PDF tính từ 1**; đôi chỗ khác số in ở footer (ví dụ trang cuối Ch01). Tài liệu nguồn được nhận diện trong [source-index.md](../references/source-index.md).

## 1. Bản đồ đọc và áp dụng

| Bộ slide | Trang PDF | Kiến thức cần giữ | Áp dụng vào Assignment 1 |
| --- | --- | --- | --- |
| Ch00 Motivation | 2-4 | Speedup, Amdahl, chi phí phối hợp và mất cân bằng | Không kỳ vọng tăng thread luôn nhanh hơn; chỉ so speedup khi workload tương ứng |
| Ch01 Consistency | 4-16, 17-30 | SC; cache coherence khác consistency; relaxed ordering; acquire/release; TSO | Lập luận visibility; không dùng tính chất x86 để thay thế C++ synchronization |
| Ch02a Atomics | 6-21 | Data race là UB; atomic types; RMW; CAS weak/strong; expected bị cập nhật; FAA | Building blocks của locks/counters; thiết kế test đúng C++ memory model |
| Ch02b Atomics | 3-18, 19-26 | Happens-before, synchronizes-with, relaxed vs acquire/release vs SC, release sequence, fences, join | Chỉ ra edge publish/observe thay vì dựa vào thứ tự thời gian quan sát được |
| Ch03 Spinlocks | 2-9, 17-29 | Safety/progress/fairness; TAS, TTAS, ticket, MCS; local spinning và queue handoff | Cài TAS/TTAS/MCS, so sánh contention; test nhánh MCS CAS-fail |
| Ch04 Condition Synchronization | 2-15, 16-25, 28-31 | Condition sync; barrier arrival/departure; lỗi reset; sense reversal; các barrier nâng cao; C++20 | Sense-Reversing và chuẩn so sánh `std::barrier`; repeated phase và visibility tests |
| Ch05 Concurrent Objects | 3-19, 22 | Sequential spec; safety/liveness; SC và linearizability; blocking, lock-free, wait-free | Chốt counter contract và linearization point; tránh nhầm spinlock với lock-free |
| Ch06 Blocking Concurrency | 2-3, 12-16, 17-33 | Coarse/fine/optimistic/lazy locking; invariant; memory lifetime; locking order | Mutex counter là coarse-grained object; RAII; lifetime của MCS nodes |
| Ch07 Nonblocking Objects | 3-18, 19-24 | CAS loop; ABA; reclamation; Treiber stack và M&S queue | Dùng CAS đúng; hiểu giới hạn progress/lifetime; stack/queue không thuộc phần bắt buộc |

## 2. Các điểm rút ra theo từng chương

### Ch00: chi phí của song song hóa

Speedup bị giới hạn bởi phần tuần tự và chi phí trao đổi/phối hợp. Critical section có thể biến thành nút thắt, trong khi contention thấp hoặc có useful work bên ngoài có thể làm kết quả khác hẳn. Trong báo cáo phải giải thích hình dạng đường thời gian, không chỉ liệt kê thứ hạng.

### Ch01: coherence chưa đủ

Coherence quản lý các bản sao của một vị trí/cache line; consistency quy định trật tự quan sát giữa nhiều truy cập/vị trí. Viết payload rồi set cờ bằng biến thường không tự tạo giao tiếp hợp lệ trong C++. Acquire/release là điểm nối cần thiết khi trao quyền vào critical section hoặc cho các thread rời barrier.

Pseudocode slide dùng ký hiệu `RW||`/`||RW` để diễn đạt ý tưởng ordering. Khi cài C++ phải ánh xạ bằng các memory orders hợp lệ và lập luận cụ thể; không chép nguyên ký hiệu hoặc mặc định mọi atomic khác nhau có chung một total order.

### Ch02a: atomic vừa là tính nguyên tử vừa là công cụ đồng bộ

- TAS dùng read-modify-write; TTAS thêm load polling để giảm số RMW khi lock đang bận.
- CAS weak có thể thất bại giả; vòng retry phải xử lý đúng cả expected/desired.
- FAA trả về giá trị **trước** phép cập nhật, thuận tiện cho `increment()` trả old value.
- Atomic thông thường có thể không lock-free trên một platform; cần ghi nhận thay vì khẳng định từ tên kiểu.
- Một số bảng nói về giao diện trước C++20. Ví dụ C++20 có `atomic_flag::test`; lựa chọn TTAS của repo dùng `atomic<bool>` để giao diện load/exchange rõ ràng.

### Ch02b: chỉ ra được happens-before

Release trên một atomic đồng bộ với acquire quan sát đúng publication/release sequence tương ứng. Relaxed vẫn nguyên tử trên chính counter nhưng không dùng để publish một payload không atomic khác. Bản counter chỉ cộng số, không trao quyền truy cập dữ liệu phụ, có thể dùng relaxed; lock và barrier phải có ordering mạnh hơn ở đúng điểm.

Thread creation/join và standard mutex đã có quan hệ synchronization. Tuy vậy gate/timer của harness không thay thế correctness của thuật toán chạy trong vòng lặp.

### Ch03: khác biệt cấu trúc giữa ba locks

| Lock | Cách chờ | Điểm nghẽn / lưu ý |
| --- | --- | --- |
| TAS | RMW liên tục trên một cờ chung | Cache line liên tục đổi quyền ghi khi nhiều thread tranh chấp |
| TTAS | Đọc cờ khi bận, RMW để thử lấy lock | Đỡ RMW trong lúc chờ, vẫn có nhiều contenders cùng thử khi unlock |
| MCS | Node queue riêng; chờ trên cờ của chính node | FIFO theo thứ tự enqueue, thêm chi phí node và handoff; scheduler vẫn ảnh hưởng |

Nhánh quan trọng ở Ch03 trang 25-27: unlock thấy `next == nullptr` chưa đủ kết luận không có successor. Thread kế tiếp có thể đã đổi `tail` nhưng chưa nối `prev->next`; CAS tail thất bại thì phải chờ liên kết xuất hiện rồi handoff.

FIFO nói về thứ tự enqueue vào hàng đợi, không phải thứ tự timestamp bên ngoài trước lời gọi lock. TAS/TTAS không có cam kết FIFO/starvation freedom. Các giả định tiến triển của scheduler và owner phải được nêu rõ.

### Ch04: barrier phải dùng lại được

Hai cách barrier sai ở trang 10-13 minh họa reset counter hoặc reset flag quá sớm khiến phase chồng nhau. Sense reversal tách thế hệ bằng cờ chung và local sense. Cần thử nhiều episode và thread chạy nhanh/chậm khác nhau.

Trong C++ dự kiến, chuỗi `fetch_sub(acq_rel)` tập hợp publication của các arrivals; thread cuối reset count rồi release-store sense; thread chờ acquire-load sense. Local sense phải riêng cho từng worker/instance. Nâng cấp dissemination/tree/split-phase là kiến thức mở rộng, chưa cần cài cho Assignment 1.

### Ch05: correctness khác performance và progress

Sequential specification cho biết increment trả gì và state đổi ra sao. Linearizability yêu cầu một điểm có hiệu lực nằm trong khoảng invocation-response, tôn trọng các thao tác không chồng lấp. Test đếm đúng cuối cùng hữu ích nhưng chưa đủ chứng minh toàn bộ lịch sử đúng.

Spinlock vẫn là blocking synchronization: owner bị dừng có thể chặn người chờ, dù người chờ bận quay thay vì ngủ. Lock-free của CAS counter phụ thuộc primitive atomic thực tế và không có nghĩa mọi thread xong trong thời gian hữu hạn có chặn trên.

### Ch06: invariant và lifetime quan trọng hơn số lượng locks

Mutex counter dùng một lock cho toàn bộ state là coarse-grained design phù hợp với bài này. Dùng scope guard để trả lock đúng cả các đường thoát. MCS tuy không cấp phát/xóa node mỗi operation vẫn cần lifetime ổn định đến hết release; không để vector di chuyển node có atomic giữa lúc worker chạy.

Các linked-list variants minh họa race ở việc xóa node và validation; không mở rộng phạm vi bài sang cài concurrent set.

### Ch07: CAS không tự giải quyết mọi vấn đề

Treiber stack cho thấy CAS thành công chưa đủ nếu gặp ABA và lifetime sai. M&S queue minh họa helping khi cập nhật nhiều pointer. Với counter chỉ tăng, giới hạn tổng phép tăng dưới miền `uint64_t` loại tình huống wraparound trong thí nghiệm, và không cần hazard-pointer/reclamation subsystem. Đây không phải lý do để áp dụng CAS lên mọi pointer mà bỏ qua quản lý bộ nhớ.

## 3. Thứ tự đọc lại khi triển khai

1. Memory ordering: Ch01 trang 21-29 → Ch02a trang 9-21 → Ch02b trang 3-18, 22-26.
2. Locks: Ch03 trang 7-9, 17-28, đặc biệt MCS trang 25-27.
3. Barrier: Ch04 trang 8-15 và 28-31.
4. Counter specification: Ch05 trang 5-7, 15-19; Ch02a trang 16-21.
5. Thảo luận giới hạn: Ch00; Ch06 phần invariant/lifetime; Ch07 phần ABA/progress.

## 4. Nguồn đối chiếu thêm

Đã đối chiếu các quyết định C++20 với working draft N4861 và thuật toán gốc của nhóm Rochester. Các nguồn này bổ sung cho slide, không thay đổi yêu cầu của đề:

- [N4861: atomic ordering](https://timsong-cpp.github.io/cppwp/n4861/atomics.order).
- [N4861: atomic operations, gồm compare-exchange](https://timsong-cpp.github.io/cppwp/n4861/atomics.types.operations).
- [N4861: class template barrier](https://timsong-cpp.github.io/cppwp/n4861/thread.barrier.class).
- [Mellor-Crummey & Scott: scalable synchronization pseudocode](https://www.cs.rochester.edu/research/synchronization/pseudocode/ss.html).

Ngày kiểm tra: 15/10/2026. Dùng draft C++20 cố định để tránh nhầm các thay đổi của draft mới hơn với toolchain của project.
