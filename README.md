# Auto Translate Video

Auto Translate Video là công cụ dịch video sang tiếng Việt, chỉnh phụ đề và xuất video hoàn chỉnh ngay trên máy tính cá nhân. Dự án hỗ trợ giao diện web kiểu trình dựng video, kèm CLI cho người muốn xử lý bằng dòng lệnh.

Ứng dụng tập trung vào quy trình thực tế: tải video lên, nhận diện giọng nói, dịch phụ đề, chỉnh sửa trực tiếp trên timeline, làm mờ phụ đề gốc nếu cần, xuất video có phụ đề hoặc video thuyết minh tiếng Việt.

## Tính Năng Chính

- Tải lên một hoặc nhiều video và theo dõi tác vụ gần đây.
- Tự động tách âm thanh, nhận diện lời thoại bằng `faster-whisper` và tạo phụ đề theo thời gian.
- Dịch phụ đề sang tiếng Việt bằng nhiều backend như `echo`, `mymemory`, `libretranslate`, `gpt`, `gemini` hoặc `llm-http`.
- Chỉnh sửa phụ đề trực tiếp trên timeline; bấm vào đoạn timeline sẽ chuyển video tới đúng đoạn đó.
- Hiển thị waveform âm thanh trên timeline để canh lời thoại trực quan hơn.
- Phóng to, thu nhỏ video và timeline để canh vị trí, thời gian hiển thị phụ đề dễ hơn.
- Kéo cả đoạn phụ đề hoặc kéo mép trái/phải để chỉnh thời gian, có snap nhẹ theo playhead.
- Tùy chỉnh kích thước, vị trí và vùng hiển thị phụ đề trên video.
- Làm mờ hoặc che vùng chữ gốc bằng hiệu ứng blur/mask trước khi phủ phụ đề mới.
- Tự lưu nháp phụ đề trên trình duyệt để tránh mất nội dung khi đang sửa.
- Có nút dừng tác vụ khi dịch, tạo phụ đề hoặc render quá lâu.
- Queue worker xử lý tác vụ nền, có thể chạy trong web hoặc chạy như service riêng bằng CLI.
- Tự retry/backoff khi tác vụ nền lỗi tạm thời, ví dụ lỗi API dịch, TTS hoặc render.
- Hiển thị thanh tiến trình phần trăm cho các tác vụ dịch, tạo thuyết minh và xuất video.
- Lưu phụ đề gốc, lưu phụ đề đã dịch, xuất video phụ đề `.mp4` và xuất video thuyết minh `.mp4`.
- Gán speaker và chọn giọng đọc riêng cho từng đoạn phụ đề khi xuất thuyết minh.
- Giao diện toolbar tự xuống dòng gọn hơn khi dùng trên màn hình nhỏ.

## Yêu Cầu Hệ Thống

- Windows 10/11 được khuyến nghị.
- Python `3.12` được khuyến nghị. Dự án hỗ trợ Python `>=3.11,<3.15`, nhưng không nên dùng Python `3.14` cho web UI trên Windows vì `faster-whisper`/`ctranslate2` có thể lỗi.
- FFmpeg và FFprobe phải dùng được bằng lệnh `ffmpeg` và `ffprobe`, hoặc được cấu hình trong `config.yaml`.
- Cần Internet nếu dùng dịch qua Gemini, OpenAI, LibreTranslate online hoặc tạo giọng đọc bằng `edge-tts`.
- GPU NVIDIA là tùy chọn; nếu có, hệ thống tự ưu tiên `cuda` cho nhận diện phụ đề ASR và tự fallback CPU nếu CUDA không dùng được.

## Cài Đặt Nhanh Trên Windows

### Cách Dễ Nhất: Cài Portable Bằng File BAT

Nếu muốn dùng nhanh hoặc chuyển cả dự án sang máy khác, hãy chạy file sau ở thư mục gốc dự án:

```text
install_all.bat
```

File này sẽ tự chuẩn bị các phần cần thiết:

- Tải và cài Python portable vào `tools\Python312` nếu máy chưa có.
- Cài toàn bộ thư viện Python của dự án.
- Tải và giải nén FFmpeg portable vào `tools\ffmpeg` nếu chưa có.
- Tạo `config.yaml`, `.env` và các thư mục dữ liệu trong `workspace_data`.
- Cấu hình worker mặc định là `thread` để chạy được bằng `run_web.bat` mà không bắt buộc Redis/Celery.
- Tải model `faster-whisper-tiny` vào `models\faster-whisper-tiny` nếu có Internet, giúp lần tạo tác vụ đầu tiên ít bị chờ tải model.

