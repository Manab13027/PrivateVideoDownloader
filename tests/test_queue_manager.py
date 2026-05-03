import threading
from core.queue_manager import DownloadJob, FORMAT_STRINGS, QUALITY_FILTERS


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
