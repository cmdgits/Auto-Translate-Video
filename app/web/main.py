from __future__ import annotations

import json
import sys
import threading
from functools import lru_cache
from pathlib import Path
from typing import Callable

from fastapi import Body
from fastapi import File, Form, HTTPException, Request, UploadFile
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import AppConfig
from app.core.celery_queue import CeleryJobQueue
from app.core.exceptions import AppError
from app.core.pipeline import VideoTranslationPipeline
from app.core.worker import JobWorkerService
from app.models import JobManifest, PipelineRunOptions, TranscriptUpdateRequest, sanitize_pipeline_options
from app.media.waveform import write_waveform_json
from app.subtitles.srt_writer import write_srt

if sys.version_info >= (3, 14):
    raise RuntimeError(
        "Dang chay web bang Python 3.14 nen faster-whisper/ctranslate2 se loi tren Windows. "
        "Hay dung .\\run_web.bat hoac tools\\Python312\\python.exe -m app.main web --host 127.0.0.1 --port 8001"
    )

WEB_ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_ROOT / "templates"))

app = FastAPI(title="Auto Translate Video")
app.mount("/static", StaticFiles(directory=str(WEB_ROOT / "static")), name="static")

_local_render_lock = threading.Lock()
_local_render_threads: dict[tuple[str, str], threading.Thread] = {}

@lru_cache
def get_config() -> AppConfig:
    return AppConfig.load()


@lru_cache
def get_pipeline() -> VideoTranslationPipeline:
    return VideoTranslationPipeline(get_config())


@lru_cache
def get_job_queue() -> JobWorkerService | CeleryJobQueue:
    if get_config().worker.backend.lower() == "celery":
        return CeleryJobQueue(get_pipeline())
    return JobWorkerService(get_pipeline)


def _load_transcript_payload(manifest: JobManifest) -> dict:
    transcript_path = manifest.outputs.get("transcript_json") if manifest.outputs else None
    if transcript_path and Path(transcript_path).exists():
        return json.loads(Path(transcript_path).read_text(encoding="utf-8"))
    return {"segments": [], "duration_sec": 0}


def _manifest_with_existing_outputs(manifest: JobManifest) -> JobManifest:
    pipeline = get_pipeline()
    context = pipeline.jobs.get_context(manifest.job_id, input_video=Path(manifest.input_video))
    outputs = {**(manifest.outputs or {}), **pipeline._collect_existing_outputs(context)}
    if outputs == (manifest.outputs or {}):
        return manifest
    return manifest.model_copy(update={"outputs": outputs})


def _manifest_payload(manifest: JobManifest) -> dict:
    manifest = _manifest_with_existing_outputs(manifest)
    if _job_has_transcript(manifest):
        source_subtitle_path = _ensure_source_subtitle(manifest)
        if source_subtitle_path:
            manifest = manifest.model_copy(
                update={"outputs": {**(manifest.outputs or {}), "source_subtitle_srt": str(source_subtitle_path)}}
            )
    payload = manifest.model_dump(mode="json")
    payload["options"] = sanitize_pipeline_options(manifest.options or {})
    transcript = _load_transcript_payload(manifest)
    payload["segments"] = transcript.get("segments", [])
    payload["duration_sec"] = transcript.get("duration_sec", 0)
    payload["downloads"] = {
        key: f"/api/download/{manifest.job_id}/{key}"
        for key, value in manifest.outputs.items()
        if value and Path(value).exists()
    }
    payload["preview_urls"] = {"source": f"/api/source/{manifest.job_id}"}
    if manifest.outputs.get("video_hardsub"):
        payload["preview_urls"]["hardsub"] = f"/api/download/{manifest.job_id}/video_hardsub"
    if manifest.outputs.get("video_softsub"):
        payload["preview_urls"]["softsub"] = f"/api/download/{manifest.job_id}/video_softsub"
    if manifest.outputs.get("video_voiceover"):
        payload["preview_urls"]["voiceover"] = f"/api/download/{manifest.job_id}/video_voiceover"
    payload["source_video_url"] = payload["preview_urls"]["source"]
    return payload


