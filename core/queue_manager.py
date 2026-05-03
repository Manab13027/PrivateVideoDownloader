import uuid
import threading
import queue as queue_module
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

FORMAT_STRINGS: dict = {
    "mp4-h264": {
        "format": "bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]",
        "extra_args": (),
        "needs_ffmpeg": True,
    },
    "mp4-h265": {
        "format": "bestvideo[ext=mp4][vcodec^=hev]+bestaudio[ext=m4a]/best[ext=mp4]",
        "extra_args": (),
        "needs_ffmpeg": True,
    },
    "webm": {
        "format": "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]",
        "extra_args": (),
        "needs_ffmpeg": False,
    },
    "mp3": {
        "format": "bestaudio/best",
        "extra_args": ("--extract-audio", "--audio-format", "mp3"),
        "needs_ffmpeg": True,
    },
    "mkv": {
        "format": "bestvideo+bestaudio/best",
        "extra_args": ("--merge-output-format", "mkv"),
        "needs_ffmpeg": True,
    },
}

QUALITY_FILTERS: dict = {
    "best": "",
    "1080p": "[height<=1080]",
    "720p": "[height<=720]",
    "480p": "[height<=480]",
    "audio": "",
}


@dataclass
class DownloadJob:
    url: str
    format: str
    quality: str
    cookies_path: str
    output_dir: str
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "queued"
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    error: str = ""
    output_path: str = ""
    title: str = ""
    cancel_event: threading.Event = field(
        default_factory=threading.Event, compare=False, repr=False
    )


class QueueManager:
    def __init__(self, ui_queue: queue_module.Queue, max_workers: int = 3):
        self._ui_queue = ui_queue
        self._max_workers = max_workers
        self._jobs: list[DownloadJob] = []
        self._executor: Optional[ThreadPoolExecutor] = None
        self._lock = threading.Lock()

    @property
    def jobs(self) -> list[DownloadJob]:
        with self._lock:
            return list(self._jobs)

    def add_jobs(
        self, urls: list[str], format: str, quality: str,
        cookies_path: str, output_dir: str
    ) -> list[DownloadJob]:
        new_jobs = [
            DownloadJob(url=u.strip(), format=format, quality=quality,
                        cookies_path=cookies_path, output_dir=output_dir)
            for u in urls if u.strip()
        ]
        with self._lock:
            self._jobs.extend(new_jobs)
        return new_jobs

    def start_all(self) -> None:
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        with self._lock:
            queued = [j for j in self._jobs if j.status == "queued"]
        for job in queued:
            self._executor.submit(self._run_job, job)

    def stop_all(self) -> None:
        with self._lock:
            active = [j for j in self._jobs if j.status == "downloading"]
        for job in active:
            job.cancel_event.set()

    def clear_done(self) -> None:
        with self._lock:
            self._jobs = [j for j in self._jobs if j.status not in ("done", "failed")]

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            job = next((j for j in self._jobs if j.job_id == job_id), None)
            if job:
                job.cancel_event.set()
                self._jobs = [j for j in self._jobs if j.job_id != job_id]

    def set_max_workers(self, n: int) -> None:
        self._max_workers = n

    def shutdown(self) -> None:
        self.stop_all()
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)

    def _run_job(self, job: DownloadJob) -> None:
        from core.downloader import run_download
        run_download(job, self._ui_queue)
