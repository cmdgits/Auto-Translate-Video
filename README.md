# Auto Translate Video

He thong ban dau de tach audio tu video, chay speech-to-text, dich subtitle sang tieng Viet, xuat `.srt`/`.vtt`, burn subtitle truc tiep vao video, va tao voice-over tieng Viet. Du an co ca `CLI` va `web UI` mot trang theo bo cuc editor toi mau, lay cam hung tu CapCut.

## Tinh nang hien co

- Upload hoac xu ly video local.
- `ffprobe` doc metadata video.
- `ffmpeg` tach audio sang `.wav` 16k mono.
- `faster-whisper` chay speech-to-text va auto detect language.
- Dich subtitle qua backend `echo`, `libretranslate`, `gpt`, `gemini`, hoac `llm-http`.
- Xuat `transcript.vi.json`, `subtitles.vi.srt`, `subtitles.vi.vtt`.
- Burn subtitle truc tiep vao video bang `ffmpeg`.
- Tao voice-over tieng Viet bang `edge-tts`, mix voi audio goc, va render video moi.
- Web UI tieng Viet co timeline subtitle, subtitle overlay, inspector clip, drag/trim timing, preview video va render actions.
- Timeline editor ho tro split clip tai playhead va merge voi clip ke ben.
- Web UI co batch upload, in-process queue worker, danh sach recent jobs va nut resume job dang queued/running.

## Kien truc chinh

- `app/core/pipeline.py`: orchestration pipeline.
- `app/media/*`: `ffprobe` va `ffmpeg`.
- `app/asr/faster_whisper_backend.py`: speech-to-text.
- `app/translate/*`: translator backend.
- `app/subtitles/*`: format segment va writer cho SRT/VTT.
- `app/tts/*`: sinh TTS va mix voice-over.
- `app/web/*`: giao dien editor va API.
- `app/cli.py`: entrypoint CLI.

## Yeu cau he thong

- Python `3.11` hoac `3.12` duoc khuyen nghi cho `faster-whisper`.
- FFmpeg phai duoc cai va dua vao `PATH`.
- Tren GPU NVIDIA, pipeline co the auto chon `cuda` neu `nvidia-smi` ton tai.

Luu y:
- Workspace hien tai dang dung `Python 3.14.3`, nhung `faster-whisper` thuong on dinh hon o `3.11/3.12`.
- Hien tai may nay chua co `ffmpeg` trong `PATH`.

## Cai dat

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

Neu muon chi dinh config rieng:

```powershell
$env:AUTOTRANSLATE_CONFIG="config.yaml"
```

Mac dinh, app se uu tien `config.yaml` neu file nay ton tai trong workspace.

## Cai FFmpeg tren Windows

1. Tai FFmpeg ban static cho Windows.
2. Giai nen, vi du vao `C:\ffmpeg`.
3. Them `C:\ffmpeg\bin` vao `PATH`.
4. Kiem tra lai:

```powershell
ffmpeg -version
ffprobe -version
```

## Cach dung CLI

Xem metadata:

```powershell
python -m app.main inspect --input "C:\videos\sample.mp4"
```

Xu ly video va xuat subtitle:

```powershell
python -m app.main process --input "C:\videos\sample.mp4"
```

Xu ly video va render burn subtitle ngay:

```powershell
python -m app.main process --input "C:\videos\sample.mp4" --hardsub
```

Xu ly video va tao voice-over ngay:

```powershell
python -m app.main process `
  --input "C:\videos\sample.mp4" `
  --voiceover `
  --voice-name "vi-VN-HoaiMyNeural"
```

Dung LibreTranslate:

```powershell
python -m app.main process `
  --input "C:\videos\sample.mp4" `
  --translator libretranslate `
  --libretranslate-url "http://localhost:5000"
```

Dung endpoint OpenAI-compatible:

```powershell
python -m app.main process `
  --input "C:\videos\sample.mp4" `
  --translator llm-http `
  --llm-base-url "https://your-endpoint/v1" `
  --llm-api-key "YOUR_KEY" `
  --llm-model "your-model-name"
```

Dung OpenAI GPT truc tiep:

```powershell
$env:OPENAI_API_KEY="YOUR_OPENAI_KEY"
python -m app.main process `
  --input "C:\videos\sample.mp4" `
  --translator gpt `
  --openai-model "gpt-4.1-mini"
```

