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
