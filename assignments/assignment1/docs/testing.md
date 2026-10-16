# Kế hoạch kiểm thử correctness

Đã có test executable và CTest registration. Đặc tả dưới đây giải thích oracle; kết quả thực thi ở [verification.md](verification.md), logs/checks.json sinh cục bộ bởi verify.py. Mỗi test phải có oracle độc lập, failure message đủ seed/config và process timeout. Chạy correctness trước performance; instrumentation correctness không nằm trong hot loop của bản Release đo chính.

## 1. Ma trận chung và test harness

| Trục | Giá trị ban đầu đề xuất |
| --- | --- |
| Số threads | 1, 2, 3, 4, 5, 8; thêm `hardware_concurrency + 1` (clamp 2..32) cho một stress case có giới hạn |
| Lần lặp | Ma trận C++: 1000 vòng/case; --stress: 10000 vòng/case; CLI smoke dùng workload nhỏ riêng |
| Lịch gây nhiễu | Không can thiệp; yield có seed; delay một worker; delayed enqueue MCS |
| Build | Debug; Release correctness; TSan khi được hỗ trợ; ASan/UBSan riêng nếu cần kiểm lifetime/UB |
| Seed | Tối thiểu 5 seed cố định cho stress, lưu seed trong log |
| Timeout | Smoke 30 giây, stress 120 giây ban đầu; điều chỉnh theo platform và ghi lý do |

Những con số này là default của kế hoạch, không phải yêu cầu đề. Không đánh fail thuật toán chỉ vì máy sanitizer chậm hơn dự kiến; kiểm tra timeout có phải do deadlock, cấu hình sai hay tải máy.

Start gate dùng primitive tin cậy độc lập với lock/barrier đang test. Khi test thất bại mà một worker mắc kẹt, không join vô hạn: chạy test trong process con/CTest có TIMEOUT để process bị kết thúc và suite tiếp tục. Báo fail/timeout bằng exit code khác 0.

## 2. Locks

| ID | Test | Oracle và lỗi nhắm tới |
| --- | --- | --- |
| L-T1 | Một thread acquire/release nhiều lần | Không tự khóa, state trở lại rảnh |
| L-T2 | Atomic occupancy trong CS: fetch_add trước, fetch_sub sau | Mỗi entry thấy giá trị cũ 0; phát hiện overlap |
| L-T3 | Tăng protected plain counter K lần ở P threads | Final count chính xác P×K; bắt lost update |
| L-T4 | Protected payload có nhiều field liên hệ, đọc/sửa dưới tested lock | Invariant luôn đúng; test publication giữa owners |
| L-T5 | Stress: CS ngắn/dài, ngoài CS thay đổi, yield/delay | Không lỗi oracle, không timeout; chưa instrument per-acquisition wait-time/fairness diagnostic |
| L-T6 | Hai locks, hai bộ context độc lập; acquire/release xen kẽ theo thứ tự nhất quán | Phát hiện state/context static dùng nhầm giữa instances |

L-T2 và L-T4 phải tách: atomic occupancy/telemetry có thể vô tình tạo synchronization che lỗi visibility. Không thêm cờ release/acquire phụ giữa publication payload và đọc payload nếu mục tiêu là kiểm tested lock. Khi tested lock sai, payload test có thể xuất hiện race; TSan là một tín hiệu kiểm tra cần dùng cùng oracle và lập luận.

Test-specific scheduling hooks chỉ biên dịch vào bản test. Logging từ nhiều thread có thể tạo lock ngoài ý muốn; thu vào buffer riêng rồi in sau join.

### MCS bổ sung

| ID | Tình huống | Điều cần xác minh |
| --- | --- | --- |
| M-T1 | Queue rỗng | Acquire nhanh; release CAS tail về null; reacquire lặp lại |
| M-T2 | Successor đã nối `next` | Chỉ successor nhận quyền; payload truyền đúng |
| M-T3 | Successor dừng sau tail exchange, trước nối predecessor.next | Owner release CAS thất bại, chưa return sai; sau mở gate, handoff hoàn tất |
| M-T4 | Nhiều lượt tái sử dụng cùng context sau release | Không stale next/waiting; node còn sống đủ lâu |
| M-T5 | Enqueue có điều khiển A rồi B rồi C | Thứ tự nhận lock theo thứ tự enqueue đã xác nhận |

M-T3 dùng scheduling hook đặt chính xác ở gap, không trông chờ random stress tự gặp. M-T5 không lấy timestamp trước lời gọi acquire để định nghĩa FIFO. Thread có thể bị preempt trước tail exchange.

Safety test không chứng minh starvation freedom. Phần report nêu đặc tính lý thuyết và giả định scheduler; số wait-time/fairness đo được chỉ mô tả mẫu thí nghiệm hữu hạn.

