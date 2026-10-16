# Đối chiếu Assignment 2

Nguồn: Assignment2_v1_30092026.pdf, 2 trang; tài liệu A* 12 trang và notebook được cung cấp. Bản gốc ở ngoài GitHub. Đây là lựa chọn mô hình của implementation, không phải yêu cầu bổ sung của giảng viên.

| ID | Yêu cầu đề | Quyết định triển khai |
| --- | --- | --- |
| S1 | A* tuần tự trên road network thật, hai vị trí tùy ý | Directed OSM network, chọn node hoặc snap GPS; baseline Dijkstra |
| S2 | h động, không chắc chắn; f vector | Static/dynamic/uncertain/zero policies; hai mục tiêu distance/time, Pareto dominance |
| S3 | Test correctness tuần tự | Dijkstra độc lập, exhaustive simple-path oracle cho Pareto trên graph nhỏ, path replay |
| L1 | Hai concurrent sorted-list sets | Coarse-grained mutex và fine-grained hand-over-hand; std::mutex được đề cho phép |
| L2 | Test correctness sets | Sequential specification, bounded exhaustive linearizability histories, mixed stress, pop-min |
| L3 | So sánh performance sets | Fixed total operations, read-heavy/update-heavy, P sweep, cùng key range/seed |
| P1 | Sửa A* và list để kết hợp song song | Priority entry (f,ticket,label), atomic pop-min; immutable labels, node locks, pending-work accounting |
| P2 | Test correctness song song | Toàn bộ policy/objective/queue combinations, Dijkstra/Pareto oracle, in-flight termination test, sanitizer |
| P3 | Quality, execution time và scalability các phiên bản trên mọi máy sở hữu | Real-road query suite, exact scalar cost/Pareto-set equality, repeats/median/IQR, P=1..quota; pipeline rerun máy cá nhân |
| O1 | Optimizations khác tùy chọn | Directed landmark bounds và incumbent dominance pruning; không contraction hierarchies |
| X1 | Cá nhân, PDF report + Python/C++ source ZIP, hạn 26/11/2026 | Script report/package; người nộp đối chiếu giờ LMS/định danh và tự nộp |

## Hợp đồng được chọn cho những trường hợp mở của đề

Graph hữu hạn có directed edges, chi phí nguyên không âm (distance mm, estimated travel time ms) và không thay đổi trong một query. Heuristic có thể thay đổi theo search epoch; đây không phải bài toán edge costs thay đổi hoặc stochastic optimal policy. Heuristic uncertain là một khoảng ước lượng; chỉ lower bound được chứng nhận dùng cho pruning. Không tuyên bố upper estimate là upper bound của đường tối ưu.

f vector dùng componentwise Pareto dominance và trả một đường cho mỗi cost vector không bị trội. Lexicographic order chỉ chọn task tiếp theo; không thay thế Pareto objective bằng một scalar weighted sum. Nghiệm được chứng minh exact trong mô hình đã chọn, dù đề cho phép near-optimal. Ngân sách label là giới hạn tài nguyên; vượt giới hạn báo lỗi, không gọi output chưa đủ là exact.
