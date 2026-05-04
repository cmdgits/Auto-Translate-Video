# Prompt Phát Triển Auto Translate Video

File này dùng làm kim chỉ nam để phát triển dự án theo từng bước. Khi triển khai, ưu tiên làm từng phase nhỏ, kiểm tra xong mới chuyển sang phase tiếp theo. Mục tiêu là giữ hệ thống ổn định, dễ mở rộng và không làm rối giao diện người dùng.

## Nguyên Tắc Chung

- Mỗi thay đổi phải giải quyết đúng một nhóm chức năng rõ ràng.
- Ưu tiên kiến trúc sạch, dễ bảo trì hơn là vá nhanh trên giao diện.
- Không lưu API key hoặc dữ liệu video riêng tư vào Git.
- Tác vụ nặng như dịch, ASR, TTS và render phải có trạng thái tiến trình, có thể dừng và có khả năng chạy lại.
- Giao diện phải phù hợp màn hình nhỏ, không chiếm quá nhiều diện tích vùng video.

## Phase 1: Tách Queue Worker Thành Service Riêng

Prompt triển khai:

```text
Hãy tách queue xử lý video khỏi tầng web thành một service riêng trong app/core. Service này phải xử lý được các tác vụ process, translate, render hardsub và render voiceover. Web UI chỉ tạo job và đưa job vào queue, không tự chạy logic xử lý nặng bằng BackgroundTasks. Thêm cơ chế resume để worker có thể nhặt lại job đang queued/running khi app khởi động lại.
```

Yêu cầu kỹ thuật:

- Tạo service worker dùng được cả trong web process và CLI riêng.
- Lưu loại tác vụ đang chạy vào manifest để worker độc lập biết cần làm gì.
- Giữ API hiện tại của web không bị đổi ở phía frontend.
- Có snapshot queue để UI vẫn xem được số job đang chờ.

## Phase 2: Retry Và Backoff Cho Tác Vụ Lỗi

Prompt triển khai:

```text
Thêm retry/backoff cho worker. Khi tác vụ lỗi do API dịch, TTS hoặc render, worker tự thử lại theo số lần cấu hình. Mỗi lần retry phải ghi rõ attempt, lỗi cuối, thời điểm retry tiếp theo và không retry nếu người dùng đã bấm Dừng tác vụ.
```

Yêu cầu kỹ thuật:

- Cấu hình `worker.max_attempts`, `worker.backoff_initial_sec`, `worker.backoff_factor`, `worker.backoff_max_sec`.
- Manifest hiển thị số lần thử hiện tại và thời điểm thử lại.
- Backoff không được chặn toàn bộ queue nếu có job khác sẵn sàng chạy.

## Phase 3: Render Softsub Và Mux Nhiều Track Phụ Đề

Prompt triển khai:

```text
Thêm chế độ xuất video softsub. Người dùng có thể mux phụ đề vào MP4/MKV dưới dạng track mềm thay vì burn cứng lên video. Hỗ trợ nhiều track phụ đề: phụ đề gốc, phụ đề tiếng Việt và track tùy chọn khác nếu người dùng import thêm.
```

Yêu cầu kỹ thuật:

- Thêm hàm FFmpeg mux subtitle track trong `app/media/render.py`.
- Thêm output mới vào manifest, ví dụ `video_softsub`.
- UI cho phép chọn hard-sub hoặc soft-sub.
- Nếu container MP4 không hỗ trợ định dạng phụ đề đang dùng, chuyển sang định dạng tương thích hoặc gợi ý MKV.

## Phase 4: Glossary Cho Thuật Ngữ Kỹ Thuật

Prompt triển khai:

```text
Thêm glossary để cố định cách dịch thuật ngữ kỹ thuật. Người dùng có thể nhập danh sách term nguồn và bản dịch mong muốn. Khi gọi Gemini/OpenAI/LLM, prompt dịch phải ưu tiên glossary để thuật ngữ được dịch nhất quán.
```

Yêu cầu kỹ thuật:

- Có file glossary dạng JSON/YAML/CSV trong workspace hoặc theo từng job.
- UI có vùng thêm, sửa, xóa term.
- Translator backend nhận glossary và đưa vào prompt.
- Nếu dùng backend đơn giản không hỗ trợ prompt, áp dụng hậu xử lý cẩn thận để không làm hỏng câu.

## Phase 5: Waveform Và Timeline Chỉnh Phụ Đề Nâng Cao

Prompt triển khai:

```text
Thêm waveform âm thanh vào timeline để người dùng nhìn được nhịp lời thoại. Cho phép kéo start/end của subtitle mượt hơn, snap theo playhead, phóng to timeline tốt hơn và chọn nhiều đoạn để chỉnh hàng loạt.
```

Yêu cầu kỹ thuật:

- Tạo dữ liệu waveform nhẹ từ audio đã tách.
- API trả waveform theo job.
- Frontend render waveform trên timeline bằng canvas hoặc SVG.
- Giữ hiệu năng tốt với video dài.

## Phase 6: TTS Chất Lượng Cao Và Speaker Control

Prompt triển khai:

```text
Mở rộng TTS backend để hỗ trợ nhiều nhà cung cấp chất lượng cao hơn ngoài edge-tts. Thêm speaker control để người dùng chọn giọng theo từng đoạn hoặc từng nhóm speaker, phù hợp video nhiều nhân vật.
```

Yêu cầu kỹ thuật:

- Thiết kế interface TTS backend thống nhất.
- Hỗ trợ cấu hình voice mặc định và voice theo speaker.
- Transcript segment có thể lưu `speaker` và `voice_name`.
- UI cho phép chọn speaker/voice mà không làm rối vùng chỉnh subtitle.

## Thứ Tự Ưu Tiên

1. Queue worker service riêng và retry/backoff.
2. Softsub và mux nhiều track phụ đề.
3. Glossary thuật ngữ kỹ thuật.
4. Waveform/timeline nâng cao.
5. TTS chất lượng cao và speaker control.

