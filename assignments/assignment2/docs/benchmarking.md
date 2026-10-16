# Benchmark protocol

Release/no sanitizer, source digest khớp binary; process serial, shuffled seeded order từng repetition; không chạy validation compile/stress cùng reference measurement. Fixed input graph/queries và matrix lưu trước đo. Mỗi process sample giữ query/preprocess/end-to-end, runner còn ghi process elapsed. Include thread startup/join trong parallel query time. Landmark precompute tách riêng, không gọi query-only speedup là application end-to-end speedup.

Reference matrix: threads [1,2,4,8], 4 heuristics × 3 objectives × 3 queries × (1 sequential + 4 coarse + 4 fine) = 324 route configurations; 2 lists × 4 threads × 2 mixes × 2 ranges = 32 set cases. Tổng 356 cases, 1 warmup + 5 measured reps = 2136 samples. Pilot 38 cases ×2 reps không warmup; smoke 68 short cases.

Set K=20000, ranges64/512, read-heavy80/10/10 và update-heavy20/40/40. Start evens; per-worker RNG seeded. Khi P đổi, random-stream partition đổi; so sánh cùng workload distribution chứ không cùng interleaving. Final sorted/unique/key-range/op-count checks không thay bounded-history correctness tests.

Quality scalar phải equal independent Dijkstra cost, Pareto equal toàn bộ FIFO oracle set; path reconstruction replay mọi directed edge ID và hai cost sums. Không chấp nhận frontier bị cắt hoặc chỉ equal cardinality. Label cap/timeout là failed sample; summary/report bị chặn khi có failure/missing rows. Không xóa outlier theo engine rank.

Warmups giữ raw nhưng loại khỏi statistics. Median và inclusive Q1/Q3; route plots dùng IQR error bars. Speedup vs sequential heap và vs own P=1 tách cột; chỉ cùng query/objective/heuristic/graph/source/platform. Row timings ngắn có startup/noise; không bảo đảm parallel speedup. Fine traversal có nhiều node locks, nên không mặc định nhanh hơn coarse. Cache/OS scheduling explanation nếu không có hardware counters chỉ là giả thuyết.

Reference platform là managed Linux, quota tương đương8 CPUs, affinity9 logical CPUs; không gọi là laptop cá nhân. Cần rerun mọi máy shared-memory thực sở hữu để hoàn tất yêu cầu đề. OSM HCM extract là một vùng nhỏ và static road-class time model; không suy rộng thành routing toàn thành phố hay live traffic.
