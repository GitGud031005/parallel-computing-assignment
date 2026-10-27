# Assignment 1 — Shared-memory Synchronization

Project C++20 cài đặt TAS/TTAS/MCS, Sense-Reversing Barrier và concurrent counters bằng mutex/CAS/FAA. Có baseline `std::mutex`/`std::barrier`, TTAS/CAS exponential backoff, correctness tests và pipeline benchmark/report. MPI-3 RMA là phần tùy chọn, chưa triển khai.

Báo cáo nộp là `Assignment1_Report.pdf` ở gốc ZIP, viết bằng LaTeX theo template HCMUT. Số liệu đo, hình và kết quả kiểm tra nằm trong [results](results/README.md).

## Đọc theo kiến thức môn học

Các thuật toán bám theo slide môn học, theo thứ tự: atomics và memory order → TAS/TTAS/MCS → sense-reversing barrier → đặc tả và progress của concurrent counter. Mục 2 của báo cáo tóm tắt kiến thức nền này, mục 3 giải thích chỗ cài đặt C++ khác pseudocode và vì sao.

## 1. Build và chạy nhanh

Chạy mọi lệnh dưới đây từ **thư mục gốc repo**, nơi có `CMakeLists.txt` và `assignments/`. Cần CMake >=3.20, compiler cùng standard library hỗ trợ C++20 `std::barrier`, Python >=3.10 để chạy đủ 6 nhóm test/scripts. Phần C++ chỉ dùng standard library; Linux/WSL2 là môi trường tham chiếu. GCC 13.3 đã build thành công; trên toolchain khác CMake sẽ probe `std::barrier`.

```bash
cmake -S . -B build/release -DCMAKE_BUILD_TYPE=Release
cmake --build build/release -j 4
ctest --test-dir build/release --output-on-failure

build/release/assignments/assignment1/bench_locks --implementation mcs --threads 4 --mode fixed_total --total-operations 20000 --prime-n 997 --outside-work 1
build/release/assignments/assignment1/bench_barriers --implementation sense_reversing --threads 4 --episodes 20000
build/release/assignments/assignment1/bench_counters --implementation cas --threads 4 --total-operations 1000000
```

Mỗi benchmark hỗ trợ `--help`, in một JSON, hoặc ghi file bằng `--output path.json`. Thành công trả exit code 0; sai tham số hoặc kết quả sai trả khác 0. Với generator nhiều configuration, executable có thể nằm thêm trong `Release/`; điều chỉnh đường dẫn và dùng `ctest -C Release`.

## 2. Cấu trúc code và thứ tự đọc

| Đường dẫn trong Ass1 | Vai trò |
| --- | --- |
| [include/pc/locks](include/pc/locks/) | TAS, TTAS, MCS, adapter standard mutex và RAII guard |
| [include/pc/barriers](include/pc/barriers/) | Sense-Reversing và adapter standard barrier |
| [include/pc/counters](include/pc/counters/) | Mutex counter, CAS counter, FAA counter |
| [include/pc/common](include/pc/common/) | Spin hint/backoff, worker harness, CLI, checked arithmetic, build fingerprint |
| [src/workload.cpp](src/workload.cpp) | Naive `is_prime()` dùng chung cho mọi lock |
| [src/environment.cpp](src/environment.cpp) | Probe build và khả năng lock-free của atomics |
| [benchmarks](benchmarks/) | Ba entry points locks, barriers, counters |
| [tests](tests/) | Correctness, CLI và phép tính analysis |
| [config](config/) | Ma trận smoke, pilot và reference benchmark |
| [scripts](scripts/) | Build/test → đo → validate → summary → plots → report → ZIP |
| [results](results/README.md) | Số liệu đo trên laptop, hình và kết quả kiểm tra |

Nên đọc `workload.cpp` → `tas_lock.hpp` → `ttas_lock.hpp` → `mcs_lock.hpp` → `sense_reversing_barrier.hpp` → ba counters. Sau đó đọc benchmark tương ứng và test của nó. Lập luận happens-before cho từng thuật toán nằm ở mục 3 của báo cáo.

## 3. Locks: API, lifetime và workload

| CLI `--implementation` | C++ type | Cơ chế |
| --- | --- | --- |
| `tas` | `pc::TasLock` | Lặp `atomic_flag.test_and_set(acquire)`, clear release khi nhả |
| `ttas` | `pc::TtasLock` | Poll relaxed khi bận, rồi thử exchange acquire |
| `mcs` | `pc::McsLock` | Queue node theo worker, chờ flag của chính node |
| `std_mutex` | `pc::StdMutex` | Adapter cho `std::mutex` |
| `ttas_backoff` | `pc::TtasBackoffLock` | TTAS, pause backoff sau failed exchange |