Dung Gemini:

```powershell
$env:GEMINI_API_KEY="YOUR_GEMINI_KEY"
python -m app.main process `
  --input "C:\videos\sample.mp4" `
  --translator gemini `
  --gemini-model "gemini-2.5-flash"
```

Render lai hardsub cho job da co subtitle:

```powershell
python -m app.main render-hardsub --job-id "<job_id>"
```

Render lai voice-over cho job da co subtitle:

```powershell
python -m app.main render-voiceover `
  --job-id "<job_id>" `
  --voice-name "vi-VN-HoaiMyNeural"
```

Ket qua moi job se nam trong:

```text
workspace_data/jobs/<job_id>/
```

## Cach dung Web UI

```powershell
tools\Python312\python.exe -m app.main web --host 127.0.0.1 --port 8001
```

Hoac chay nhanh bang script co san:

```powershell
.\run_web.ps1
```

Neu PowerShell chan script, bam dup `run_web.bat` hoac chay:

```powershell
.\run_web.bat
```

Tren Windows nen dung dung Python di kem trong `tools\Python312`. Neu chay bang Python he thong 3.14, buoc nhan dang giong noi co the loi `Could not find module ... ctranslate2.dll`.

Mo `http://127.0.0.1:8001`

Giao dien co:
- toan bo nhan, nut va thong bao chinh bang tieng Viet de de thao tac
- panel trai giong editor
- preview video o giua
- panel setting pipeline ben phai
- batch upload nhieu video va recent jobs queue
- muc `Cai dat API dich` rieng de luu OpenAI/Gemini/LLM/LibreTranslate tren trinh duyet, co thong bao nho khi luu va tu nap lai sau khi reload
- hop thong bao nho hoi `Luu`, `Khong luu` hoac `Huy` khi co phu de chua luu ma ban sap doi tac vu/xuat video/tao tac vu moi
- timeline subtitle co the drag va trim
- split subtitle tai playhead hoac merge voi clip truoc/sau
- inspector clip de sua source, translated, subtitle, start va end
- nut save timeline, render burn subtitle, render voice-over

## Translator backend

### 1. `echo`

Dung de test UI/pipeline. Khong dich that.

### 2. `libretranslate`

Hop voi server tu host. Can dien:
- `libretranslate_url`
- `libretranslate_api_key` neu server yeu cau

### 3. `llm-http`

Backend HTTP cho endpoint tuong thich `chat/completions`. Can:
- `llm_base_url`
- `llm_model`
- `llm_api_key` neu endpoint yeu cau

### 4. `gpt`

Backend OpenAI GPT truc tiep qua Chat Completions-compatible endpoint. Can:
- `OPENAI_API_KEY` hoac `AUTOTRANSLATE_OPENAI_API_KEY`
- `openai_model`, mac dinh goi y `gpt-4.1-mini`
- `openai_base_url`, mac dinh `https://api.openai.com/v1`

### 5. `gemini`

Backend Google Gemini qua `generateContent`. Can:
- `GEMINI_API_KEY` hoac `AUTOTRANSLATE_GEMINI_API_KEY`
- `gemini_model`, mac dinh goi y `gemini-2.5-flash`
- `gemini_base_url`, mac dinh `https://generativelanguage.googleapis.com/v1beta`

Docs chinh thuc:
- OpenAI Chat Completions API: https://platform.openai.com/docs/api-reference/chat/create
- Gemini Generate Content API: https://ai.google.dev/api/generate-content

## Han che cua ban dau

- Queue worker hien la in-process theo web app, chua tach thanh worker service rieng.
- Voice-over hien tai dung `edge-tts`, chua co lip-sync hay speaker cloning.
- Burn subtitle va voice-over phu thuoc `ffmpeg` trong `PATH`.
- Timeline editor hien chua co waveform audio.

## Huong phat trien tiep

1. Tach queue worker thanh service rieng va them retry/backoff.
2. Them render softsub va mux nhieu track subtitle.
3. Them glossary cho term ky thuat.
4. Them waveform/timeline chinh sua subtitle nang cao hon.
5. Them TTS backend chat luong cao hon va speaker control.
"# Auto-Translale-Video" 