Sau khi cài xong, chạy ứng dụng bằng:

```text
run_web.bat
```

Khi muốn chuyển sang máy khác, copy cả thư mục `Auto-Translate-Video` sang máy mới rồi chạy lại `install_all.bat` nếu máy đó còn thiếu Python, FFmpeg hoặc thư viện.

Nếu `install_all.bat` đứng ở bước tải Python, thường là do mạng hoặc firewall chặn `python.org`. Script mới sẽ tự thử `curl`, có timeout và fallback sang Python đã cài sẵn trên máy. Nếu vẫn không được, hãy tải tay file Python theo link script hiển thị, đặt vào thư mục `tools`, rồi chạy lại `install_all.bat`.

### 1. Tải mã nguồn

```powershell
git clone https://github.com/cmdgits/Auto-Translate-Video.git
cd Auto-Translate-Video
```

### 2. Tạo môi trường Python

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Nếu máy chưa có Python 3.12, hãy cài Python 3.12 trước rồi chạy lại các lệnh trên.

### 3. Cấu hình ứng dụng

```powershell
Copy-Item config.example.yaml config.yaml
Copy-Item .env.example .env
```

Sau đó mở `config.yaml` hoặc `.env` để điền API key nếu muốn dùng Gemini, OpenAI hoặc backend LLM khác.

### 4. Cài FFmpeg

Tải FFmpeg bản Windows, giải nén và thêm thư mục `bin` vào `PATH`. Kiểm tra bằng lệnh:

```powershell
ffmpeg -version
ffprobe -version
```

Nếu không muốn thêm vào `PATH`, hãy sửa trực tiếp trong `config.yaml`:

```yaml
ffmpeg_bin: C:\ffmpeg\bin\ffmpeg.exe
ffprobe_bin: C:\ffmpeg\bin\ffprobe.exe
```

## Chạy Giao Diện Web

Nếu bạn đang dùng bộ chạy có sẵn trong thư mục `tools\Python312`, có thể mở nhanh bằng cách nhấp đúp:

```text
run_web.bat
```

Hoặc chạy bằng PowerShell:

```powershell
.\run_web.ps1
```

Nếu cài bằng môi trường `.venv`, chạy:

```powershell
.venv\Scripts\Activate.ps1
python -m app.main web --host 127.0.0.1 --port 8001
```

Sau khi chạy, mở trình duyệt tại:

```text
http://127.0.0.1:8001
```

## Quy Trình Sử Dụng Trên Web

### 1. Tải video lên

- Bấm nút nhập video hoặc kéo thả video vào giao diện.
- Có thể chọn nhiều video để tạo hàng đợi xử lý.
- Mỗi video sẽ được lưu thành một tác vụ riêng trong `workspace_data/jobs`.

### 2. Chọn cách dịch

- Mở phần cài đặt API nếu muốn dùng Gemini, OpenAI hoặc LLM riêng.
- Chọn ngôn ngữ đích là tiếng Việt.
- Bấm dịch để hệ thống nhận diện lời thoại và tạo phụ đề tiếng Việt.

### 3. Chỉnh phụ đề

- Bấm vào một đoạn trên timeline để video nhảy tới đúng thời điểm của đoạn đó.
- Sửa trực tiếp nội dung phụ đề trong vùng chỉnh sửa.
- Điều chỉnh thời gian bắt đầu/kết thúc nếu phụ đề lệch so với video.
- Dùng thanh zoom timeline để kéo giãn hoặc thu gọn khoảng thời gian hiển thị.
- Dựa vào waveform để kéo mép đoạn phụ đề khớp với nhịp âm thanh.
- Có thể gán speaker và giọng đọc riêng cho từng đoạn nếu video có nhiều nhân vật.
- Bản nháp phụ đề sẽ được tự lưu trên trình duyệt trong quá trình chỉnh.

### 4. Chỉnh hiển thị trên video

- Chọn chế độ xem phụ đề để kiểm tra chữ hiển thị trên video.
- Tùy chỉnh cỡ chữ, vị trí, vùng đặt phụ đề và độ che phủ chữ gốc.
- Nếu video có chữ gốc, có thể dùng blur/mask để làm mờ vùng chữ cũ thay vì phủ màu cứng.
- Khi phóng to hoặc thu nhỏ video, phụ đề sẽ co giãn theo khung video để dễ canh chỉnh.

