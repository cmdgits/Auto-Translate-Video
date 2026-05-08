from __future__ import annotations

import sys
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from app.config import AppConfig
from app.core.exceptions import AppError
from app.core.pipeline import VideoTranslationPipeline
from app.core.worker import JobWorkerService
from app.media.probe import probe_video
from app.models import PipelineRunOptions

app = typer.Typer(help="Auto Translate Video CLI")
console = Console()


def _load_pipeline(config_path: Path | None) -> VideoTranslationPipeline:
    return VideoTranslationPipeline(AppConfig.load(config_path))


@app.command()
def process(
    input: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False, help="Video dau vao."),
    config: Path | None = typer.Option(None, help="Duong dan config YAML."),
    output_root: Path | None = typer.Option(None, help="Thu muc output jobs."),
    asr_model: str | None = typer.Option(None, help="Model faster-whisper, vi du small hoac medium."),
    translator: str | None = typer.Option(None, help="echo, libretranslate, llm-http, gpt, gemini."),
    llm_base_url: str | None = typer.Option(None, help="OpenAI-compatible base URL."),
    llm_api_key: str | None = typer.Option(None, help="API key cho LLM translator."),
    llm_model: str | None = typer.Option(None, help="Ten model translator."),
    openai_api_key: str | None = typer.Option(None, help="OpenAI API key cho GPT translator."),
    openai_model: str | None = typer.Option(None, help="OpenAI model, vi du gpt-4.1-mini."),
    openai_base_url: str | None = typer.Option(None, help="OpenAI base URL, mac dinh https://api.openai.com/v1."),
    gemini_api_key: str | None = typer.Option(None, help="Gemini API key."),
    gemini_model: str | None = typer.Option(None, help="Gemini model, vi du gemini-2.5-flash-lite."),
    gemini_base_url: str | None = typer.Option(None, help="Gemini API base URL."),
    libretranslate_url: str | None = typer.Option(None, help="URL dich LibreTranslate."),
    libretranslate_api_key: str | None = typer.Option(None, help="API key LibreTranslate."),
    glossary: Path | None = typer.Option(None, help="File glossary, moi dong dang source=target hoac source,target."),
    glossary_json: Path | None = typer.Option(None, help="File glossary JSON, vi du glossary.json."),
    hardsub: bool = typer.Option(False, help="Render video burn subtitle ngay sau khi tao SRT."),
    voiceover: bool = typer.Option(False, help="Render voice-over tieng Viet ngay sau khi tao subtitle."),
    voice_name: str | None = typer.Option(None, help="Ten voice edge-tts, vi du vi-VN-HoaiMyNeural."),
    voiceover_gain: float | None = typer.Option(None, help="Muc am luong kenh voice-over."),
    background_audio_gain: float | None = typer.Option(None, help="Muc am luong kenh audio goc khi mix voice-over."),
    subtitle_font_size: float | None = typer.Option(None, help="Co chu phu de khi render hardsub, 8-120."),
    subtitle_font_family: str | None = typer.Option(None, help="Font chu phu de, vi du Arial hoac Tahoma."),
    subtitle_font_weight: str | None = typer.Option(None, help="Kieu chu phu de: 400, 700 hoac 900."),
    subtitle_primary_color: str | None = typer.Option(None, help="Mau chu phu de dang #RRGGBB."),
    subtitle_box_width_ratio: float | None = typer.Option(None, help="Do rong dong phu de, 0.1-1.0."),
    subtitle_position_x: float | None = typer.Option(None, help="Vi tri ngang phu de khi render hardsub, 0-100."),
    subtitle_position_y: float | None = typer.Option(None, help="Vi tri doc phu de tinh tu duoi len, 0-100."),
    subtitle_cover_mode: str | None = typer.Option(None, help="Che chu goc: none hoac box."),
    subtitle_cover_opacity: float | None = typer.Option(None, help="Muc lam mo che chu goc, 0-1."),
    subtitle_cover_height_ratio: float | None = typer.Option(None, help="Chieu cao vung lam mo, 0.01-1.0."),
    subtitle_cover_width_ratio: float | None = typer.Option(None, help="Chieu rong vung lam mo, 0.01-1.0."),
    subtitle_cover_position_x: float | None = typer.Option(None, help="Vi tri ngang vung lam mo, 0-100."),
    subtitle_cover_position_y: float | None = typer.Option(None, help="Vi tri doc vung lam mo tinh tu duoi len, 0-100."),
) -> None:
    """Xu ly mot video: tach audio, ASR, dich, xuat SRT/VTT va tuy chon render."""
    pipeline = _load_pipeline(config)
    options = PipelineRunOptions(
        output_root=str(output_root) if output_root else None,
        asr_model_size=asr_model,
        translator_backend=translator,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        openai_base_url=openai_base_url,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        gemini_base_url=gemini_base_url,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        libretranslate_url=libretranslate_url,
        libretranslate_api_key=libretranslate_api_key,
        glossary_text=glossary.read_text(encoding="utf-8") if glossary else None,
        glossary_json_path=str(glossary_json) if glossary_json else None,
        render_hardsub=hardsub,
        generate_voiceover=voiceover,
        voice_name=voice_name,
        voiceover_gain=voiceover_gain,
        background_audio_gain=background_audio_gain,
        subtitle_font_size=subtitle_font_size,
        subtitle_font_family=subtitle_font_family,
        subtitle_font_weight=subtitle_font_weight,
        subtitle_primary_color=subtitle_primary_color,
        subtitle_box_width_ratio=subtitle_box_width_ratio,
        subtitle_position_x=subtitle_position_x,
        subtitle_position_y=subtitle_position_y,
        subtitle_cover_mode=subtitle_cover_mode,
        subtitle_cover_opacity=subtitle_cover_opacity,
        subtitle_cover_height_ratio=subtitle_cover_height_ratio,
        subtitle_cover_width_ratio=subtitle_cover_width_ratio,
        subtitle_cover_position_x=subtitle_cover_position_x,
        subtitle_cover_position_y=subtitle_cover_position_y,
    )
    try:
        manifest = pipeline.process(input.resolve(), options)
    except AppError as exc:
        console.print(f"[red]Loi:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover - safety net for unexpected runtime errors
        console.print(f"[red]Loi khong mong doi:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Job {manifest.job_id}")
    table.add_column("Artifact")
    table.add_column("Path")
    for key, value in manifest.outputs.items():
        table.add_row(key, value or "-")
    console.print(table)
    if manifest.status == "completed_with_errors":
        console.print(f"[yellow]Canh bao:[/yellow] {' | '.join(manifest.errors)}")


@app.command()
def inspect(
    input: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False, help="Video dau vao."),
    config: Path | None = typer.Option(None, help="Duong dan config YAML."),
) -> None:
    """Doc metadata media bang ffprobe."""
    loaded_config = AppConfig.load(config)
    metadata = probe_video(input.resolve(), loaded_config.ffprobe_bin)
    console.print(metadata.model_dump_json(indent=2))


