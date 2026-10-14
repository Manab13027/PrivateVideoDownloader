import re
import subprocess
import queue as queue_module
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.queue_manager import DownloadJob, FORMAT_STRINGS, QUALITY_FILTERS

PROGRESS_RE = re.compile(
    r'\[download\]\s+(\d+\.?\d*)%\s+of\s+~?[\d.]+\s*\w+\s+at\s+([\d.]+\s*\w+/s)\s+ETA\s+([\d:]+)'
)
DEST_RE = re.compile(r'\[download\] Destination: (.+)')
ALREADY_RE = re.compile(r'\[download\] (.+) has already been downloaded')


@dataclass
class ProgressUpdate:
    job_id: str
    progress: float
    speed: str
    eta: str
    status: str        # "queued" | "downloading" | "done" | "failed"
    error: str = ""
    output_path: str = ""


def build_yt_dlp_command(job: DownloadJob) -> list[str]:
    fmt_info = FORMAT_STRINGS.get(job.format)
    if fmt_info is None:
        raise ValueError(f"Unknown format: {job.format!r}")
    base_format = fmt_info["format"]
    quality_filter = QUALITY_FILTERS.get(job.quality, "")

    if quality_filter and job.format not in ("mp3",):
        fmt_str = base_format.replace("bestvideo", f"bestvideo{quality_filter}", 1)
    else:
        fmt_str = base_format

    output_template = str(Path(job.output_dir) / "%(title)s.%(ext)s")

    cmd = [
        "yt-dlp",
        "--format", fmt_str,
        "--output", output_template,
        "--newline",
        "--retries", "3",
        "--no-playlist",
    ]

    if job.cookies_path:
        cmd += ["--cookies", job.cookies_path]

    cmd += list(fmt_info["extra_args"])
    cmd.append(job.url)
    return cmd


def parse_progress_line(line: str) -> Optional[ProgressUpdate]:
    m = PROGRESS_RE.search(line)
    if not m:
        return None
    return ProgressUpdate(
        job_id="",
        progress=float(m.group(1)),
        speed=m.group(2),
        eta=m.group(3),
        status="downloading",
    )


def run_download(job: DownloadJob, ui_queue: queue_module.Queue) -> None:
    job.status = "downloading"
    job.progress = 0.0
    ui_queue.put(ProgressUpdate(job_id=job.job_id, progress=0.0, speed="", eta="", status="downloading"))

    try:
        cmd = build_yt_dlp_command(job)
    except ValueError as e:
        _fail(job, ui_queue, str(e))
        return

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"},
        )
    except FileNotFoundError:
        _fail(job, ui_queue, "yt-dlp not found. Run: pip install yt-dlp")
        return

    output_path = ""
    last_error_line = ""

    try:
        for line in process.stdout:
            if job.cancel_event.is_set():
                process.terminate()
                process.wait()
                job.status = "queued"
                job.progress = 0.0
                job.cancel_event.clear()
                ui_queue.put(ProgressUpdate(job_id=job.job_id, progress=0.0, speed="", eta="", status="queued"))
                return

            line = line.rstrip()

            m_dest = DEST_RE.search(line)
            if m_dest:
                output_path = m_dest.group(1)

            m_already = ALREADY_RE.search(line)
            if m_already:
                output_path = m_already.group(1)

            update = parse_progress_line(line)
            if update:
                update.job_id = job.job_id
                ui_queue.put(update)
            elif line and not line.startswith(("[download]", "[info]", "[youtube]", "WARNING")):
                last_error_line = line

        process.wait()
    except Exception as e:
        _fail(job, ui_queue, f"Unexpected error: {e}")
        return

    if process.returncode == 0:
        job.status = "done"
        job.progress = 100.0
        job.output_path = output_path
        ui_queue.put(ProgressUpdate(
            job_id=job.job_id, progress=100.0, speed="", eta="", status="done", output_path=output_path
        ))
    else:
        _fail(job, ui_queue, last_error_line or "Download failed (check URL or cookies)")


def _fail(job: DownloadJob, ui_queue: queue_module.Queue, error: str) -> None:
    job.status = "failed"
    job.error = error
    ui_queue.put(ProgressUpdate(
        job_id=job.job_id, progress=job.progress, speed="", eta="", status="failed", error=error
    ))
