# Mục lục tài liệu nguồn

Nguồn đọc: archive `Parallel_Computing_Slides_and_Assignments.zip` người dùng cung cấp ngày 15/10/2026. [source-manifest.json](source-manifest.json) ghi SHA-256, kích thước và page count để nhận diện đúng phiên bản.

## Đã đọc để lập kế hoạch hiện tại

| Đường dẫn trong archive | Trang PDF | Vai trò |
| --- | --- | --- |
| `Parallel_Computing/Slides/Ch00_Motivation.pdf` | 4 | Amdahl, chi phí phối hợp |
| `Parallel_Computing/Slides/Ch01_Consistency.pdf` | 32 | Memory consistency/coherence |
| `Parallel_Computing/Slides/Ch02a_Atomics.pdf` | 26 | C++ atomic operations |
| `Parallel_Computing/Slides/Ch02b_Atomics.pdf` | 28 | Happens-before, ordering |
| `Parallel_Computing/Slides/Ch03_Spinlocks.pdf` | 30 | TAS/TTAS/MCS |
| `Parallel_Computing/Slides/Ch04_Condition_Synchronization.pdf` | 32 | Sense-Reversing, standard barriers |
| `Parallel_Computing/Slides/Ch05_Concurrent_Objects.pdf` | 22 | Safety, progress, linearizability |
| `Parallel_Computing/Slides/Ch06_Blocking_Concurrency.pdf` | 34 | Lock-based objects, invariant/lifetime |
| `Parallel_Computing/Slides/Ch07_Nonblocking_Objects.pdf` | 26 | CAS, ABA, reclamation |
| `Parallel_Computing/Assignment_1/Assignment1_v1_16092026.pdf` | 4 | Yêu cầu Assignment 1, code ảnh trang 1-2, hạn 29/10/2026 |

Tổng slides: 234 trang; Assignment 1: 4 trang. Các page references trong ghi chú dùng thứ tự trang PDF, không mặc định bằng số in ở footer.

## Có trong archive, ngoài phạm vi đọc chi tiết lần này

- `Parallel_Computing/Outline/DCMH_CO5133_Parallel_Computing.pdf`
- `Parallel_Computing/Assignment_2/Assignment2_v1_30092026.pdf`
- `Parallel_Computing/Assignment_2/osm-astar.ipynb`
- `Parallel_Computing/Assignment_2/pc8_astar-algorithm-pc-discussion.pdf`

## Bố trí bản nguồn khi làm trên máy

Repo lưu ghi chú và manifest nhận diện; các PDF/IPYNB gốc nằm trong archive đã cung cấp. Có thể giải nén archive vào `references/local/` để đọc trên máy; thư mục đó được gitignore. Không cần các PDF gốc để build/run mã C++.

Ngày/giờ hạn nộp và phiên bản đề mới hơn vẫn đối chiếu LMS khi bắt đầu implementation và trước khi nộp.
