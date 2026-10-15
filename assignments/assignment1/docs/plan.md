# Kế hoạch thực hiện Assignment 1

Ngày lập: **15/10/2026**, múi giờ **Asia/Ho_Chi_Minh (UTC+7)**. Phạm vi hiện tại: lập kế hoạch và dựng cấu trúc; implementation chưa bắt đầu. Đề gốc và tiêu chí đối chiếu ở [requirements.md](requirements.md).

## 1. Kết quả cuối cần đạt

Một project C++ có 3 nhóm thuật toán, correctness tests, benchmark tái lập được, kết quả trên các shared-memory machines thực có, báo cáo PDF và ZIP có thể build độc lập. Tách rõ kết luận đo được khỏi kỳ vọng lý thuyết.

Ưu tiên: bắt buộc và correctness → phép đo đáng tin → giải thích kết quả → backoff → MPI tùy quỹ thời gian. Không đặt MPI vào đường găng.

## 2. Các mốc và tiêu chí hoàn thành

| Mốc | Công việc cụ thể | File/đầu ra dự kiến | Hoàn thành khi |
| --- | --- | --- | --- |
| M0 - tài liệu | Đọc 9 bộ slide và Assignment 1; đối chiếu code ảnh, deadline và phạm vi | Tài liệu trong repo hiện tại | Đã làm ở commit khởi tạo kế hoạch |
| M1 - nền tảng | Chốt môi trường; build Debug/Release; workload; parse CLI; start gate; timer; raw CSV; baseline | `common/*`, `src/workload.cpp`, benchmark baseline, collector môi trường | Hai baseline chạy được; checksum/count đúng; raw CSV có metadata; probe C++20 thành công |
| M2 - locks | TAS → TTAS → MCS; explicit context; RAII; bản SC rồi acquire/release; correctness từng lock | `locks/*`, `tests/test_locks.cpp`, `bench_locks.cpp` | 3 locks qua test safety/visibility/stress; nhánh MCS enqueue-gap được thử; có lập luận HB |
| M3 - barrier | Sense-Reversing, state theo worker và instance; đối chiếu `std::barrier` | `barriers/*`, `tests/test_barriers.cpp`, `bench_barriers.cpp` | N=1, số lẻ, nhiều episode, hai instance, visibility và delay injection qua test |
| M4 - counters | Counter dùng TAS/TTAS/MCS/standard mutex; CAS; FAA; test kết quả và giá trị trả về | `counters/*`, `tests/test_counters.cpp`, `bench_counters.cpp` | Đủ mutex/CAS/FAA, không lost update; test boundary; giải thích linearization point |
| M5 - thí nghiệm | Pilot → khóa cấu hình → đo lặp; thêm backoff khi đủ thời gian; tổng hợp/biểu đồ | `config/`, `scripts/`, `results/` | Mỗi máy có raw CSV, metadata, bảng/hình; mọi hình truy được commit và run ID |
| M6 - hoàn thiện | Viết báo cáo; fresh build/run; xuất PDF; giải nén ZIP kiểm tra; chuẩn bị nộp | `report/report.pdf`, ZIP trong `dist/` | Build/test từ bản đóng gói thành công; báo cáo đủ 3 phần; không có kết quả giả/placeholder |

Ước lượng chủ động: M1 3-4 giờ; M2 7-10 giờ; M3 4-6 giờ; M4 3-5 giờ; M5 5-8 giờ thao tác và thời gian máy chạy; M6 5-7 giờ. Tổng khoảng **27-40 giờ**, chưa tính MPI. Đây là dự toán để chia buổi, cần điều chỉnh sau M1; không phải thời lượng bắt buộc của đề.

## 3. Lịch đề xuất đến ngày nộp

| Ngày (2026, giờ Việt Nam) | Nội dung | Mốc chốt |
| --- | --- | --- |
| 15/10 | Đọc tài liệu, plan, cấu trúc | M0 |
| 16/10 | Môi trường, workload và standard baselines | M1 |
| 17/10 | TAS, TTAS và test | M2 một phần |
| 18-19/10 | MCS, enqueue-gap, memory ordering review | M2 |
| 20/10 | Sense-Reversing và barrier tests | M3 |
| 21/10 | Counter mutex/CAS/FAA và tests | M4 |
| 22/10 | Stress, sanitizer, sửa lỗi, pilot benchmark | Correctness gate |
| 23/10 | TTAS/CAS backoff nếu core ổn; khóa ma trận chính | Chuẩn bị M5 |
| 24-25/10 | Đo đủ các máy đang có; tổng hợp; ghi bất thường | M5 |
| 26/10 | Viết giải thích, bảng/hình, giới hạn | Báo cáo nháp đầy đủ |
| 27/10 | Đối chiếu requirements; fresh build/test; xuất thử PDF | M6 một phần |
| 28/10 | Chốt PDF, ZIP, giải nén kiểm tra, dự phòng lỗi | Sẵn sàng nộp |
| 29/10 | Nộp theo giờ LMS, lưu xác nhận | Hoàn tất |

Mỗi buổi triển khai nên kết thúc bằng một phiên bản build được cùng ghi chú quyết định. Nếu trễ: bỏ MPI trước, sau đó giảm các mở rộng backoff/Pthreads/OpenMP và các phép đo phụ; vẫn giữ đủ 3 phần bắt buộc, baseline, correctness và metric chính.

## 4. Thứ tự làm chi tiết

### M1: Nền tảng trước thuật toán