API chung là `acquire(context)`/`release(context)`. Dùng RAII để luôn nhả lock khi thoát scope:

```cpp
#include "pc/locks/mcs_lock.hpp"
#include "pc/locks/scoped_lock.hpp"
#include <cstdint>

pc::McsLock lock;                  // chia sẻ giữa các workers
std::uint64_t protected_value = 0; // mọi truy cập đồng thời đều giữ lock

// Bên trong mỗi worker, có context riêng cho lock này:
pc::McsLock::ThreadContext context;
{
    pc::ScopedLock guard(lock, context);
    ++protected_value;
}
```

Context MCS phải có địa chỉ ổn định và sống tới khi `release()` hoàn tất. Mỗi worker dùng context riêng cho **từng lock**; không share/move node đang hoạt động, không recursive acquire. Chỉ hủy lock sau khi join workers. Các lock không có API cancel/try-lock.

TTAS load relaxed chỉ là gợi ý; successful exchange mới cho phép vào CS. MCS xử lý đủ ba nhánh release: có successor, queue rỗng, successor đã đổi tail nhưng chưa nối `next`. CAS một lần ở unlock dùng **strong** để không nhầm spurious failure với successor thật. Payload truyền qua waiting release/acquire, hoặc qua tail release-CAS/acquire-exchange khi queue rỗng.

MCS FIFO theo thứ tự enqueue tại tail exchange. TAS/TTAS không hứa FIFO. Busy-wait lock vẫn là blocking theo progress condition: owner bị dừng có thể giữ tất cả người chờ.

Mỗi iteration gọi `is_prime(N)` **một lần trong lock**, sau đó `W = outside-work` lần ngoài lock. Hàm thử ước từ `2` tới `N-1`, dừng sớm khi thấy ước; không dùng sqrt optimization trong benchmark. Hàm ở translation unit riêng, benchmark tắt IPO để giữ workload ở vị trí cần đo; không thêm LTO vào phép đo chính.

| Mode | Cờ | Tổng critical sections `K` |
| --- | --- | --- |
| `per_thread` | `--iterations-per-thread I` | `P × I`; mặc định `I=10000` |
| `fixed_total` | `--total-operations K` | Cố định `K`; mặc định `K=100000`, chia quotient/remainder cho workers |

Không truyền hai cờ workload cùng lúc. `N` mặc định 997, miền CLI `2..UINT32_MAX`; `W` mặc định 0; `P` trong `1..1024`. `W=0/1/2` cho tỷ lệ số lời gọi trong CS là `1`, `1/2`, `1/3`; không phải tỷ lệ thời gian đảm bảo.

Với `N` nguyên tố, checksum phải là `K × (W+1)`; với hợp số là 0. Checksum xác nhận workload, còn mutual exclusion/visibility được kiểm bằng tests riêng.

```bash
build/release/assignments/assignment1/bench_locks --implementation ttas_backoff --threads 3 --mode per_thread --iterations-per-thread 1000 --prime-n 997 --outside-work 2
```

## 4. Barrier: phase và local sense

Chọn `--implementation sense_reversing|std_barrier`, `--threads P`, `--episodes E` (mặc định 10000). Tất cả `P` workers gọi barrier đúng `E` lần; vòng benchmark không chứa useful work giữa các lần gọi.

```cpp
#include "pc/barriers/sense_reversing_barrier.hpp"

pc::SenseReversingBarrier barrier(participants); // participants > 0, cố định
// Mỗi worker giữ context riêng cho barrier instance này:
pc::SenseReversingBarrier::ThreadContext context;
barrier.arrive_and_wait(context);
```

Không dùng chung local sense cho nhiều barrier instances. Mỗi worker tham gia đúng một lần ở mọi phase, không được bỏ cuộc giữa chừng. Thread cuối reset counter trước khi publish sense release. RMW acq_rel tập hợp dữ liệu trước arrivals; acquire-load sense cho thread chờ nhận dữ liệu đó. Thread cuối đã acquire qua chuỗi RMW.

`E` là số **episode toàn cục**, số arrivals là `P × E`. Throughput dùng `E / (worker_elapsed_ns / 1e9)`, đơn vị episodes/s; không nhân thêm `P`.

## 5. Counters: giá trị cũ và ordering

| CLI `--implementation` | C++ type |
| --- | --- |
| `mutex_tas`, `mutex_ttas`, `mutex_mcs`, `mutex_std` | `pc::MutexCounter<Lock>` với lock tương ứng |
| `cas` | `pc::CasCounter` |
| `faa` | `pc::FaaCounter` |
| `cas_backoff` | `pc::CasBackoffCounter` |