@app.command("render-hardsub")
def render_hardsub(
    job_id: str = typer.Option(..., help="Job ID da co transcript/subtitle."),
    config: Path | None = typer.Option(None, help="Duong dan config YAML."),
    subtitle_font_size: float | None = typer.Option(None, help="Co chu phu de khi render hardsub, 8-120."),
    subtitle_font_family: str | None = typer.Option(None, help="Font chu phu de, vi du Arial hoac Tahoma."),
    subtitle_font_weight: str | None = typer.Option(None, help="Kieu chu phu de: 400, 700 hoac 900."),
    subtitle_primary_color: str | None = typer.Option(None, help="Mau chu phu de dang #RRGGBB."),
    subtitle_box_width_ratio: float | None = typer.Option(None, help="Do rong dong phu de, 0.1-1.0."),
    subtitle_position_x: float | None = typer.Option(None, help="Vi tri ngang phu de khi render hardsub, 0-100."),
    subtitle_position_y: float | None = typer.Option(None, help="Vi tri doc phu de tinh tu duoi len, 0-100."),
    subtitle_cover_mode: str | None = typer.Option(None, help="Che chu goc: none hoac box."),
    subtitle_cover_opacity: float | None = typer.Option(None, help="Muc lam mo che chu goc, 0-1."),
    subtitle_cover_height_ratio: float | None = typer.Option(None, help="Chieu cao vung lam mo, 0.01-1.0."),
    subtitle_cover_width_ratio: float | None = typer.Option(None, help="Chieu rong vung lam mo, 0.01-1.0."),
    subtitle_cover_position_x: float | None = typer.Option(None, help="Vi tri ngang vung lam mo, 0-100."),
    subtitle_cover_position_y: float | None = typer.Option(None, help="Vi tri doc vung lam mo tinh tu duoi len, 0-100."),
) -> None:
    """Burn subtitle hien tai vao video output."""
    pipeline = _load_pipeline(config)
    options = PipelineRunOptions(
        subtitle_font_size=subtitle_font_size,
        subtitle_font_family=subtitle_font_family,
        subtitle_font_weight=subtitle_font_weight,
        subtitle_primary_color=subtitle_primary_color,
        subtitle_box_width_ratio=subtitle_box_width_ratio,
        subtitle_position_x=subtitle_position_x,
        subtitle_position_y=subtitle_position_y,
        subtitle_cover_mode=subtitle_cover_mode,
        subtitle_cover_opacity=subtitle_cover_opacity,
        subtitle_cover_height_ratio=subtitle_cover_height_ratio,
        subtitle_cover_width_ratio=subtitle_cover_width_ratio,
        subtitle_cover_position_x=subtitle_cover_position_x,
        subtitle_cover_position_y=subtitle_cover_position_y,
    )
    try:
        manifest = pipeline.render_hardsub(job_id, options)
    except AppError as exc:
        console.print(f"[red]Loi:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(manifest.model_dump_json(indent=2))


@app.command("render-voiceover")
def render_voiceover(
    job_id: str = typer.Option(..., help="Job ID da co transcript/subtitle."),
    config: Path | None = typer.Option(None, help="Duong dan config YAML."),
    voice_name: str | None = typer.Option(None, help="Ten voice edge-tts."),
    voiceover_gain: float | None = typer.Option(None, help="Muc am luong voice-over."),
    background_audio_gain: float | None = typer.Option(None, help="Muc am luong audio goc khi mix."),
) -> None:
    """Tao voice-over tieng Viet va render video moi."""
    pipeline = _load_pipeline(config)
    options = PipelineRunOptions(
        generate_voiceover=True,
        voice_name=voice_name,
        voiceover_gain=voiceover_gain,
        background_audio_gain=background_audio_gain,
    )
    try:
        manifest = pipeline.render_voiceover(job_id, options)
    except AppError as exc:
        console.print(f"[red]Loi:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(manifest.model_dump_json(indent=2))


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", help="Host web UI."),
    port: int = typer.Option(8001, help="Port web UI."),
    reload: bool = typer.Option(False, help="Bat auto reload cho dev."),
    open_browser: bool = typer.Option(True, "--open-browser/--no-open-browser", help="Tu dong mo trinh duyet khi server san sang."),
) -> None:
    """Chay giao dien web editor kieu CapCut."""
    if sys.version_info >= (3, 14):
        console.print(
            "[red]Loi:[/red] Dang chay bang Python 3.14 nen faster-whisper/ctranslate2 de loi tren Windows. "
            "Hay dung .\\run_web.bat hoac tools\\Python312\\python.exe -m app.main web --host 127.0.0.1 --port 8001"
        )
        raise typer.Exit(code=1)
    if open_browser:
        import threading
        import webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}/")).start()
    uvicorn.run("app.web.main:app", host=host, port=port, reload=reload, factory=False)


@app.command("worker")
def worker(
    config: Path | None = typer.Option(None, help="Duong dan config YAML."),
    scan_interval: float = typer.Option(5.0, help="So giay giua moi lan quet job queued/running."),
) -> None:
    """Chay queue worker nhu mot service rieng."""
    pipeline = _load_pipeline(config)
    if pipeline.config.worker.backend.lower() == "celery":
        from app.core.celery_app import celery_app

        console.print("[green]Dang chay Celery worker. Hay dam bao Redis dang bat.[/green]")
        celery_app.worker_main(["worker", "--loglevel=INFO", "--pool=solo"])
        return
    service = JobWorkerService(lambda: pipeline)
    service.start_scanner(scan_interval)
    resumed = service.resume_pending()
    console.print(f"[green]Worker dang chay.[/green] Da dua lai {resumed} tac vu vao hang doi.")
    console.print("Nhan Ctrl+C de dung worker.")
    try:
        while True:
            import time

            time.sleep(3600)
    except KeyboardInterrupt:
        console.print("[yellow]Da dung worker.[/yellow]")