### 5. Lưu và xuất kết quả

- Lưu phụ đề gốc ra file `.srt` nếu cần giữ bản nhận diện ban đầu.
- Lưu phụ đề đã dịch ra file `.srt` sau khi chỉnh sửa.
- Xuất video phụ đề để tạo file `.mp4` có phụ đề tiếng Việt được gắn vào video.
- Xuất video softsub để tạo file `.mkv` chứa nhiều track phụ đề mềm, gồm phụ đề gốc và phụ đề tiếng Việt.
- Xuất video thuyết minh để tạo file `.mp4` có giọng đọc tiếng Việt dựa trên phụ đề đã dịch hoặc đã sửa.
- Khi xuất video, hệ thống tự ưu tiên GPU theo thứ tự `NVIDIA`, `Intel`, `AMD`; nếu FFmpeg hoặc máy không hỗ trợ GPU thì tự chuyển về CPU.
- Khi xuất, giao diện hiển thị phần trăm tiến trình để biết tác vụ đang chạy tới đâu.

## Chạy Worker Riêng

Mặc định web UI tự khởi động worker nền để xử lý tác vụ. Nếu muốn tách worker thành một service riêng, có thể chạy thêm lệnh:

```powershell
python -m app.main worker --scan-interval 5
```

Worker riêng sẽ quét các job đang `queued` hoặc `running` trong `workspace_data/jobs`, đưa lại vào hàng đợi và tự retry theo cấu hình `worker` trong `config.yaml`.

Nếu muốn chỉ dùng worker riêng, đặt `worker.web_enabled: false` trong `config.yaml` để web UI không tự chạy worker nền.

Cấu hình retry/backoff mẫu:

```yaml
worker:
  web_enabled: true
  backend: thread
  broker_url: redis://localhost:6379/0
  result_backend: redis://localhost:6379/1
  max_attempts: 3
  backoff_initial_sec: 5
  backoff_factor: 2
  backoff_max_sec: 60
```

Muốn dùng Celery/Redis thay cho worker thread, cài Redis và đặt:

```yaml
worker:
  backend: celery
  web_enabled: true
  broker_url: redis://localhost:6379/0
  result_backend: redis://localhost:6379/1
  max_attempts: 3
```

Trong bản cấu hình local hiện tại, `config.yaml` đã được bật sẵn `worker.backend: celery`. Khi dùng chế độ này, nên mở 3 cửa sổ terminal theo thứ tự:

```powershell
run_redis_docker.bat
run_worker.bat
run_web.bat
```

- `run_redis_docker.bat`: bật Redis bằng Docker tại `localhost:6379` nếu máy có Docker Desktop.
- `run_worker.bat`: bật Celery worker xử lý nhận diện, dịch, render và retry/backoff.
- `run_web.bat`: bật giao diện web.
- `check_celery_redis.bat`: kiểm tra nhanh dependency Celery/Redis và Redis server đã sẵn sàng chưa.

Nếu không dùng Docker, hãy tự bật Redis sao cho truy cập được tại `redis://localhost:6379/0`, rồi chạy `run_worker.bat` và `run_web.bat`.

Sau đó chạy worker:

```powershell
python -m app.main worker
```

## Cấu Hình Dịch Và API

Các cấu hình chính nằm trong `config.yaml`:

```yaml
translation:
  backend: gemini
  target_language: vi
  gemini_api_key: YOUR_GEMINI_API_KEY
  gemini_model: gemini-2.5-flash
```

Các backend dịch thường dùng:

- `echo`: không dịch, dùng để kiểm tra quy trình hoặc giữ nguyên văn bản gốc.
- `mymemory`: dịch online đơn giản, không cần cấu hình phức tạp.
- `libretranslate`: dùng LibreTranslate public hoặc server riêng.
- `gpt`: dùng OpenAI API.
- `gemini`: dùng Google Gemini API.
- `llm-http`: dùng server tương thích OpenAI API, ví dụ một số server LLM nội bộ.

Glossary thuật ngữ:

