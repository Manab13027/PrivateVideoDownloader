import threading
import queue as queue_module
from core.queue_manager import DownloadJob, FORMAT_STRINGS, QUALITY_FILTERS, QueueManager


def test_download_job_defaults():
    job = DownloadJob(
        url="https://youtube.com/watch?v=abc",
        format="mp4-h264",
        quality="best",
        cookies_path="/tmp/cookies.txt",
        output_dir="/tmp/videos",
    )
    assert job.status == "queued"
    assert job.progress == 0.0
    assert job.error == ""
    assert job.output_path == ""
    assert isinstance(job.job_id, str) and len(job.job_id) == 36  # UUID
    assert isinstance(job.cancel_event, threading.Event)


def test_format_strings_have_required_keys():
    for key, val in FORMAT_STRINGS.items():
        assert "format" in val, f"{key} missing 'format'"
        assert "extra_args" in val, f"{key} missing 'extra_args'"
        assert "needs_ffmpeg" in val, f"{key} missing 'needs_ffmpeg'"


def test_all_expected_formats_present():
    for fmt in ("mp4-h264", "mp4-h265", "webm", "mp3", "mkv"):
        assert fmt in FORMAT_STRINGS


def test_quality_filters_present():
    for q in ("best", "1080p", "720p", "480p", "audio"):
        assert q in QUALITY_FILTERS


def test_add_jobs_creates_correct_count():
    q = queue_module.Queue()
    mgr = QueueManager(ui_queue=q, max_workers=2)
    urls = ["https://youtube.com/1", "https://youtube.com/2", "https://youtube.com/3"]
    jobs = mgr.add_jobs(urls, format="mp4-h264", quality="best",
                         cookies_path="/tmp/c.txt", output_dir="/tmp")
    assert len(jobs) == 3
    assert len(mgr.jobs) == 3

def test_add_jobs_strips_whitespace():
    q = queue_module.Queue()
    mgr = QueueManager(ui_queue=q, max_workers=2)
    jobs = mgr.add_jobs(["  https://youtube.com/1  ", ""], format="mp4-h264",
                         quality="best", cookies_path="", output_dir="/tmp")
    assert len(jobs) == 1
    assert jobs[0].url == "https://youtube.com/1"

def test_clear_done_removes_done_and_failed():
    q = queue_module.Queue()
    mgr = QueueManager(ui_queue=q, max_workers=2)
    jobs = mgr.add_jobs(
        ["https://a.com", "https://b.com", "https://c.com"],
        format="mp4-h264", quality="best", cookies_path="", output_dir="/tmp"
    )
    jobs[0].status = "done"
    jobs[1].status = "failed"
    # jobs[2] stays "queued"
    mgr.clear_done()
    assert len(mgr.jobs) == 1
    assert mgr.jobs[0].url == "https://c.com"

def test_remove_job_by_id():
    q = queue_module.Queue()
    mgr = QueueManager(ui_queue=q, max_workers=2)
    jobs = mgr.add_jobs(["https://a.com", "https://b.com"],
                         format="mp4-h264", quality="best", cookies_path="", output_dir="/tmp")
    mgr.remove_job(jobs[0].job_id)
    assert len(mgr.jobs) == 1
    assert mgr.jobs[0].url == "https://b.com"