1. Ghi danh sách platform thực có. Chạy compiler/version probe; xác nhận `std::barrier` của standard library, không chỉ cờ `-std=c++20`.
2. Chọn công cụ xuất báo cáo PDF; thử một trang để không vướng toolchain cuối kỳ.
3. Tạo `workload.cpp`: naive `is_prime` theo đề, đầu vào runtime, checksum theo thread; thử số nguyên tố/hợp số.
4. Tạo CLI thống nhất, kiểm tra tham số và integer overflow; ghi mọi tham số ra CSV/metadata.
5. Tạo worker harness, start gate độc lập thuật toán đang đo, thu thời gian toàn chương trình và thời gian worker khi cần.
6. Dựng `std::mutex` baseline cho locks/counters và `std::barrier` cho barrier; thử một cấu hình nhỏ trước.
7. Tạo CTest thật kèm TIMEOUT; Debug/TSan để correctness và Release để benchmark là các build riêng. TSan chỉ dùng khi toolchain hỗ trợ.

### M2: Locks theo mức độ khó

1. TAS: `atomic_flag` với acquire/release; test mutual exclusion, protected counter, payload visibility.
2. TTAS: polling load rồi thử RMW; giữ cùng workload để tách ảnh hưởng cache-coherence traffic.
3. MCS: mỗi worker có node riêng sống đủ lâu, `tail`/`next`/`waiting` atomic; test cả đường rỗng, successor sẵn và enqueue đang dở.
4. Review memory orders theo từng đường trao quyền lock. Test các giá trị thread 1,2,3,4,8 và một số lượng vượt logical CPUs khi phù hợp.
5. Chạy stress qua nhiều seed. Duy trì giải thích correctness và progress; không suy từ test pass thành chứng minh starvation freedom.

### M3: Barrier

1. Thiết kế số participant cố định, local sense thuộc từng worker **và từng barrier instance**.
2. Cài bản dễ kiểm tra trước; sau đó dùng `fetch_sub(acq_rel)`, publish sense release, wait acquire theo [design.md](design.md).
3. Test 1 participant, số lẻ, nhiều vòng, thread bị chậm, hai barrier xen kẽ và memory visibility với hai điểm đồng bộ mỗi vòng test.
4. Dựng hot loop benchmark chỉ chứa các lần `arrive_and_wait()`, không có prime/log/checksum ở giữa.

### M4: Counters

1. Chốt `increment()` trả giá trị cũ; `value()` đọc giá trị hiện tại. `reset()` chỉ dùng khi workers đã dừng.
2. Cài counter theo từng mutex; dùng `uint64_t` thường bên trong lock.
3. CAS loop: cập nhật desired từ expected mới sau thất bại; chọn relaxed khi counter không publish payload.
4. FAA: một `fetch_add(1, relaxed)`; ghi `is_lock_free()` của kiểu atomic trên máy thực.
5. Test final count, tập giá trị trả về và lịch sử nhỏ; không dùng một plain counter không khóa nhiều thread làm baseline vì data race.

### M5-M6: Từ dữ liệu tới báo cáo

1. Pilot để chọn iterations/episodes và lượng công việc; ghi cấu hình đã chốt vào JSON trước phép đo chính.
2. Đo thread sweep trên mọi máy đang có; đánh dấu core vật lý, SMT và oversubscription riêng.
3. Với locks giữ phép đo toàn chương trình theo đề; với barrier dùng episode/s toàn cục. Chỉ tính speedup strong scaling khi tổng công việc cố định.
4. Lưu từng repetition, warmup, lỗi/timeout, seed và commit. Chỉ dùng Release không sanitizer để kết luận performance.
5. Tổng hợp median/IQR, tạo hình có đơn vị và platform, giải thích cả trường hợp custom thua standard baseline.
6. Điền báo cáo theo [outline.md](../report/outline.md), chỉ đưa số thực đo. Hoàn tất checklist bên dưới.

## 5. Checklist theo dõi

- [x] M0: đọc slide và đề; plan/structure.
- [ ] M1: máy đo và compiler được xác nhận; công cụ PDF chọn xong.
- [ ] M1: workload/harness/baseline có thể chạy.
- [ ] M2: TAS và TTAS có tests.
- [ ] M2: MCS đủ nhánh release và node lifetime tests.
- [ ] M2: memory ordering được giải thích theo happens-before.
- [ ] M3: barrier reusable, visibility, hai instance và odd participants.
- [ ] M4: counter mutex/CAS/FAA đủ test.
- [ ] Correctness gate: stress + sanitizer phù hợp + timeout không có lỗi chưa giải thích.
- [ ] M5: pilot chốt, ma trận chính thực thi, metadata đủ các máy.
- [ ] M5 bổ sung: so sánh TTAS/CAS backoff với bản thường.
- [ ] M5: raw CSV, summary và biểu đồ tái lập được.
- [ ] M6: PDF đủ yêu cầu L/B/C/X/S, nguồn trích dẫn đầy đủ.
- [ ] M6: build/test từ fresh checkout và ZIP đã giải nén.
- [ ] M6: kiểm tra PDF không còn TODO, tên/MSSV và ZIP đúng quy định thực tế.
- [ ] Nộp LMS, kiểm tra file đã lên và lưu xác nhận.

## 6. Điều kiện nghiệm thu cuối

Đủ TAS/TTAS/MCS, Sense-Reversing và counters mutex/CAS/FAA; đủ standard baseline cho lock/barrier; test có khả năng bắt lỗi thuật toán và giải thích memory model; performance dùng đúng workload và metric, dữ liệu thật có truy vết; ZIP có PDF + source + build/run hướng dẫn. Không cần làm distributed để đạt phạm vi bắt buộc.