- Có thể nhập glossary trong phần cài đặt API dịch để cố định cách dịch thuật ngữ kỹ thuật.
- Mỗi dòng dùng một cặp `thuật ngữ gốc = bản dịch`, ví dụ `render = xuất video`.
- Cũng có thể dùng CSV đơn giản dạng `source,target`.
- Có thể dùng file JSON bằng CLI: `--glossary-json "C:\videos\glossary.json"`.
- Glossary được đưa trực tiếp vào prompt của Gemini/OpenAI/LLM; với MyMemory/LibreTranslate hệ thống sẽ hậu xử lý để ưu tiên thuật ngữ đã đặt.

Lưu ý khi dùng Gemini:

- Tên model nên để dạng ngắn như `gemini-2.5-flash`, không nhập kèm tiền tố `models/` nếu giao diện hoặc cấu hình đã tự xử lý.
- Nếu gặp lỗi `unexpected model name format`, hãy kiểm tra lại tên model trong phần cài đặt API.

## Cấu Hình Giọng Đọc

Giọng đọc mặc định nằm trong `config.yaml`:

```yaml
tts:
  backend: edge-tts
  voice: vi-VN-HoaiMyNeural
  background_audio_gain: 0.24
  voiceover_gain: 1.4
  speaker_voice_map:
    SPEAKER_00: vi-VN-NamMinhNeural
    SPEAKER_01: vi-VN-HoaiMyNeural
```

Một số giọng tiếng Việt thường dùng:

- `vi-VN-HoaiMyNeural`
- `vi-VN-NamMinhNeural`

Khi xuất video thuyết minh, hệ thống sẽ dùng nội dung phụ đề tiếng Việt hiện tại. Nếu bạn đã sửa phụ đề trên web, hãy lưu phụ đề trước khi render để video thuyết minh dùng đúng nội dung mới nhất.

Nếu một đoạn phụ đề có chọn `Giọng đoạn này`, hệ thống sẽ ưu tiên giọng đó thay cho giọng mặc định. Trường `Speaker` giúp phân nhóm nhân vật khi chỉnh video nhiều người nói.

## Thư Mục Kết Quả

Mỗi tác vụ được lưu trong thư mục:

```text
workspace_data/jobs/<job_id>/
```

Các file thường gặp:

```text
workspace_data/jobs/<job_id>/data/transcript.vi.json
workspace_data/jobs/<job_id>/subtitles/subtitles.original.srt
workspace_data/jobs/<job_id>/subtitles/subtitles.vi.srt
workspace_data/jobs/<job_id>/subtitles/subtitles.vi.vtt
workspace_data/jobs/<job_id>/subtitles/subtitles.vi.ass
workspace_data/jobs/<job_id>/renders/video.hardsub.mp4
workspace_data/jobs/<job_id>/renders/video.softsub.mkv
workspace_data/jobs/<job_id>/renders/video.softsub.ffmpeg.txt
workspace_data/jobs/<job_id>/renders/video.voiceover.vi.mp4
```

Ý nghĩa file:

- `subtitles.original.srt`: phụ đề gốc nhận diện từ video.
- `subtitles.vi.srt`: phụ đề tiếng Việt sau dịch hoặc sau chỉnh sửa.
- `subtitles.vi.ass`: phụ đề định dạng ASS dùng khi render video.
- `video.hardsub.mp4`: video đã gắn phụ đề tiếng Việt.
- `video.softsub.mkv`: video giữ hình ảnh gốc và mux nhiều track phụ đề mềm SRT.
- `video.softsub.ffmpeg.txt`: câu lệnh FFmpeg dùng để mux softsub, giúp đối chiếu/kỹ thuật.
- `video.voiceover.vi.mp4`: video thuyết minh tiếng Việt.

## Dùng Bằng Dòng Lệnh

Xem thông tin video:

```powershell
python -m app.main inspect --input "C:\videos\sample.mp4"
```

Xử lý video và tạo phụ đề:

```powershell
python -m app.main process --input "C:\videos\sample.mp4"
```

Dịch với glossary thuật ngữ:

```powershell
python -m app.main process --input "C:\videos\sample.mp4" --glossary "C:\videos\glossary.txt"
```

Dịch với glossary JSON:

```powershell
python -m app.main process --input "C:\videos\sample.mp4" --glossary-json "C:\videos\glossary.json"
```

Xử lý video và xuất luôn video phụ đề:

```powershell
python -m app.main process --input "C:\videos\sample.mp4" --hardsub
```

Xử lý video và xuất luôn video thuyết minh:

```powershell
python -m app.main process --input "C:\videos\sample.mp4" --voiceover --voice-name "vi-VN-HoaiMyNeural"
```

Render lại video phụ đề từ một tác vụ đã có:

