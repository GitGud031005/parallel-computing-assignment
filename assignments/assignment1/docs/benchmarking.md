# Thiết kế thí nghiệm và phân tích

**Protocol đã triển khai.** Matrix thực thi có schema v2, giá trị cụ thể trong [benchmark_matrix.json](../config/benchmark_matrix.json). Raw/metadata giữ riêng cho smoke, pilot và reference run; CSV/summary/report chỉ nói về môi trường thực sự đã đo. Các mục phía dưới còn giữ gợi ý mở rộng ban đầu; khi khác, manifest của run và bảng cấu hình thực tế ngay dưới là authoritative.

## Cấu hình reference đã chốt

| Series | Cấu hình |
| --- | --- |
| Core locks | 5 implementations (TAS/TTAS/MCS/std mutex/TTAS-backoff), P=1/2/3/4/8, N=997, W=0/1/2/4/8 |
| Lock modes | fixed-total K=20000; per-thread I=5000 |
| Sensitivity | N=97/K=200000 và N=10007/K=2000; W=0/4, fixed-total; giữ K giữa algorithms/P trong mỗi series |
| Barriers | Sense-Reversing/std barrier, E=20000, cùng P |
| Counters | 4 mutex + CAS + FAA + CAS-backoff, K=1000000, cùng P |
| Repetition | 2 warmups + 7 measured; seeded order 20261016; 395 configurations, 3555 raw samples |

Đây là reference sweep trên managed Linux với 9 affinity logical CPUs nhưng quota tương đương 8 CPUs; P chính dừng ở 8. Oversubscription có bounded correctness cases riêng, chưa làm performance claims. Pilot được giữ nguyên trong `results/raw/.../pilot-20261016`. Các series ngắn để phủ đủ tham số; không đạt mục tiêu gợi ý 0,5-2 giây cho mọi run. Với workload nhanh, startup/scheduling là phần quan trọng của program metric theo đề, và worker metric được giữ riêng để kiểm tra tác động đó. Không ngụy tạo là thí nghiệm laptop cá nhân.

CLI xuất JSON rồi Python runner lưu từng sample vào raw CSV, bao gồm source fingerprint ngay trong executable, build type và sanitizer. `pc_environment` được đối chiếu current C++/CMake digest; mỗi benchmark sample cũng phải có cùng digest/build mode. Dữ liệu dùng report cần được summarize.py kiểm independent checksum và manifest, đủ repetition, không có failed/timeout chưa xử lý.

## 1. Câu hỏi cần trả lời

1. TAS/TTAS/MCS thay đổi thế nào khi tăng số thread, công việc trong CS và công việc ngoài CS? Standard mutex đứng ở đâu?
2. Sense-Reversing hoàn thành bao nhiêu **episode toàn cục/giây** so với `std::barrier`? Có thay đổi ở ngưỡng physical cores, SMT, oversubscription?
3. Counter mutex/CAS/FAA mất bao nhiêu thời gian để hoàn thành cùng số increments? CAS retry/backoff ảnh hưởng ra sao?
4. Điều gì lặp lại giữa các máy đang có, điều gì phụ thuộc môi trường? Chỉ kết luận trong phạm vi dữ liệu thực tế.

Kỳ vọng như TTAS giảm coherence traffic hay MCS lợi hơn khi contention cao là **giả thuyết để kiểm tra**, không điền trước thành kết luận.

## 2. Khống chế workload và compiler

Giữ naive `is_prime()` trong source file riêng, input `N` đọc từ CLI lúc chạy, không LTO. Mỗi thread cộng kết quả vào checksum cục bộ, main tổng hợp sau join và ghi ra output. Không ghi `std::cout`/CSV, cấp phát, sinh số ngẫu nhiên hoặc đọc đồng hồ theo từng operation trong hot loop.

Checksum một mình chưa đủ nếu compiler nhận ra hàm pure và hoist các lời gọi cùng N. Workload translation unit riêng, không khai báo pure/const attribute, không inline liên module và không LTO là thiết kế ban đầu. Trong pilot kiểm tra optimized assembly hoặc profiler/call instrumentation riêng để xác minh lời gọi vẫn nằm trong/ngoài CS đúng vị trí; probe instrumented không dùng làm kết quả performance.

Không dùng shared volatile accumulator làm sink vì nó gây thêm tranh chấp; `volatile` cũng không phải primitive synchronization. Cùng compiler flags và workload cho mọi implementation trong một comparison.

Prime N dự kiến 97,997,10007 giúp tạo công việc ngắn/vừa/dài vì naive loop đi gần hết miền chia. Thêm composite là phép đo phụ, ghi rõ early exit làm đổi lượng việc. Không so đồ thị của hai N như cùng một workload.

## 3. Thời gian và thước đo

