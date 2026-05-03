import pytest
import queue
from core.downloader import build_yt_dlp_command, parse_progress_line, ProgressUpdate
from core.queue_manager import DownloadJob

def _make_job(**kwargs) -> DownloadJob:
    defaults = dict(
        url="https://youtube.com/watch?v=abc",
        format="mp4-h264",
        quality="best",
        cookies_path="/tmp/cookies.txt",
        output_dir="/tmp/videos",
    )
    defaults.update(kwargs)
    return DownloadJob(**defaults)

def test_command_includes_url():
    job = _make_job()
    cmd = build_yt_dlp_command(job)
    assert "https://youtube.com/watch?v=abc" in cmd

def test_command_includes_cookies():
    job = _make_job(cookies_path="/tmp/cookies.txt")
    cmd = build_yt_dlp_command(job)
    assert "--cookies" in cmd
    assert "/tmp/cookies.txt" in cmd

def test_command_omits_cookies_when_empty():
    job = _make_job(cookies_path="")
    cmd = build_yt_dlp_command(job)
    assert "--cookies" not in cmd

def test_command_includes_retries():
    job = _make_job()
    cmd = build_yt_dlp_command(job)
    assert "--retries" in cmd
    assert "3" in cmd

def test_mp3_format_uses_extract_audio():
    job = _make_job(format="mp3")
    cmd = build_yt_dlp_command(job)
    assert "--extract-audio" in cmd
    assert "--audio-format" in cmd
    assert "mp3" in cmd

def test_mkv_format_uses_merge_output():
    job = _make_job(format="mkv")
    cmd = build_yt_dlp_command(job)
    assert "--merge-output-format" in cmd
    assert "mkv" in cmd

def test_quality_filter_applied_for_1080p():
    job = _make_job(format="mp4-h264", quality="1080p")
    cmd = build_yt_dlp_command(job)
    fmt_arg = cmd[cmd.index("--format") + 1]
    assert "height<=1080" in fmt_arg

def test_parse_progress_line_valid():
    line = "[download]  67.3% of  128.54MiB at    2.41MiB/s ETA 00:12"
    update = parse_progress_line(line)
    assert update is not None
    assert update.progress == pytest.approx(67.3)
    assert update.speed == "2.41MiB/s"
    assert update.eta == "00:12"
    assert update.status == "downloading"

def test_parse_progress_line_invalid():
    assert parse_progress_line("[info] Downloading metadata") is None
    assert parse_progress_line("") is None

import queue as queue_module
from unittest.mock import patch, MagicMock

def test_run_download_yt_dlp_not_found():
    q = queue_module.Queue()
    job = _make_job()
    with patch("subprocess.Popen", side_effect=FileNotFoundError):
        from core.downloader import run_download
        run_download(job, q)
    update = q.get_nowait()
    # first update is "downloading"
    update2 = q.get_nowait()
    assert update2.status == "failed"
    assert "yt-dlp" in update2.error.lower()

def test_run_download_success():
    q = queue_module.Queue()
    job = _make_job()
    mock_proc = MagicMock()
    mock_proc.stdout = iter([
        "[download] Destination: /tmp/videos/test.mp4\n",
        "[download] 100% of  10.00MiB at    5.00MiB/s ETA 00:00\n",
    ])
    mock_proc.returncode = 0
    mock_proc.wait.return_value = None
    with patch("subprocess.Popen", return_value=mock_proc):
        from core.downloader import run_download
        run_download(job, q)
    updates = []
    while not q.empty():
        updates.append(q.get_nowait())
    done = [u for u in updates if u.status == "done"]
    assert len(done) == 1
    assert done[0].progress == 100.0
    assert done[0].output_path == "/tmp/videos/test.mp4"

def test_run_download_failure():
    q = queue_module.Queue()
    job = _make_job()
    mock_proc = MagicMock()
    mock_proc.stdout = iter(["ERROR: Video unavailable\n"])
    mock_proc.returncode = 1
    mock_proc.wait.return_value = None
    with patch("subprocess.Popen", return_value=mock_proc):
        from core.downloader import run_download
        run_download(job, q)
    updates = []
    while not q.empty():
        updates.append(q.get_nowait())
    failed = [u for u in updates if u.status == "failed"]
    assert len(failed) == 1
    assert "unavailable" in failed[0].error.lower()

def test_run_download_unknown_format():
    q = queue_module.Queue()
    job = _make_job(format="invalid-format")
    from core.downloader import run_download
    run_download(job, q)
    updates = []
    while not q.empty():
        updates.append(q.get_nowait())
    failed = [u for u in updates if u.status == "failed"]
    assert len(failed) == 1
    assert "invalid-format" in failed[0].error