def _ensure_source_subtitle(manifest: JobManifest) -> Path | None:
    pipeline = get_pipeline()
    context = pipeline.jobs.get_context(manifest.job_id, input_video=Path(manifest.input_video))
    if context.original_srt_path.exists():
        return context.original_srt_path
    transcript_path = manifest.outputs.get("transcript_json") if manifest.outputs else None
    if not transcript_path or not Path(transcript_path).exists():
        return None
    transcript = pipeline.load_transcript(manifest.job_id)
    write_srt(transcript, context.original_srt_path, text_mode="source")
    outputs = {**(manifest.outputs or {}), **pipeline._collect_existing_outputs(context)}
    pipeline.jobs.update_manifest(manifest.model_copy(update={"outputs": outputs}))
    return context.original_srt_path


def _get_manifest_or_404(job_id: str) -> JobManifest:
    manifest = get_pipeline().jobs.load_manifest(job_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Khong tim thay job.")
    return manifest


def _has_active_local_render(job_id: str, task_type: str) -> bool:
    key = (job_id, task_type)
    with _local_render_lock:
        thread = _local_render_threads.get(key)
        if thread and thread.is_alive():
            return True
        _local_render_threads.pop(key, None)
    return False


def _start_local_render(job_id: str, task_type: str, target) -> bool:
    key = (job_id, task_type)

    def runner() -> None:
        try:
            target()
        except Exception:
            return
        finally:
            with _local_render_lock:
                if _local_render_threads.get(key) is threading.current_thread():
                    _local_render_threads.pop(key, None)

    with _local_render_lock:
        thread = _local_render_threads.get(key)
        if thread and thread.is_alive():
            return False
        thread = threading.Thread(target=runner, name=f"{task_type}-{job_id}", daemon=True)
        _local_render_threads[key] = thread
        thread.start()
    return True


def _queue_local_render(
    job_id: str,
    *,
    task_type: str,
    stage: str,
    options: PipelineRunOptions | None,
    render: Callable[[str, PipelineRunOptions], JobManifest],
    option_updates: dict[str, object] | None = None,
) -> JobManifest:
    manifest = _get_manifest_or_404(job_id)
    if manifest.status in {"queued", "running"} and manifest.stage == stage and _has_active_local_render(job_id, task_type):
        return manifest

    run_options = (options or PipelineRunOptions()).model_copy(update=option_updates or {})
    queued_manifest = manifest.model_copy(
        update={
            "status": "queued",
            "stage": stage,
            "progress": 0.0,
            "task_type": task_type,
            "options": {**(manifest.options or {}), **sanitize_pipeline_options(run_options)},
            "errors": [],
        }
    )
    get_pipeline().jobs.update_manifest(queued_manifest)

    def run_render() -> None:
        try:
            render(job_id, run_options)
        except Exception:
            return

    _start_local_render(job_id, task_type, run_render)
    return queued_manifest


def _mark_job_running(job_id: str, stage: str, progress: float) -> JobManifest:
    pipeline = get_pipeline()
    manifest = pipeline.jobs.load_manifest(job_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Khong tim thay job.")
    running_manifest = manifest.model_copy(
        update={
            "status": "running",
            "stage": stage,
            "progress": progress,
        }
    )
    return pipeline.jobs.update_manifest(running_manifest)


def _job_has_transcript(manifest: JobManifest) -> bool:
    transcript_path = manifest.outputs.get("transcript_json") if manifest.outputs else None
    if transcript_path and Path(transcript_path).exists():
        return True
    context = get_pipeline().jobs.get_context(manifest.job_id, input_video=Path(manifest.input_video))
    return context.transcript_json_path.exists()


def _options_from_form(
    translator_backend: str,
    asr_model: str,
    llm_base_url: str | None,
    llm_api_key: str | None,
    llm_model: str | None,
    openai_base_url: str | None,
    openai_api_key: str | None,
    openai_model: str | None,
    gemini_base_url: str | None,
    gemini_api_key: str | None,
    gemini_model: str | None,
    libretranslate_url: str | None,
    libretranslate_api_key: str | None,
    glossary_text: str | None,
    render_hardsub: bool,
    generate_voiceover: bool,
    voice_name: str | None,
    voiceover_gain: float | None,
    background_audio_gain: float | None,
    render_encoder: str | None = None,
    render_preset: str | None = None,
    subtitle_font_size: float | None = None,
    subtitle_box_width_ratio: float | None = None,
    subtitle_position_x: float | None = None,
    subtitle_position_y: float | None = None,
    subtitle_cover_mode: str | None = None,
    subtitle_cover_opacity: float | None = None,
    subtitle_cover_height_ratio: float | None = None,
    subtitle_cover_width_ratio: float | None = None,
    subtitle_cover_position_x: float | None = None,
    subtitle_cover_position_y: float | None = None,
) -> PipelineRunOptions:
    selected_backend = (translator_backend or "echo").strip().lower()
    if selected_backend == "echo":
        if gemini_api_key:
            selected_backend = "gemini"
        elif openai_api_key:
            selected_backend = "gpt"
        elif llm_api_key and llm_base_url and llm_model:
            selected_backend = "llm-http"
        elif libretranslate_url:
            selected_backend = "libretranslate"

    return PipelineRunOptions(
        asr_model_size=asr_model,
        translator_backend=selected_backend,
        llm_base_url=llm_base_url or None,
        llm_api_key=llm_api_key or None,
        llm_model=llm_model or None,
        openai_base_url=openai_base_url or None,
        openai_api_key=openai_api_key or None,
        openai_model=openai_model or None,
        gemini_base_url=gemini_base_url or None,
        gemini_api_key=gemini_api_key or None,
        gemini_model=gemini_model or None,
        libretranslate_url=libretranslate_url or None,
        libretranslate_api_key=libretranslate_api_key or None,
        glossary_text=glossary_text or None,
        render_hardsub=render_hardsub,
        generate_voiceover=generate_voiceover,
        voice_name=voice_name or None,
        voiceover_gain=voiceover_gain,
        background_audio_gain=background_audio_gain,
        render_encoder=render_encoder if render_encoder in {"cpu", "nvidia", "intel", "amd"} else None,
        render_preset=render_preset if render_preset in {"fast", "balanced", "quality"} else None,
        subtitle_font_size=subtitle_font_size,
        subtitle_box_width_ratio=subtitle_box_width_ratio,
        subtitle_position_x=subtitle_position_x,
        subtitle_position_y=subtitle_position_y,
        subtitle_cover_mode=subtitle_cover_mode if subtitle_cover_mode in {"none", "box"} else None,
        subtitle_cover_opacity=subtitle_cover_opacity,
        subtitle_cover_height_ratio=subtitle_cover_height_ratio,
        subtitle_cover_width_ratio=subtitle_cover_width_ratio,
        subtitle_cover_position_x=subtitle_cover_position_x,
        subtitle_cover_position_y=subtitle_cover_position_y,
    )


async def _create_queued_job(file: UploadFile, options: PipelineRunOptions) -> JobManifest:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Khong co ten file upload.")

    pipeline = get_pipeline()
    context = pipeline.create_job_context(file.filename, Path(file.filename))
    saved_path = context.input_dir / Path(file.filename).name
    context.input_video = saved_path

    saved_path.parent.mkdir(parents=True, exist_ok=True)
    with saved_path.open("wb") as sink:
        while chunk := await file.read(1024 * 1024):
            sink.write(chunk)

    initial_manifest = JobManifest(
        job_id=context.job_id,
        status="queued",
        stage="queued",
        progress=0.0,
        input_video=str(context.input_video),
        output_dir=str(context.root_dir),
        options=sanitize_pipeline_options(options),
        task_type="process",
        retry_max_attempts=max(1, int(get_config().worker.max_attempts)),
    )
    pipeline.jobs.write_manifest(context, initial_manifest)
    try:
        get_job_queue().enqueue(context, options, task_type="process", update_manifest=False)
    except Exception as exc:
        failed_manifest = initial_manifest.model_copy(
            update={
                "status": "failed",
                "stage": "worker_unavailable",
                "progress": 1.0,
                "errors": [
                    "Không đưa được tác vụ vào worker. Nếu đang dùng Celery, hãy bật Redis và chạy run_worker.bat. "
                    f"Chi tiết: {exc}"
                ],
            }
        )
        pipeline.jobs.update_manifest(failed_manifest)
        raise HTTPException(status_code=503, detail=failed_manifest.errors[0]) from exc
    return initial_manifest


@app.get("/", response_class=HTMLResponse)
async def editor(request: Request) -> HTMLResponse:
    config = get_config()
    return templates.TemplateResponse(
        request,
        "editor.html",
        {
            "app_name": config.app_name,
            "default_asr_model": config.asr.model_size,
            "default_translator": config.translation.backend,
            "default_voice": config.tts.voice,
        },
    )


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def start_job_queue() -> None:
    if not get_config().worker.web_enabled:
        return
    queue = get_job_queue()
    queue.start()
    if get_config().worker.backend.lower() != "celery":
        queue.resume_pending()


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    translator_backend: str = Form("gemini"),
    asr_model: str = Form("tiny"),
    llm_base_url: str | None = Form(None),
    llm_api_key: str | None = Form(None),
    llm_model: str | None = Form(None),
    openai_base_url: str | None = Form(None),
    openai_api_key: str | None = Form(None),
    openai_model: str | None = Form(None),
    gemini_base_url: str | None = Form(None),
    gemini_api_key: str | None = Form(None),
    gemini_model: str | None = Form(None),
    libretranslate_url: str | None = Form(None),
    libretranslate_api_key: str | None = Form(None),
    glossary_text: str | None = Form(None),
    render_hardsub: bool = Form(False),
    generate_voiceover: bool = Form(False),
    voice_name: str | None = Form(None),
    voiceover_gain: float | None = Form(None),
    background_audio_gain: float | None = Form(None),
    render_encoder: str | None = Form(None),
    render_preset: str | None = Form(None),
    subtitle_font_size: float | None = Form(None),
    subtitle_box_width_ratio: float | None = Form(None),
    subtitle_position_x: float | None = Form(None),
    subtitle_position_y: float | None = Form(None),
    subtitle_cover_mode: str | None = Form(None),
    subtitle_cover_opacity: float | None = Form(None),
    subtitle_cover_height_ratio: float | None = Form(None),
    subtitle_cover_width_ratio: float | None = Form(None),
    subtitle_cover_position_x: float | None = Form(None),
    subtitle_cover_position_y: float | None = Form(None),
) -> JSONResponse:
    options = _options_from_form(
        translator_backend,
        asr_model,
        llm_base_url,
        llm_api_key,
        llm_model,
        openai_base_url,
        openai_api_key,
        openai_model,
        gemini_base_url,
        gemini_api_key,
        gemini_model,
        libretranslate_url,
        libretranslate_api_key,
        glossary_text,
        render_hardsub,
        generate_voiceover,
        voice_name,
        voiceover_gain,
        background_audio_gain,
        render_encoder,
        render_preset,
        subtitle_font_size,
        subtitle_box_width_ratio,
        subtitle_position_x,
        subtitle_position_y,
        subtitle_cover_mode,
        subtitle_cover_opacity,
        subtitle_cover_height_ratio,
        subtitle_cover_width_ratio,
        subtitle_cover_position_x,
        subtitle_cover_position_y,
    )
    manifest = await _create_queued_job(file, options)
    return JSONResponse(_manifest_payload(manifest))


@app.post("/api/jobs/batch")
async def create_batch_jobs(
    files: list[UploadFile] = File(...),
    translator_backend: str = Form("gemini"),
    asr_model: str = Form("tiny"),
    llm_base_url: str | None = Form(None),
    llm_api_key: str | None = Form(None),
    llm_model: str | None = Form(None),
    openai_base_url: str | None = Form(None),
    openai_api_key: str | None = Form(None),
    openai_model: str | None = Form(None),
    gemini_base_url: str | None = Form(None),
    gemini_api_key: str | None = Form(None),
    gemini_model: str | None = Form(None),
    libretranslate_url: str | None = Form(None),
    libretranslate_api_key: str | None = Form(None),
    glossary_text: str | None = Form(None),
    render_hardsub: bool = Form(False),
    generate_voiceover: bool = Form(False),
    voice_name: str | None = Form(None),
    voiceover_gain: float | None = Form(None),
    background_audio_gain: float | None = Form(None),
    render_encoder: str | None = Form(None),
    render_preset: str | None = Form(None),
    subtitle_font_size: float | None = Form(None),
    subtitle_box_width_ratio: float | None = Form(None),
    subtitle_position_x: float | None = Form(None),
    subtitle_position_y: float | None = Form(None),
    subtitle_cover_mode: str | None = Form(None),
    subtitle_cover_opacity: float | None = Form(None),
    subtitle_cover_height_ratio: float | None = Form(None),
    subtitle_cover_width_ratio: float | None = Form(None),
    subtitle_cover_position_x: float | None = Form(None),
    subtitle_cover_position_y: float | None = Form(None),
) -> JSONResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Chua chon file nao.")
    options = _options_from_form(
        translator_backend,
        asr_model,
        llm_base_url,
        llm_api_key,
        llm_model,
        openai_base_url,
        openai_api_key,
        openai_model,
        gemini_base_url,
        gemini_api_key,
        gemini_model,
        libretranslate_url,
        libretranslate_api_key,
        glossary_text,
        render_hardsub,
        generate_voiceover,
        voice_name,
        voiceover_gain,
        background_audio_gain,
        render_encoder,
        render_preset,
        subtitle_font_size,
        subtitle_box_width_ratio,
        subtitle_position_x,
        subtitle_position_y,
        subtitle_cover_mode,
        subtitle_cover_opacity,
        subtitle_cover_height_ratio,
        subtitle_cover_width_ratio,
        subtitle_cover_position_x,
        subtitle_cover_position_y,
    )
    manifests = [await _create_queued_job(file, options) for file in files]
    return JSONResponse({"jobs": [_manifest_payload(manifest) for manifest in manifests]})


@app.get("/api/jobs")
async def list_jobs() -> JSONResponse:
    return JSONResponse(
        {
            "jobs": [_manifest_payload(manifest) for manifest in get_pipeline().jobs.list_manifests()],
            "queue": get_job_queue().snapshot(),
        }
    )


@app.post("/api/jobs/resume")
async def resume_jobs() -> JSONResponse:
    resumed = get_job_queue().resume_pending()
    return JSONResponse({"resumed": resumed, "queue": get_job_queue().snapshot()})


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
    return JSONResponse(_manifest_payload(_get_manifest_or_404(job_id)))


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str) -> JSONResponse:
    _get_manifest_or_404(job_id)
    active_job_ids = set(get_job_queue().snapshot().get("queued_ids", []))
    if job_id in active_job_ids:
        manifest = _get_manifest_or_404(job_id)
        if manifest.status in {"queued", "running"}:
            raise HTTPException(status_code=409, detail="Không thể xoá tác vụ đang chạy. Hãy bấm Dừng trước rồi xoá lại.")
    deleted = get_pipeline().jobs.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư mục tác vụ.")
    return JSONResponse({"deleted": True, "job_id": job_id})


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> JSONResponse:
    manifest = _get_manifest_or_404(job_id)
    if manifest.status not in {"queued", "running"}:
        return JSONResponse(_manifest_payload(manifest))
    cancelled_manifest = get_job_queue().cancel(job_id)
    return JSONResponse(_manifest_payload(cancelled_manifest))