Mọi counter khởi tạo 0; `increment(context)` trả **giá trị trước khi tăng**, `value(context)` đọc hiện tại. Có thể truyền giá trị ban đầu vào constructor. API không có reset; tạo instance mới sau khi workers đã dừng. Mutex counter khóa cả increment lẫn value.

```cpp
#include "pc/counters/cas_counter.hpp"

pc::CasCounter counter;
pc::CasCounter::ThreadContext context; // riêng cho worker
// Nếu đây là operation đầu tiên thì old == 0:
auto old = counter.increment(context);
auto now = counter.value(context); // có thể đã tăng tiếp bởi worker khác
```

CAS tính lại desired từ expected mới sau mỗi thất bại; FAA dùng `fetch_add(1, relaxed)`. Relaxed đủ cho **số đếm độc lập**, không dùng counter làm cờ publish payload khác. Atomic `uint64_t` có lock-free hay không tùy platform; xem executable `pc_environment`.

Benchmark dùng tổng cố định `--total-operations K` (mặc định 100000), chia đều cả khi `K < P`. Final value phải bằng `K`; checksum giá trị cũ bằng `K(K-1)/2` modulo `2^64`. Correctness tests mạnh hơn: thu đủ old values và kiểm đúng tập `[0,K)`. Hợp đồng thư viện yêu cầu counter không wrap; CLI kiểm miền số và overflow khi tính workload.

Backoff TTAS/CAS là pause theo cấp số nhân `1..1024`, giới hạn trên và reset mỗi operation; đây là số bước pause, không phải nanosecond cố định.

## 6. Đọc JSON và hiểu thời gian đo

| Field | Ý nghĩa |
| --- | --- |
| `program_elapsed_ns` | Từ trước spawn tới sau join, gồm ready/start gates và công việc workers |
| `worker_elapsed_ns` | Từ worker bắt đầu sớm nhất tới worker kết thúc muộn nhất |
| `total_operations` | Tổng critical sections của locks hoặc increments của counters |
| `episodes` | Số barrier episodes toàn cục |
| `checksum`, `final_value` | Oracle khi áp dụng; field không dùng là null |
| `source_sha256`, `build_type`, `sanitizer` | Dấu vân tay C++/CMake và cấu hình binary |

`program_elapsed_ns` là metric chính cho locks/counters theo đề; không bao gồm parse CLI, cấp phát trước timer, kiểm kết quả sau join hay xuất JSON. Barrier dùng worker time cho throughput và vẫn giữ cả hai timers. `steady_clock` tránh clock wall-time bị chỉnh. Không dùng sanitizer/Debug để kết luận performance.

Strong-scaling speedup chỉ tính `T(1)/T(P)` khi cùng implementation, tổng `K`, `N`, `W`, source và platform. Với `per_thread`, tổng việc tăng theo `P`; ratio thời gian đó không phải strong-scaling speedup.

## 7. Correctness và sanitizer

| CTest | Điều cần bắt lỗi |
| --- | --- |
| `workload` | Prime oracle độc lập, partition, checked arithmetic |
| `locks` | Không chồng CS, protected payload, RAII, MCS enqueue-gap/FIFO, nhiều instance |
| `barriers` | No early release, visibility, nhiều phase, hai instances A-A-B |
| `counters` | Final count, toàn bộ old values, concurrent reads, boundary không wrap |
| `cli_validation` | Tất cả variants, input lỗi/overflow, `K < P`, prime/composite |
| `analysis_validation` | Known-answer throughput/speedup/quartiles, CSV sai/duplicate |

Các C++ suites dùng nhiều seeds với `P=1,2,3,4,5,8`, có SC reference cho thuật toán custom, directed hooks và bounded oversubscription. Visibility test của barrier dùng barrier thứ hai trước vòng ghi kế tiếp để bản test không tự race. Runtime assertions vẫn hoạt động trong Release.

```bash
python3 assignments/assignment1/scripts/verify.py --output validation-local/check-01 --modes debug release address undefined thread --stress
```

`verify.py` lưu logs/exit codes/checks.json; `--stress` tăng workload ba C++ suites 10 lần. Output directory phải mới. GCC/Clang cần hỗ trợ sanitizer tương ứng. ASan mode bật cả address và UB checks; thread mode là TSan. Nếu host thực sự chặn LeakSanitizer do `/proc task`/ptrace, có thể thêm `--disable-leak-detection`: chỉ bỏ LSan và ghi giới hạn vào checks, không chứng nhận leak-free. Giữ mặc định trên host hỗ trợ đầy đủ.

