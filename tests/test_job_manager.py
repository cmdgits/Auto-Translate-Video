from pathlib import Path
import shutil
import uuid

from app.core.jobs import JobManager
from app.models import JobManifest, PipelineRunOptions, sanitize_pipeline_options


def test_job_manager_lists_manifests_newest_first() -> None:
    jobs_root = Path("workspace_data") / "test_runs" / f"job_manager_{uuid.uuid4().hex}"
    try:
        manager = JobManager(jobs_root)
        for job_id in ("demo_20260502_210000", "demo_20260502_220000"):
            context = manager.get_context(job_id, input_video=jobs_root / f"{job_id}.mp4")
            context.root_dir.mkdir(parents=True)
            manager.write_manifest(
                context,
                JobManifest(
                    job_id=job_id,
                    status="queued",
                    stage="queued",
                    input_video=str(context.input_video),
                    output_dir=str(context.root_dir),
                    options={"translator_backend": "echo"},
                ),
            )

        manifests = manager.list_manifests()
        assert [manifest.job_id for manifest in manifests] == ["demo_20260502_220000", "demo_20260502_210000"]
        assert manifests[0].options["translator_backend"] == "echo"
    finally:
        shutil.rmtree(jobs_root, ignore_errors=True)


def test_job_manager_avoids_duplicate_job_ids() -> None:
    jobs_root = Path("workspace_data") / "test_runs" / f"job_manager_{uuid.uuid4().hex}"
    try:
        manager = JobManager(jobs_root)
        first_context = manager.create_context("same.mp4", jobs_root / "same.mp4")
        second_context = manager.create_context("same.mp4", jobs_root / "same.mp4")

        assert first_context.job_id != second_context.job_id
        assert second_context.job_id.startswith(f"{first_context.job_id}_")
    finally:
        shutil.rmtree(jobs_root, ignore_errors=True)


def test_job_manager_deletes_job_directory() -> None:
    jobs_root = Path("workspace_data") / "test_runs" / f"job_manager_{uuid.uuid4().hex}"
    try:
        manager = JobManager(jobs_root)
        context = manager.get_context("delete_me", input_video=jobs_root / "delete_me.mp4")
        context.root_dir.mkdir(parents=True)
        manager.write_manifest(
            context,
            JobManifest(
                job_id=context.job_id,
                status="completed",
                stage="completed",
                input_video=str(context.input_video),
                output_dir=str(context.root_dir),
            ),
        )

        assert manager.delete_job(context.job_id) is True
        assert not context.root_dir.exists()
        assert manager.delete_job(context.job_id) is False
    finally:
        shutil.rmtree(jobs_root, ignore_errors=True)


def test_sanitize_pipeline_options_removes_api_keys() -> None:
    options = sanitize_pipeline_options(
        PipelineRunOptions(
            translator_backend="gpt",
            openai_api_key="sk-secret",
            gemini_api_key="gemini-secret",
            openai_model="gpt-test",
        )
    )

    assert "openai_api_key" not in options
    assert "gemini_api_key" not in options
    assert options["openai_api_key_configured"] is True
    assert options["gemini_api_key_configured"] is True
    assert options["openai_model"] == "gpt-test"