@app.put("/api/jobs/{job_id}/segments")
async def update_segments(job_id: str, payload: TranscriptUpdateRequest) -> JSONResponse:
    try:
        manifest = get_pipeline().save_transcript(job_id, payload.segments)
    except AppError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(_manifest_payload(manifest))


@app.post("/api/jobs/{job_id}/render/hardsub")
async def render_hardsub(
    job_id: str,
    options: PipelineRunOptions | None = Body(default=None),
) -> JSONResponse:
    queued_manifest = _queue_local_render(
        job_id,
        task_type="render_hardsub",
        stage="rendering_hardsub",
        options=options,
        render=get_pipeline().render_hardsub,
        option_updates={"render_hardsub": True},
    )
    return JSONResponse(_manifest_payload(queued_manifest))


@app.post("/api/jobs/{job_id}/render/softsub")
async def render_softsub(job_id: str, options: PipelineRunOptions | None = Body(default=None)) -> JSONResponse:
    queued_manifest = _queue_local_render(
        job_id,
        task_type="render_softsub",
        stage="rendering_softsub",
        options=options,
        render=get_pipeline().render_softsub,
    )
    return JSONResponse(_manifest_payload(queued_manifest))


@app.post("/api/jobs/{job_id}/translate")
async def translate_job(job_id: str, options: PipelineRunOptions) -> JSONResponse:
    manifest = _get_manifest_or_404(job_id)
    if manifest.status in {"queued", "running"}:
        raise HTTPException(
            status_code=409,
            detail="Video đang được nhận dạng/dịch. Hãy chờ chạy xong rồi mới bấm Dịch lại.",
        )
    if not _job_has_transcript(manifest):
        raise HTTPException(
            status_code=409,
            detail="Chưa có bản nhận dạng giọng nói cho job này. Hãy chạy xử lý video xong trước, rồi mới bấm Dịch lại sang tiếng Việt.",
        )
    queued_manifest = get_job_queue().enqueue_existing(job_id, "translate", options)
    return JSONResponse(_manifest_payload(queued_manifest))