| Nhóm | Metric chính | Quy ước |
| --- | --- | --- |
| Locks | `program_elapsed_ns` | Start ngay trước spawn worker, stop sau join tất cả; bao gồm quản lý threads theo yêu cầu thời gian toàn chương trình |
| Barriers | `episodes_per_second` | E episode toàn cục chia thời gian worker hoàn thành E barriers; không có useful work giữa barriers |
| Counters | `program_elapsed_ns` | Tăng cùng tổng K; cùng biên đo spawn-to-join cho mọi biến thể |

Metric phụ: thời gian workers (`worker_elapsed_ns`) cho locks/counters để thấy startup overhead; throughput operations/s; barrier latency trung bình `worker_elapsed_ns/E`. Đặt tên metric rõ ràng, không trộn primary và secondary trong cùng bảng.

Timer dùng `steady_clock`. Mỗi worker ghi start sau gate, end sau loop vào slot riêng; tổng hợp `max(end)-min(start)` sau join làm worker interval. Gate độc lập với tested algorithm, không đặt custom barrier chưa kiểm tra làm start gate. Compiler/harness overhead được giữ nhất quán giữa các biến thể.

Barrier hot loop chỉ gồm E lần gọi barrier. Không đặt prime, checksum, log, per-episode timestamp hay completion callback làm việc thêm ở giữa. E×P là số **arrivals**, không phải số episodes. Nếu báo arrivals/s thì ghi metric riêng.

## 4. Hai chế độ phân chia công việc

| Chế độ | Tổng việc khi P thay đổi | Cách dùng |
| --- | --- | --- |
| `per_thread` | Locks: P×I critical sections, P×I×(W+1) prime calls | Bám mẫu đề: mỗi thread chạy I vòng; thời gian tăng có thể do tổng việc tăng |
| `fixed_total` | Locks/counters: K operations được chia đều bằng thương + số dư | Strong scaling; so thời gian và speedup trên cùng K,N,W |

Tại cùng P, mọi implementation phải nhận cùng số operations. Với strong scaling, `S(P)=T(1)/T(P)` và efficiency `S(P)/P` chỉ tính trên cùng implementation, cùng fixed-total workload, platform, compiler và timer. Với `per_thread`, ưu tiên throughput hoặc weak-scaling discussion; không gọi `T(1)/T(P)` là strong-scaling speedup.

Barrier dùng E phase như nhau ở mọi P; per-thread gọi E lần nên tổng arrivals là P×E. Đây là phép đo synchronization, không gán Amdahl efficiency như một bài toán useful work cố định.

## 5. Thread sweep và các tầng thí nghiệm

Thu `physical_cores` và `logical_cpus` thật trước. Tập ban đầu là unique/sorted của `{1,2,3,4,8,physical_cores,logical_cpus,2*logical_cpus}`, loại số không hợp lệ. Các giá trị vượt logical CPUs là oversubscription, gắn nhãn riêng; chỉ chạy khi thời gian và khả năng đáp ứng của máy cho phép. Khóa danh sách cụ thể vào manifest trước chạy chính.

| Tầng | Cấu hình | Mục đích |
| --- | --- | --- |
| Smoke | Threads 1,2,3; N=97; W=0,1; workload rất nhỏ; 1 repetition | Kiểm wiring/output; không dùng làm kết luận performance |
| Pilot | Các baselines và bản custom tại ít thread + mức contention cao; 2 warmup + 3 rep | Chọn I/K/E để mỗi run khoảng 0,5-2 giây tại cấu hình tham chiếu; kiểm compiler và timer |
| Core - locks | TAS,TTAS,MCS,std mutex; N=997; W=0,1,2,4,8; thread sweep; cả hai modes | Trả lời yêu cầu chính |
| Sensitivity - locks | N=97 và 10007; W=0,4; cùng thread sweep | Phân tích critical-section cost, tránh Cartesian product quá lớn |
| Core - barrier | Sense-Reversing,std barrier; E fixed; thread sweep | Episode/s không useful work |
| Core - counters | 4 mutex counters,CAS,FAA; K fixed; thread sweep | Time/throughput cùng workload |
| Extensions | TTAS-backoff, CAS-backoff; high contention trước; mở rộng nếu hữu ích | Giải thích backoff, không trì hoãn bản bắt buộc |

Core/sensitivity bắt đầu với **2 warmup + 7 measured repetitions** mỗi cấu hình. Nếu nhiễu lớn, ghi nguyên nhân, làm lại hoặc tăng rep có lý do. Pilot calibration chỉ chọn khối lượng trước; không đổi K/I/E riêng cho từng implementation để làm đẹp thời gian. Một số N/W có thể cần bộ tham số riêng để phép đo đủ dài; giữa các algorithms và P trong cùng scaling series giữ workload cố định.