## 3. Sense-Reversing Barrier

| ID | Test | Oracle và lưu ý |
| --- | --- | --- |
| B-T1 | 1 participant, nhiều episode | Mỗi lần trả về; sense và count tái sử dụng đúng |
| B-T2 | 2,3,5,8 participants | Đúng cả số lẻ, không chỉ power-of-two |
| B-T3 | Nhiều episode liên tục, worker nhanh/chậm | Không lẫn phase, không mất notification |
| B-T4 | Một participant bị giữ trước arrival | Các thread đã tới không được qua barrier; mở gate thì tất cả qua |
| B-T5 | Payload visibility | Mỗi worker ghi slot riêng, barrier, đọc toàn bộ slots, barrier lần hai rồi mới sửa slots cho vòng sau |
| B-T6 | Hai barrier instances, context riêng | Xen kẽ lịch A-A-B và nhiều vòng để tách phase counts của A/B; không dùng chung local sense |
| B-T7 | Constructor/CLI nhận 0 participants hoặc giá trị không hợp lệ | Validation từ chối rõ ràng trước spawn; không chạy case treo cố ý |

Trong B-T5, expected slot là dữ liệu của cùng generation hiện tại. **Barrier thứ hai rất cần thiết** để thread nhanh không ghi vòng mới trong lúc thread chậm còn đọc vòng cũ; nếu thiếu, bản test có thể tự gây data race ngay cả khi barrier đúng.

B-T4 dùng gate độc lập để giữ participant cuối; quan sát early-exit bằng atomic flag an toàn và thời hạn hữu hạn. Không dùng sleep đơn lẻ làm "chứng minh" rằng một thread chắc chắn đã tới đoạn code.

## 4. Concurrent counters

| ID | Test | Oracle và lỗi nhắm tới |
| --- | --- | --- |
| C-T1 | Increment tuần tự từ 0 | Trả 0,1,2,...; value bằng số operations |
| C-T2 | P workers cùng tăng K lần | Final value P×K chính xác trên mọi biến thể |
| C-T3 | Thu các giá trị trả về vào buffer riêng, sort sau join | Tập bằng đúng [0, P×K); không trùng, không thiếu |
| C-T4 | Lịch nhỏ gồm increment/value có quan hệ không chồng lấp được điều khiển | Kiểm tra own-thread read sau increment và post-join precedence; không có exhaustive history checker; bổ sung lập luận linearization point |
| C-T5 | CAS contention cao, thử nhiều seed/yield trước retry | Desired được tính lại, expected được xử lý đúng |
| C-T6 | Input âm, 0/biên, tổng vượt uint64_t, phép nhân overflow | Từ chối trường hợp invalid trước chạy; zero operations chỉ là correctness case nếu hỗ trợ |
| C-T7 | Nhiều counter instances, contexts riêng | Không chia sẻ nhầm state giữa các counters |

Không cần lưu toàn bộ returned values trong benchmark production. C-T3 là test kích thước vừa phải để giới hạn RAM; performance loop chỉ checksum/thu kết quả cuối theo thiết kế.

## 5. Workload và dữ liệu thí nghiệm

- `is_prime`: thử 0,1,2,3,4,97,997,10007 và các số chẵn/hợp số; so với oracle tuần tự đơn giản độc lập trong test.
- Với input prime và fixed `N`, expected số kết quả prime là tổng số calls. Với composite, tất cả kết quả false. Ghi tách checksum/count cho calls trong/ngoài CS nếu cần chẩn đoán.
- Kiểm tra chia fixed-total workload bằng thương/số dư không bỏ sót operations, kể cả tổng không chia hết cho P.
- CSV: cùng header, run ID duy nhất; runtime > 0; tham số và counts nhất quán; mọi row lỗi/timeout có trạng thái và lý do.
- Plots: một mẫu nhỏ có thể tính tay để xác minh median/IQR và công thức episode/s; không dùng dữ liệu mẫu làm kết quả cuối.

## 6. Correctness gate trước khi benchmark chính

Tất cả mandatory algorithms và baselines qua cùng suite; M-T3/B-T5/C-T3 được thực thi; không có sanitizer finding chưa giải thích; stress không lỗi với seed/config đã ghi; memory ordering review đủ các đường handoff. Sau khi thay memory order hoặc backoff phải chạy lại tests liên quan.

Giới hạn cần nói trong báo cáo: kiểm thử hữu hạn không duyệt mọi interleaving; TSan không chứng minh tính đúng của relaxed ordering/progress; ASan/UBSan và TSan chạy trong các build riêng. Các công cụ này bổ sung, không thay thế lập luận invariant và happens-before.