@app.post("/api/jobs/{job_id}/render/voiceover")
async def render_voiceover(
    job_id: str,
    options: PipelineRunOptions | None = Body(default=None),
) -> JSONResponse:
    queued_manifest = _queue_local_render(
        job_id,
        task_type="render_voiceover",
        stage="rendering_voiceover",
        options=options,
        render=get_pipeline().render_voiceover,
        option_updates={"generate_voiceover": True},
    )
    return JSONResponse(_manifest_payload(queued_manifest))


@app.get("/api/source/{job_id}")
async def get_source_video(job_id: str) -> FileResponse:
    manifest = _get_manifest_or_404(job_id)
    source_path = Path(manifest.input_video)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Khong tim thay file video.")
    return FileResponse(source_path)


@app.get("/api/jobs/{job_id}/waveform")
async def get_waveform(job_id: str) -> JSONResponse:
    manifest = _get_manifest_or_404(job_id)
    context = get_pipeline().jobs.get_context(job_id, input_video=Path(manifest.input_video))
    if not context.waveform_json_path.exists():
        if context.extracted_audio_path.exists():
            write_waveform_json(context.extracted_audio_path, context.waveform_json_path)
        else:
            return JSONResponse({"version": 1, "pending": True, "peaks": [], "points": 0})
    return JSONResponse(json.loads(context.waveform_json_path.read_text(encoding="utf-8")))


@app.get("/api/download/{job_id}/{artifact}")
async def download_artifact(job_id: str, artifact: str) -> FileResponse:
    manifest = _manifest_with_existing_outputs(_get_manifest_or_404(job_id))
    if artifact == "source_subtitle_srt":
        source_path = _ensure_source_subtitle(manifest)
        if source_path and source_path.exists():
            return FileResponse(source_path, filename=source_path.name)
    output_path = manifest.outputs.get(artifact)
    if not output_path:
        raise HTTPException(status_code=404, detail="Artifact khong ton tai.")
    path = Path(output_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact da mat hoac chua duoc tao.")
    return FileResponse(path, filename=path.name)