```powershell
python -m app.main render-hardsub --job-id "<job_id>"
```

Render lại video thuyết minh từ một tác vụ đã có:

```powershell
python -m app.main render-voiceover --job-id "<job_id>" --voice-name "vi-VN-HoaiMyNeural"
```

Chạy web UI:

```powershell
python -m app.main web --host 127.0.0.1 --port 8001
```

## Cấu Trúc Dự Án

```text
app/
  asr/          Nhận diện giọng nói bằng faster-whisper
  core/         Điều phối pipeline, job, trạng thái và hủy tác vụ
  media/        FFmpeg, FFprobe, render video và xử lý âm thanh
  subtitles/    Tạo SRT, VTT, ASS và định dạng đoạn phụ đề
  translate/    Các backend dịch phụ đề
  tts/          Tạo giọng đọc và mix thuyết minh
  web/          FastAPI, giao diện web, CSS và JavaScript
config.example.yaml  File cấu hình mẫu
run_web.bat          File chạy nhanh web UI trên Windows
run_web.ps1          File chạy web UI bằng PowerShell
build_exe.bat        File đóng gói bản chạy AutoTranslateVideo.exe
workspace_data/      Dữ liệu upload, tác vụ và kết quả render
```

## Đóng Gói Thành File EXE

Dự án có sẵn cấu hình PyInstaller để đóng gói web UI thành bản chạy trên Windows.

1. Cài PyInstaller nếu máy chưa có:

```powershell
tools\Python312\python.exe -m pip install pyinstaller
```

2. Chạy file đóng gói:

```powershell
.\build_exe.bat
```

3. Sau khi hoàn tất, mở file:

```text
dist\AutoTranslateVideo\AutoTranslateVideo.exe
```

File EXE sẽ tự mở web UI tại `http://127.0.0.1:8001/`. Nếu có `tools\ffmpeg\bin\ffmpeg.exe` và `ffprobe.exe`, script sẽ đưa FFmpeg vào gói chạy để máy khác dùng thuận tiện hơn.

## Lưu Ý Khi Đưa Lên GitHub

Không nên đưa các file nặng hoặc dữ liệu riêng tư lên GitHub. Dự án đã bỏ qua các mục sau trong `.gitignore`:

- `.env`, `config.yaml`: có thể chứa API key.
- `workspace_data/`: chứa video, phụ đề và kết quả xuất.
- `tools/Python312/`, `tools/ffmpeg/`: bộ chạy và công cụ nặng.
- `*.zip`, `*.exe`: file cài đặt hoặc file nén lớn.

Nếu cần chia sẻ dự án, chỉ nên đẩy mã nguồn, file cấu hình mẫu và hướng dẫn sử dụng.

## Xử Lý Lỗi Thường Gặp

### Không chạy được `run_web.bat`

Nguyên nhân thường là thiếu `tools\Python312\python.exe`. Hãy cài Python 3.12 và chạy bằng môi trường `.venv`, hoặc đặt Python portable đúng vào thư mục `tools\Python312`.

### Báo lỗi không tìm thấy FFmpeg

Kiểm tra:

```powershell
ffmpeg -version
ffprobe -version
```

Nếu hai lệnh trên không chạy, hãy cài FFmpeg hoặc sửa đường dẫn `ffmpeg_bin` và `ffprobe_bin` trong `config.yaml`.

### Dịch Gemini lỗi 400

Kiểm tra API key, base URL và tên model. Tên model nên để dạng `gemini-2.5-flash`. Không nên nhập thừa dạng `models/gemini-2.5-flash` nếu hệ thống đã tự thêm định dạng cần thiết.

### Video xuất ra chưa đúng phụ đề đã sửa

Hãy lưu phụ đề sau khi chỉnh rồi mới render lại video phụ đề hoặc video thuyết minh. Video thuyết minh sẽ dựa trên phụ đề tiếng Việt hiện tại của tác vụ.

### Giao diện web không thấy cập nhật

Thử tải lại trang bằng `Ctrl + F5` để xóa cache trình duyệt.

## Ghi Chú Bảo Mật

- Không chia sẻ `.env` hoặc `config.yaml` nếu trong đó có API key.
- Không upload video riêng tư lên dịch vụ bên ngoài nếu chưa kiểm tra backend dịch đang dùng.
- Nếu cần xử lý nội bộ, hãy dùng backend cục bộ hoặc server LLM riêng thông qua `llm-http`.
