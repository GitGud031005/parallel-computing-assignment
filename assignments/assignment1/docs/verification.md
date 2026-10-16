# Double-check: kiến thức, implementation và phép đo

Đối chiếu theo slides Ch01/Ch02a/Ch02b/Ch03/Ch04/Ch05, code ảnh của đề trang 1-2 và C++20 working draft N4861. Review dưới đây là kiểm tra từng đường trạng thái và bằng chứng thực thi; không phải tuyên bố đã duyệt mọi interleaving bằng model checker.

## Kiểm tra lại ngày 16/10/2026 trước publish code

Đã đọc lại yêu cầu bản đề 16/09/2026 trang 1-4 và ảnh code `is_prime` trang 2; đối chiếu Ch03 trang PDF 17-28 (đặc biệt MCS 25-27), Ch04 trang 8-15 (Sense-Reversing trang 14), Ch02a/Ch02b về atomic/CAS/acquire-release và Ch05 về progress/linearizability. Số trang ở đây là trang PDF từ 1. Không phát hiện sai lệch thuật toán bắt buộc hoặc workload cần sửa sau lần review này.

| Yêu cầu | Code/bằng chứng đối chiếu |
| --- | --- |
| TAS/TTAS/MCS bằng C++, tests, standard baseline | Ba headers trong `include/pc/locks`, `test_locks.cpp`, `StdMutex` |
| Workload trong/ngoài CS và thời gian toàn chương trình | `bench_locks.cpp`, `src/workload.cpp`, timer spawn-to-join trong harness; giữ cùng N/W giữa variants |
| Reusable Sense-Reversing, tests và baseline | `sense_reversing_barrier.hpp`, `test_barriers.cpp`, `StdBarrier` |
| Barrier episodes/s không useful work | Hot loop chỉ gọi barrier; summary dùng E/worker-seconds, không dùng P×E |
| Counters mutex/CAS/FAA và correctness/execution time | Ba counter headers, `test_counters.cpp`, `bench_counters.cpp`; đủ mutex variants |
| Nghiên cứu scalability | Runner có sweep P, fixed-total/per-thread tách riêng, so sánh baseline, median/IQR |
| Tất cả máy shared-memory sở hữu | Pipeline sẵn; chưa thay thế phép đo trên các máy cá nhân của người nộp |
| ZIP PDF + C++ / MPI tùy chọn | Script tạo report/ZIP đã có; chưa làm MPI, chưa nộp LMS |

Lần chạy mới dùng kernel/build source SHA-256 `1695153b0caf2d8bd2a316b757addac3387b618dc3a72fe8cf47a29b1832720c` (không phải Git commit SHA). README và các ghi chú không đổi fingerprint C++/CMake.

| Check chạy lại | Kết quả |
| --- | --- |
| Configure/build/CTest Release | 6/6 groups passed |
| Configure/build/CTest UBSan | 6/6 groups passed, không báo UB |
| Configure/build/CTest TSan | 6/6 groups passed, không báo data race |
| Release stress locks/barriers/counters | 3/3 suites passed, workload 10 lần |
| Bốn lệnh benchmark minh họa trong README | Passed; prime checksums 40000/9000, counter final 1000000 và old-value checksum 499999500000 |
| Smoke runner + summary theo README | 57/57 configurations, 0 failed samples, đủ nhóm |
| Build từ đúng tập 69 file source/docs chuẩn bị publish, không có tài liệu gốc/results | Configure/build Release và 6/6 CTest groups passed; fingerprint khớp |

Đã kiểm toàn bộ relative Markdown links trong tập file publish. Thử gitignore với slide PDF, đề PDF, PPTX, ZIP, build outputs, raw CSV, validation JSON và report sinh ra: đều bị ignore; 69 file code/tài liệu tự viết đều được phép versioning. Không có slide/PDF đề gốc ở main trước cập nhật.

Logs và dữ liệu gốc của lần kiểm tra được giữ cục bộ; bảng này là ghi chú kết quả, không phải raw log được publish. README Ass1 mô tả lệnh tái lập. GitHub chỉ nhận code/tests/scripts/config và tài liệu tự viết; không nhận slide/đề PDF, generated report, dữ liệu hoặc metadata máy.

