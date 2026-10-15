# Dàn ý báo cáo Assignment 1

**Bản khung, chưa có số liệu hay kết luận thực nghiệm.** Chuyển thành bản thảo theo công cụ đã chọn ở M1; xuất `report.pdf` sau khi hoàn tất. Không có giới hạn số trang trong bản đề được cung cấp, nên độ dài là lựa chọn trình bày của người làm.

## Trang đầu

Tên môn/bài, họ tên, MSSV, ngày, repo và commit dùng để đo. Điền thông tin thật trước nộp.

## 1. Phạm vi và phương pháp

Giới thiệu ba yêu cầu locks/barrier/counters; bắt buộc/tùy chọn; các platform thực có; bảng đối chiếu yêu cầu đề. Nêu C++20, standard baselines và cấu trúc source.

## 2. Nền tảng lý thuyết

Mutual exclusion, data race/UB, happens-before, acquire/release, coherence vs consistency; linearizability/progress; Amdahl và giới hạn khi dùng speedup. Chỉ giải thích khái niệm thực sự được dùng.

## 3. Thiết kế và tính đúng

### 3.1 Locks

TAS/TTAS/MCS, state và operation chính. So sánh central RMW với local spinning. Trình bày MCS ba nhánh release, node lifetime, hai đường publish CS và memory orders. Phân biệt FIFO và scheduler progress.

### 3.2 Barrier

Sense reversal, per-instance local sense, reusable phases, last-arriver path. Giải thích vì sao counter reset đơn thuần sai và vì sao acquire/release truyền được writes trước barrier.

### 3.3 Counters

Contract increment trả old value, mutex/CAS/FAA, các linearization points, điều kiện dùng relaxed, overflow và lock-free thực tế.

## 4. Correctness validation

Bảng test ID → mục đích → cấu hình/seed → kết quả thật. Bao gồm MCS enqueue-gap, barrier visibility/reuse/two instances, counter final count/returned-value uniqueness. Ghi môi trường sanitizer, version, thời hạn tests và các hạn chế kiểm thử hữu hạn.

## 5. Experimental setup

Bảng cấu hình từng máy, OS/WSL/VM, compiler/stdlib/flags, commit, atomic lock-free, affinity/power setting. Workload naive prime, chống tối ưu hóa, tham số N/W/I/K/E, thread sweep, startup có/không trong timer, warmup và repetitions, median/IQR.

## 6. Kết quả và thảo luận

### 6.1 Mutex locks

Time toàn chương trình theo threads và contention; N sensitivity; so standard mutex; strong/weak workload tách riêng. Giải thích kết quả dưới/qua physical cores và SMT.

### 6.2 Barrier

Episodes/s và latency; nhấn mạnh episode toàn cục khác arrivals; không useful work giữa barriers. So Sense-Reversing/std barrier.

### 6.3 Counter

Time/throughput với cùng tổng increments. So lock-based/CAS/FAA và backoff nếu đã làm.

### 6.4 Tác động backoff và khác biệt platform

Chỉ viết các thí nghiệm đã thực hiện. Nêu trường hợp thua baseline, biến thiên lớn và nguồn nhiễu; phân biệt quan sát và giả thuyết.

## 7. Giới hạn và kết luận

Những gì dữ liệu thật hỗ trợ, những gì chưa đo. Tóm lại các trade-off theo workload và platform; không tuyên bố một algorithm luôn tốt nhất. MPI ghi rõ không làm nếu chưa triển khai, không mô tả như kết quả có sẵn.

## Nguồn tham khảo và phụ lục

Đề Assignment 1 và các slides đã dùng, primary references đã đối chiếu, tool/docs nếu có. Phụ lục gồm build/test/run commands thật, schema raw data, manifest/run ID, bảng phụ và cách tái tạo figures.

## Checklist PDF/ZIP

- [ ] Không còn TODO, placeholder, dữ liệu minh họa hoặc kết luận chưa đo.
- [ ] Hình/bảng có caption, đơn vị, platform, workload và run ID.
- [ ] Kiểm font tiếng Việt, công thức, số trang, hình không bị cắt.
- [ ] Mọi phần bắt buộc đều có code, correctness, kết quả và thảo luận.
- [ ] ZIP chứa PDF cuối, source/header, CMake/build instructions, tests và các scripts/config cần để chạy.
- [ ] Data/metadata cần cho report được đưa kèm hoặc chỉ rõ chính xác; giữ ZIP tự đủ cho yêu cầu source/PDF.
- [ ] Không chứa build binaries, cache hay tài liệu trung gian không cần thiết.
- [ ] Giải nén ZIP ở thư mục mới, build/test/smoke bằng đúng hướng dẫn, mở PDF kiểm tra lần cuối.
- [ ] Tên file và thông tin cá nhân phù hợp thông báo lớp; kiểm tra giờ LMS trước nộp.
