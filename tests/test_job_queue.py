from pathlib import Path
import shutil
import uuid

from app.config import AppConfig
from app.core.pipeline import VideoTranslationPipeline
from app.models import JobManifest
from app.web.job_queue import JobQueue


def test_job_queue_marks_stale_running_jobs_failed() -> None:
    jobs_root = Path("workspace_data") / "test_runs" / f"job_queue_{uuid.uuid4().hex}"
    try:
        config = AppConfig.load().model_copy(
            update={"directories": AppConfig.load().directories.model_copy(update={"jobs_dir": jobs_root})}
        )
        pipeline = VideoTranslationPipeline(config)
        context = pipeline.jobs.get_context("stale_job", input_video=jobs_root / "stale.mp4")
        context.root_dir.mkdir(parents=True)
        pipeline.jobs.write_manifest(
            context,
            JobManifest(
                job_id=context.job_id,
                status="running",
                stage="transcribing",
                progress=0.53,
                input_video=str(context.input_video),
                output_dir=str(context.root_dir),
            ),
        )

        queue = JobQueue(lambda: pipeline)

        assert queue.mark_stale_running_jobs_failed() == 1
        manifest = pipeline.jobs.load_manifest(context.job_id)
        assert manifest is not None
        assert manifest.status == "failed"
        assert "dừng giữa chừng" in manifest.errors[0]
    finally:
        shutil.rmtree(jobs_root, ignore_errors=True)