| Điểm kiểm tra | Kết quả review / bằng chứng |
| --- | --- |
| TAS/TTAS trao quyền đúng | Chỉ successful TAS/exchange acquire cho vào CS; unlock release. Polling relaxed của TTAS không tự trao lock. |
| MCS không mất successor | next/waiting/tail đều atomic. Release xử lý successor sẵn, queue-rỗng CAS thành công và enqueue-gap CAS thất bại. Hook giữ successor đúng tại gap. |
| MCS strong CAS | Nhánh unlock dùng strong CAS một lần; spurious weak failure không được coi là có successor. Expected là pointer riêng, không ghi đè node owner. |
| MCS payload qua queue rỗng | Release-CAS tail→null kết nối với acquire-exchange nhận null ở người lấy lock tiếp. Không chỉ xét waiting flag của queue không rỗng. |
| MCS context lifetime / FIFO | Mỗi worker/lock có node riêng, không move trong lúc hoạt động. FIFO test điều khiển enqueue order, không dùng timestamp trước acquire. |
| Barrier publish và reset | RMW acq_rel tập hợp arrivals; reset remaining trước release sense; acquire-load sense khi chờ. Thread cuối nhận payload từ chuỗi RMW. |
| Barrier nhiều instance / phase | Local sense thuộc context riêng cho mỗi instance. Test A-A-B; test visibility có barrier thứ hai trước khi ghi thế hệ mới, để bản test không tự race. |
| CAS counter | Failure cập nhật expected, desired tính lại trong mỗi lần thử. Relaxed chỉ cho số đếm, không publish dữ liệu phụ. |
| Counter read / overflow | Mutex value(context) cũng giữ lock; không truy cập plain counter ngoài bảo vệ khi workers còn chạy. CLI kiểm multiplication/addition overflow; library contract không wrap. |
| Progress terminology | Spinlock vẫn blocking. Atomic lock-free ghi theo máy thực tế; không suy ra wait-free/starvation-free từ một lần test pass. |
| Workload gốc | Naive divisor 2..N-1, cùng N/OUTSIDE_WORK giữa variants; N<2 trả false đúng toán học. Không thay một variant bằng sqrt optimization. |
| Compiler không bỏ useful work | Workload translation unit riêng, IPO/LTO tắt; đã kiểm optimized call sites còn trong worker loops của các lock variants. Call-site log giữ cục bộ. |
| Checksum không bị dùng quá mức | Prime workload checksum chỉ xác nhận lượng việc/kết quả, không tự chứng minh mutual exclusion vì primality là pure work. Safety/visibility được kiểm bằng suite locks riêng. |
| Barrier metric | E episodes hoàn thành toàn cục, P×E arrivals. Analysis test known-answer xác minh không nhân P sai đơn vị. |
| Scalability metric | Strong scaling chỉ với fixed-total và cùng N/W/K. Per-thread có tổng việc P×I, không gọi ratio thời gian của nó là strong-scaling speedup. |
| Dấu vân tay / build | CMake hash C++/headers/build files; mỗi executable trả hash. Runner đối chiếu source/binary/build-mode, từ chối Debug hoặc sanitizer để làm performance. |
| Statistics | Warmups không vào summary; mọi measured repetition được giữ. Known-answer test kiểm inclusive quartiles, throughput, speedup, checksum hỏng và duplicate row. |

## Bằng chứng thực thi

Đợt kiểm tra đầy đủ trước đó đã qua Debug, Release, ASan+UBSan, UBSan, TSan và ba stress suites; checks/logs giữ cục bộ. Mỗi build có 6 CTest groups. Release stress tăng workload 10 lần; các custom algorithms có SC reference trong cùng test suite. Payload test tách khỏi occupancy RMW để giảm khả năng instrumentation che lỗi ordering. Lần kiểm lại mới chạy Release/UBSan/TSan và stress như bảng trên, không gọi những checks cũ là vừa chạy lại.

ASan ban đầu kết thúc bằng lỗi LeakSanitizer không đọc được `/proc/.../task` của host; log gốc được giữ. Chạy lại với `detect_leaks=0` qua tất cả tests; **không có kết luận leak-free từ LSan**. Address/UB checks vẫn bật. TSan đã chạy thành công trên host này, không phải skip.

Smoke 57 configurations và pilot 28 configurations đều qua checksum/output validation trước reference study. Các warmup là process riêng như measured samples; mục đích ổn định tải/tần số chung, không giả định giữ một lock object/cache state giữa các process. Trong từng sample, hot loop có nhiều operation liên tiếp.

## Giới hạn và phần cần xác nhận ngoài môi trường này

Số liệu là của managed Linux x86_64, có quota/ảo hóa và host power mode không kiểm soát. Không gắn nhãn là laptop cá nhân; chưa có ARM test hay hardware cache-counter measurement. Chưa biết tất cả máy cá nhân người nộp sở hữu nên yêu cầu thí nghiệm trên các máy đó vẫn cần chạy lại bằng pipeline. Các quyết định memory ordering không dựa vào đặc tính x86 để thay thế C++ happens-before.

Họ tên/MSSV, giờ đóng cổng LMS và thay đổi đề mới hơn phải được người nộp đối chiếu trước nộp. MPI-3 RMA là tùy chọn và được ghi rõ không triển khai; không dùng một MPI_Barrier có sẵn để giả là distributed port.