Kết quả kiểm tra và giới hạn ở mục 4 của báo cáo và `results/platforms/checks-laptop-02.json`. Test/sanitizer hữu hạn không duyệt hết interleavings và không thay thế lập luận happens-before.

## 8. Benchmark tái lập, report và ZIP

Smoke kiểm wiring trước; chỉ cần Python standard library:

```bash
python3 assignments/assignment1/scripts/run_benchmarks.py --bin-dir build/release/assignments/assignment1 --matrix assignments/assignment1/config/smoke_matrix.json --platform-id my-computer --revision working-tree --output results-local/smoke-01
python3 assignments/assignment1/scripts/summarize.py --run-dir results-local/smoke-01 --output results-local/smoke-summary
```

Smoke có 57 configurations ngắn, không dùng kết luận performance. `pilot_matrix.json` dùng chọn workload. `benchmark_matrix.json` có 711 configurations × (2 warmups + 7 measured reps) = 6399 samples với P = 1–14; `saturation_matrix.json` đo riêng P = 12–16, nơi MCS và barrier spin bị preemption làm sập. Giữ cùng tham số trong mỗi series so sánh.

```bash
A=assignments/assignment1
python3 $A/scripts/run_benchmarks.py --bin-dir build/release/$A --matrix $A/config/benchmark_matrix.json --platform-id my-computer --revision working-tree --output results-local/run-01
python3 $A/scripts/run_benchmarks.py --bin-dir build/release/$A --matrix $A/config/saturation_matrix.json --platform-id my-computer --revision working-tree --output results-local/saturation-01
python3 $A/scripts/summarize.py --run-dir results-local/run-01 --output $A/results/processed
python3 $A/scripts/summarize.py --run-dir results-local/saturation-01 --output $A/results/processed/saturation
python3 $A/scripts/plot_results.py --summary $A/results/processed/summary.csv --output $A/results/figures
python3 $A/scripts/latex_tables.py --run-dir results-local/run-01 --summary $A/results/processed/summary.csv --saturation $A/results/processed/saturation/summary.csv --output $A/report/latex/generated
(cd $A/report/latex && latexmk -pdf -outdir=build main.tex)
python3 $A/scripts/package_submission.py
```

Thay `--revision working-tree` bằng commit SHA đã checkout khi đo bản Git đã chốt; source fingerprint vẫn được kiểm độc lập. Matplotlib chỉ cần cho plots; báo cáo cần TeX Live hoặc MiKTeX có `latexmk`. Hình trong `results/figures` phải được chép vào `report/latex/figures` sau khi vẽ lại.

Runner từ chối binary cũ, Debug, sanitizer và LTO flags đã nhận diện; chạy process tuần tự với thứ tự seeded, giữ cả lỗi/timeout. Summary kiểm checksum, duplicate và tính đầy đủ; bỏ warmup khi tính median/IQR, và một warmup lỗi được ghi lại nhưng không chặn phân tích. Run directory phải chưa tồn tại; không sửa tay raw CSV. Đóng gói lấy `report/latex/build/main.pdf`, từ chối nếu PDF cũ hơn nguồn LaTeX hoặc code C++ được nhúng, rồi tạo ZIP mặc định `dist/Assignment1_GitGud031005.zip` cùng SHA-256 manifest. Đây là ZIP nộp cục bộ, không phải nội dung GitHub.

Số liệu trong báo cáo đo trên laptop của người nộp (Intel Core i7-13620H, 6 P-core + 4 E-core, 16 logical CPUs, Windows 11, MinGW-w64 GCC 13.2), run `run-laptop-02` và `saturation-laptop-01`. Không suy rằng MCS/FAA luôn nhanh nhất từ lý thuyết hoặc một lần đo.

## 9. Khi sửa code

1. Sửa thuật toán kèm cập nhật lập luận invariant/happens-before trong báo cáo.
2. Build và chạy test liên quan, toàn bộ CTest, sanitizer phù hợp; dùng directed/stress tests khi đổi synchronization.
3. Rebuild mọi executables sau khi đổi C++/CMake. Runner kiểm fingerprint để tránh đo binary cũ.
4. Benchmark vào thư mục mới, tạo lại summary/hình/report; không gắn kết quả source cũ cho source mới.
5. Giải nén ZIP ở thư mục khác và build/test trước nộp. Đối chiếu bảng yêu cầu ở mục 1 của báo cáo, định danh và giờ LMS. Repo không tự nộp LMS.
