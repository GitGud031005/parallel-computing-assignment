# Testing

C++ runtime require hoạt động cả Release. Test timeout là process-level qua CTest; directed hooks chỉ được bật trong test, production callback rỗng.

- Lists so std::set theo từng result tuần tự, extreme keys, same-key winner, partition insert, parallel pop no missing/duplicate và mixed reclamation stress. Bounded history checker backtrack mọi thứ tự hợp `response(A)<invocation(B) => A trước B`, với sequential set/pop-min spec; có negative fixture hai insert cùng key đều success để kiểm chính checker.
- Search dùng exhaustive simple paths trên graph nhỏ với zero cycles, disconnected, parallel edges/random seeds; lọc nondominated vectors rồi so toàn bộ frontier. Dijkstra scalar và landmark admissibility được đối chiếu độc lập. Unsupported Pareto point (12,12) giữa (2,18),(18,2) phát hiện cách scalar hóa sai.
- Directed test giữ worker trên đường 0→1→goal giá 2 trong khi worker khác thấy goal giá 20 và queue cạn. Future không được hoàn tất trước khi cho worker rẻ tiếp tục. Test worker exception và label-budget cancellation để kiểm notify/join.
- Python CLI kiểm mọi logical combination, path edge/cost replay và endpoint modes, invalid graph/parameters. Tools test converter và summary known-answer; lỗi duplicate/missing/corrupt raw phải bị reject.
- Real-road scalar reference là Python heap Dijkstra; Pareto reference là FIFO label-correcting không dùng A*, landmarks hoặc C++ list. Mỗi sample so toàn bộ cost set, replay directed edge IDs, không chỉ đếm số nghiệm.

Default search random graphs 15 seeds, stress 60; list histories 20 seeds, stress 100. Không có exhaustive whole-program C++ memory-model checking. Passing TSan/ASan không chứng minh absence of mọi lỗi, nhưng không bỏ qua tool finding. LSan host limitation được ghi riêng. Kết quả và các lần sửa/recheck ở verification.md; raw logs giữ cục bộ.