Với 8 giá trị threads, số lần chạy measured ở kế hoạch core là: locks `4×8×5×2×7 = 2.240`; barrier `2×8×7 = 112`; counters `6×8×7 = 336`. Tổng **2.688 measured runs/máy**, chưa tính warmup, sensitivity hay extensions. Ước lượng lại tổng runtime từ pilot trước khi bắt đầu; có thể giảm bớt thread points trùng/ít ý nghĩa hoặc phép đo phụ và ghi quyết định. Không lặng lẽ bỏ required variants.

## 6. Protocol trên mỗi máy

1. Qua correctness gate, chốt commit và compiler flags. Có thay code thì tạo run set mới.
2. Thu CPU/cores/SMT, RAM, OS/kernel, compiler/version, standard library, CMake, atomic lock-free, alignment, affinity, nguồn điện và power mode.
3. Đóng tác vụ nặng, giữ nguồn điện/power setting ổn định, ghi virtualization/WSL/VM. Không tự ý thay cấu hình hệ thống làm điều kiện benchmark khác thường mà không ghi lại.
4. Build Release cùng optimization. Tắt sanitizer và test hooks; không áp `-march=native` cho riêng một implementation. Nếu dùng thì log và chỉ so trong cấu hình tương ứng.
5. Warmup không đưa vào summary. Randomize thứ tự algorithms/config theo seed cố định để giảm drift; không chạy các benchmarks đồng thời.
6. Thu từng repetition vào raw CSV; log lỗi/timeouts và checksum/count. Không loại outlier chỉ vì làm algorithm thua.
7. Sau run kiểm consistency/schema/counts; tạo summary/hình bằng script từ raw CSV. Không sửa raw bằng tay.
8. Lặp cùng protocol cho từng máy đang sở hữu. WSL và native trên cùng máy là hai môi trường, không giả là hai CPU vật lý khác nhau.

Affinity mặc định `none` cho bản portable; experiment pinning chỉ thêm khi có khả năng hỗ trợ và áp giống nhau. Không so một lock pinned với baseline unpinned rồi gộp thành một kết luận.

## 7. Schema đầu ra dự kiến

Mỗi run set có `manifest.json` ghi cấu hình đã resolve, platform ID, commit, flags và seed. Platform JSON mô tả máy; raw CSV lưu một dòng cho mỗi warmup/repetition. Nhóm file theo `results/raw/<platform_id>/<run_id>/`.

| Field | Nội dung |
| --- | --- |
| `run_id`, `platform_id`, `git_commit`, `timestamp_utc` | Truy vết source và máy đo |
| `suite`, `implementation`, `mode`, `timing_scope` | Locks/barriers/counters; biến thể; loại workload/timer |
| `threads`, `iterations_per_thread`, `total_operations`, `episodes` | Dùng số thực tế; trường không áp dụng để trống |
| `prime_n`, `outside_work` | Lock workload; trống cho barriers/counters |
| `repetition`, `is_warmup`, `seed` | Lần đo và randomization |
| `program_elapsed_ns`, `worker_elapsed_ns` | Thời gian nguyên bản, từ đó tính metric |
| `checksum`, `final_value`, `status`, `error` | Correctness/result hoặc failed/timeout lý do |
| `backoff_policy`, `backoff_initial`, `backoff_max`, `affinity` | Điều kiện ảnh hưởng so sánh |

Metrics dẫn xuất tính bằng script tổng hợp. Không cộng CAS retry instrumentation/shared counters vào bản performance mặc định; nếu cần đo retries thì làm diagnostic run riêng và gắn nhãn.

## 8. Tổng hợp và biểu đồ cho báo cáo

- Bảng theo platform/implementation/config: median elapsed, Q1/Q3 hoặc IQR, số repetitions hợp lệ. Không lấy mean của các workload khác nhau.
- Lock time vs threads, facet theo W và N; so custom với standard mutex bằng cùng metric chính.
- Lock fixed-total speedup vs threads; kèm lượng việc, không ghép với per-thread.
- Barrier episodes/s vs threads, thêm latency/episode khi hữu ích.
- Counter time hoặc increments/s vs threads, cùng K; counter mạnh nhất không mặc định là FAA trước khi đo.
- Backoff off/on trên cùng contention/workload; trình bày cả khi backoff gây chậm.
- Đánh dấu physical cores/logical CPUs/oversubscription và đơn vị trục; giữ số hình vừa đủ để đọc, raw/sensitivity ở phụ lục.

Mọi kết luận phải gắn với quan sát: cache-line bouncing là giả thuyết giải thích dựa trên cấu trúc thuật toán nếu chưa đo hardware counters. Không khẳng định đã đo cache misses, NUMA hay công suất chỉ từ elapsed time.
