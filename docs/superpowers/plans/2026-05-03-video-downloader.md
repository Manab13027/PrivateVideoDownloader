# PrivateVideoDownloader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-platform Python desktop app (CustomTkinter) that downloads videos from YouTube and other platforms using yt-dlp, with cookies.txt support, a multi-URL queue, real-time progress bars, and compressed output format options.

**Architecture:** Modular Python package with `core/` (business logic) and `ui/` (CustomTkinter widgets). Background downloads run on a `ThreadPoolExecutor`; progress updates flow through a thread-safe `queue.Queue` polled by the UI every 100ms via `CTk.after()`.

**Tech Stack:** Python 3.11+, CustomTkinter 5.2+, yt-dlp, tkinterdnd2 (drag-drop), pytest

---

## File Map

| File | Responsibility |
|---|---|
| `main.py` | Entry point — instantiates and launches App |
| `core/__init__.py` | Empty package marker |
| `core/settings.py` | Load/save `~/.pvd_settings.json`; `SettingsManager` class |
| `core/queue_manager.py` | `DownloadJob` dataclass, `FORMAT_STRINGS`, `QUALITY_FILTERS`, `QueueManager` |
| `core/downloader.py` | `build_yt_dlp_command()`, `parse_progress_line()`, `run_download()`, `ProgressUpdate` |
| `ui/__init__.py` | Empty package marker |
| `ui/app.py` | Main `CTk` window, `CTkTabview`, ffmpeg check, `ui_queue` poll loop |
| `ui/settings_panel.py` | Settings tab: cookies path, output dir, format, quality, max workers |
| `ui/queue_panel.py` | Queue tab: URL input left panel + queue right panel; manages `DownloadRow` widgets |
| `ui/progress_panel.py` | `DownloadRow` widget (progress bar, status badge, 🍪 + ✕ buttons) |
| `ui/history_panel.py` | History tab: completed downloads list with "Open Folder" |
| `tests/test_settings.py` | Unit tests for `SettingsManager` |
| `tests/test_downloader.py` | Unit tests for `build_yt_dlp_command`, `parse_progress_line` |
| `tests/test_queue_manager.py` | Unit tests for `QueueManager.add_jobs`, `clear_done` |
| `requirements.txt` | Python dependencies |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `main.py`
- Create: `core/__init__.py`
- Create: `ui/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
customtkinter>=5.2.0
yt-dlp>=2024.1.0
tkinterdnd2>=0.3.0
pytest>=8.0.0
```

- [ ] **Step 2: Create package markers**

```bash
touch core/__init__.py ui/__init__.py tests/__init__.py
```

- [ ] **Step 3: Create main.py stub**

```python
# main.py
import sys

def main():
    from ui.app import App
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 5: Verify Python version**

```bash
python --version
```

Expected: `Python 3.11.x` or higher.

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt main.py core/__init__.py ui/__init__.py tests/__init__.py
git commit -m "chore: scaffold project structure"
```

---

## Task 2: Settings Module

**Files:**
- Create: `core/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_settings.py
import json
import pytest
from pathlib import Path
from core.settings import SettingsManager, DEFAULTS

def test_defaults_loaded_when_no_file(tmp_path):
    mgr = SettingsManager(path=tmp_path / "settings.json")
    assert mgr.get("max_workers") == 3
    assert mgr.get("default_format") == "mp4-h264"
    assert mgr.get("default_quality") == "best"

def test_save_and_reload(tmp_path):
    path = tmp_path / "settings.json"
    mgr = SettingsManager(path=path)
    mgr.set("max_workers", 5)
    mgr2 = SettingsManager(path=path)
    assert mgr2.get("max_workers") == 5

def test_ignores_unknown_keys(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"unknown_key": "value", "max_workers": 2}))
    mgr = SettingsManager(path=path)
    assert mgr.get("max_workers") == 2
    assert mgr.get("unknown_key") is None

def test_corrupted_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not valid json{{{")
    mgr = SettingsManager(path=path)
    assert mgr.get("max_workers") == DEFAULTS["max_workers"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_settings.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `core.settings`.

- [ ] **Step 3: Implement core/settings.py**

```python
# core/settings.py
import json
from pathlib import Path

SETTINGS_PATH = Path.home() / ".pvd_settings.json"

DEFAULTS: dict = {
    "cookies_path": "",
    "output_dir": str(Path.home() / "Downloads" / "Videos"),
    "default_format": "mp4-h264",
    "default_quality": "best",
    "max_workers": 3,
}

class SettingsManager:
    def __init__(self, path: Path = SETTINGS_PATH):
        self._path = path
        self._data: dict = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    saved = json.load(f)
                self._data.update({k: v for k, v in saved.items() if k in DEFAULTS})
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value) -> None:
        if key in DEFAULTS:
            self._data[key] = value
            self.save()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_settings.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add core/settings.py tests/test_settings.py
git commit -m "feat(core): add SettingsManager with JSON persistence"
```

---

## Task 3: DownloadJob Model + Format/Quality Constants

**Files:**
- Create: `core/queue_manager.py` (partial — dataclass + constants only)
- Create: `tests/test_queue_manager.py` (partial)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_queue_manager.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_queue_manager.py -v
```

Expected: `ImportError` for `core.queue_manager`.

- [ ] **Step 3: Implement the dataclass and constants in core/queue_manager.py**

```python
# core/queue_manager.py
import uuid
import threading
import queue as queue_module
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

FORMAT_STRINGS: dict = {
    "mp4-h264": {
        "format": "bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]",
        "extra_args": [],
        "needs_ffmpeg": True,
    },
    "mp4-h265": {
        "format": "bestvideo[ext=mp4][vcodec^=hev]+bestaudio[ext=m4a]/best[ext=mp4]",
        "extra_args": [],
        "needs_ffmpeg": True,
    },
    "webm": {
        "format": "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]",
        "extra_args": [],
        "needs_ffmpeg": False,
    },
    "mp3": {
        "format": "bestaudio/best",
        "extra_args": ["--extract-audio", "--audio-format", "mp3"],
        "needs_ffmpeg": True,
    },
    "mkv": {
        "format": "bestvideo+bestaudio/best",
        "extra_args": ["--merge-output-format", "mkv"],
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_queue_manager.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add core/queue_manager.py tests/test_queue_manager.py
git commit -m "feat(core): add DownloadJob dataclass and format/quality constants"
```

---

## Task 4: Downloader — Command Builder + Progress Parser

**Files:**
- Create: `core/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_downloader.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_downloader.py -v
```

Expected: `ImportError` for `core.downloader`.

- [ ] **Step 3: Implement core/downloader.py**

```python
# core/downloader.py
import re
import subprocess
import queue as queue_module
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.queue_manager import DownloadJob, FORMAT_STRINGS, QUALITY_FILTERS

PROGRESS_RE = re.compile(
    r'\[download\]\s+(\d+\.?\d*)%\s+of\s+~?[\d.]+\w+\s+at\s+([\d.]+\w+/s)\s+ETA\s+(\d+:\d+)'
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
    fmt_info = FORMAT_STRINGS[job.format]
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

    cmd += fmt_info["extra_args"]
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

    cmd = build_yt_dlp_command(job)

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
    except FileNotFoundError:
        _fail(job, ui_queue, "yt-dlp not found. Run: pip install yt-dlp")
        return

    output_path = ""
    last_error_line = ""

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
        elif line and not line.startswith(("[download]", "[info]", "[youtube]")):
            last_error_line = line

    process.wait()

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add core/downloader.py tests/test_downloader.py
git commit -m "feat(core): add downloader with yt-dlp command builder and progress parser"
```

---

## Task 5: QueueManager Class

**Files:**
- Modify: `core/queue_manager.py` (append QueueManager class)
- Modify: `tests/test_queue_manager.py` (append tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_queue_manager.py`:

```python
import queue as queue_module
from core.queue_manager import QueueManager

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_queue_manager.py::test_add_jobs_creates_correct_count -v
```

Expected: `ImportError` or `AttributeError` — `QueueManager` not defined yet.

- [ ] **Step 3: Append QueueManager to core/queue_manager.py**

```python
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

    def _run_job(self, job: DownloadJob) -> None:
        from core.downloader import run_download
        run_download(job, self._ui_queue)
```

- [ ] **Step 4: Run all core tests**

```bash
pytest tests/ -v
```

Expected: all tests pass (minimum 18).

- [ ] **Step 5: Commit**

```bash
git add core/queue_manager.py tests/test_queue_manager.py
git commit -m "feat(core): add QueueManager with ThreadPoolExecutor and job lifecycle"
```

---

## Task 6: Main App Window

**Files:**
- Create: `ui/app.py`

- [ ] **Step 1: Create ui/app.py**

```python
# ui/app.py
import shutil
import queue as queue_module
import customtkinter as ctk

from core.settings import SettingsManager
from core.queue_manager import QueueManager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PrivateVideoDownloader")
        self.geometry("960x620")
        self.minsize(780, 500)

        self.settings = SettingsManager()
        self.ui_queue: queue_module.Queue = queue_module.Queue()
        self.queue_manager = QueueManager(
            ui_queue=self.ui_queue,
            max_workers=self.settings.get("max_workers"),
        )
        self._ffmpeg_available = shutil.which("ffmpeg") is not None

        self._build_ui()
        self._show_ffmpeg_warning_if_needed()
        self._start_poll()

    def _build_ui(self) -> None:
        from ui.queue_panel import QueuePanel
        from ui.settings_panel import SettingsPanel
        from ui.history_panel import HistoryPanel

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        for tab_name in ("Queue", "History", "Settings"):
            self.tabs.add(tab_name)

        self.queue_panel = QueuePanel(
            self.tabs.tab("Queue"),
            queue_manager=self.queue_manager,
            settings=self.settings,
            ffmpeg_available=self._ffmpeg_available,
        )
        self.queue_panel.pack(fill="both", expand=True)

        self.history_panel = HistoryPanel(self.tabs.tab("History"))
        self.history_panel.pack(fill="both", expand=True)

        self.settings_panel = SettingsPanel(
            self.tabs.tab("Settings"),
            settings=self.settings,
            on_max_workers_change=self.queue_manager.set_max_workers,
        )
        self.settings_panel.pack(fill="both", expand=True)

    def _show_ffmpeg_warning_if_needed(self) -> None:
        if not self._ffmpeg_available:
            banner = ctk.CTkLabel(
                self,
                text="⚠  ffmpeg not found — MP4 H.264/H.265, MP3, and MKV require ffmpeg. Install it and restart.",
                text_color="orange",
                font=ctk.CTkFont(size=11),
            )
            banner.pack(side="bottom", fill="x", padx=10, pady=(0, 4))

    def _start_poll(self) -> None:
        self._poll_ui_queue()

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                update = self.ui_queue.get_nowait()
                self.queue_panel.apply_update(update)
                if update.status == "done":
                    job = next(
                        (j for j in self.queue_manager.jobs if j.job_id == update.job_id),
                        None,
                    )
                    if job:
                        self.history_panel.add_entry(job)
        except queue_module.Empty:
            pass
        self.after(100, self._poll_ui_queue)
```

- [ ] **Step 2: Verify app launches (no UI tests — visual check)**

```bash
python main.py
```

Expected: window opens with "Queue", "History", "Settings" tabs. Will show import errors for missing panels — that's expected at this stage. If it crashes with `ModuleNotFoundError: ui.queue_panel`, create a temporary stub:

```python
# ui/queue_panel.py (temporary stub — replace in Task 8)
import customtkinter as ctk
class QueuePanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs): super().__init__(master)
    def apply_update(self, update): pass
```

```python
# ui/settings_panel.py (temporary stub — replace in Task 7)
import customtkinter as ctk
class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs): super().__init__(master)
```

```python
# ui/history_panel.py (temporary stub — replace in Task 10)
import customtkinter as ctk
class HistoryPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs): super().__init__(master)
    def add_entry(self, job): pass
```

- [ ] **Step 3: Commit**

```bash
git add ui/app.py ui/queue_panel.py ui/settings_panel.py ui/history_panel.py
git commit -m "feat(ui): add main App window with tabview and poll loop"
```

---

## Task 7: Settings Panel

**Files:**
- Modify: `ui/settings_panel.py` (replace stub)

- [ ] **Step 1: Replace ui/settings_panel.py**

```python
# ui/settings_panel.py
import customtkinter as ctk
from tkinter import filedialog
from core.settings import SettingsManager

class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, settings: SettingsManager, on_max_workers_change, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._settings = settings
        self._on_max_workers_change = on_max_workers_change
        self._build()

    def _build(self) -> None:
        pad = {"padx": 20, "pady": 8}

        # --- Cookies path ---
        ctk.CTkLabel(self, text="Default Cookies.txt Path", anchor="w").pack(fill="x", **pad)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 8))
        self._cookies_var = ctk.StringVar(value=self._settings.get("cookies_path") or "")
        ctk.CTkEntry(row, textvariable=self._cookies_var, placeholder_text="No file selected").pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ctk.CTkButton(row, text="Browse", width=80, command=self._pick_cookies).pack(side="left")

        # --- Output folder ---
        ctk.CTkLabel(self, text="Default Output Folder", anchor="w").pack(fill="x", **pad)
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=20, pady=(0, 8))
        self._output_var = ctk.StringVar(value=self._settings.get("output_dir") or "")
        ctk.CTkEntry(row2, textvariable=self._output_var, placeholder_text="Downloads/Videos").pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ctk.CTkButton(row2, text="Browse", width=80, command=self._pick_output).pack(side="left")

        # --- Default format ---
        ctk.CTkLabel(self, text="Default Format", anchor="w").pack(fill="x", **pad)
        self._format_var = ctk.StringVar(value=self._settings.get("default_format") or "mp4-h264")
        ctk.CTkOptionMenu(
            self, variable=self._format_var,
            values=["mp4-h264", "mp4-h265", "webm", "mp3", "mkv"],
            command=lambda v: self._settings.set("default_format", v),
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # --- Default quality ---
        ctk.CTkLabel(self, text="Default Quality", anchor="w").pack(fill="x", **pad)
        self._quality_var = ctk.StringVar(value=self._settings.get("default_quality") or "best")
        ctk.CTkOptionMenu(
            self, variable=self._quality_var,
            values=["best", "1080p", "720p", "480p", "audio"],
            command=lambda v: self._settings.set("default_quality", v),
        ).pack(anchor="w", padx=20, pady=(0, 8))

        # --- Max workers ---
        ctk.CTkLabel(self, text="Max Concurrent Downloads", anchor="w").pack(fill="x", **pad)
        self._workers_var = ctk.IntVar(value=self._settings.get("max_workers") or 3)
        slider_row = ctk.CTkFrame(self, fg_color="transparent")
        slider_row.pack(fill="x", padx=20, pady=(0, 8))
        self._workers_label = ctk.CTkLabel(slider_row, text=str(self._workers_var.get()), width=20)
        self._workers_label.pack(side="right")
        ctk.CTkSlider(
            slider_row, from_=1, to=5, number_of_steps=4,
            variable=self._workers_var, command=self._on_slider,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        # --- Save button ---
        ctk.CTkButton(self, text="Save Settings", command=self._save).pack(anchor="w", padx=20, pady=16)

    def _pick_cookies(self) -> None:
        path = filedialog.askopenfilename(
            title="Select cookies.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._cookies_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self._output_var.set(path)

    def _on_slider(self, value) -> None:
        n = int(value)
        self._workers_label.configure(text=str(n))

    def _save(self) -> None:
        self._settings.set("cookies_path", self._cookies_var.get())
        self._settings.set("output_dir", self._output_var.get())
        self._settings.set("default_format", self._format_var.get())
        self._settings.set("default_quality", self._quality_var.get())
        n = int(self._workers_var.get())
        self._settings.set("max_workers", n)
        self._on_max_workers_change(n)
```

- [ ] **Step 2: Launch and verify Settings tab visually**

```bash
python main.py
```

Expected: Settings tab shows all controls — cookies path browser, output folder browser, format/quality dropdowns, workers slider, Save button.

- [ ] **Step 3: Commit**

```bash
git add ui/settings_panel.py
git commit -m "feat(ui): implement settings panel with file pickers and sliders"
```

---

## Task 8: DownloadRow Widget (Progress Panel)

**Files:**
- Replace: `ui/progress_panel.py`

- [ ] **Step 1: Replace ui/progress_panel.py**

```python
# ui/progress_panel.py
import customtkinter as ctk
from tkinter import filedialog
from core.queue_manager import DownloadJob

STATUS_COLORS = {
    "queued": "#888888",
    "downloading": "#3b82f6",
    "done": "#22c55e",
    "failed": "#ef4444",
}

class DownloadRow(ctk.CTkFrame):
    def __init__(self, master, job: DownloadJob, on_remove, on_set_cookies, **kwargs):
        super().__init__(master, fg_color="#2b2b2b", corner_radius=8, **kwargs)
        self._job = job
        self._on_remove = on_remove
        self._on_set_cookies = on_set_cookies
        self._build()

    def _build(self) -> None:
        self.pack_configure(fill="x", padx=4, pady=3)

        # Top row: URL + status badge + buttons
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 2))

        domain = self._truncate_url(self._job.url)
        ctk.CTkLabel(top, text=domain, anchor="w", font=ctk.CTkFont(size=12)).pack(
            side="left", fill="x", expand=True
        )

        self._status_label = ctk.CTkLabel(
            top, text=self._job.status.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=STATUS_COLORS.get(self._job.status, "#888"),
            width=90, anchor="e",
        )
        self._status_label.pack(side="left", padx=(4, 0))

        ctk.CTkButton(top, text="🍪", width=28, height=24,
                      command=self._pick_cookies, fg_color="transparent",
                      hover_color="#3a3a3a").pack(side="left", padx=(4, 0))
        ctk.CTkButton(top, text="✕", width=28, height=24,
                      command=lambda: self._on_remove(self._job.job_id),
                      fg_color="transparent", hover_color="#3a3a3a",
                      text_color="#ef4444").pack(side="left", padx=(2, 0))

        # Progress bar
        self._progress_bar = ctk.CTkProgressBar(self, height=6)
        self._progress_bar.pack(fill="x", padx=8, pady=(2, 0))
        self._progress_bar.set(0)

        # Bottom row: speed + eta + error
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=8, pady=(2, 6))
        self._detail_label = ctk.CTkLabel(
            bottom, text="", anchor="w",
            font=ctk.CTkFont(size=10), text_color="#888888"
        )
        self._detail_label.pack(side="left")

    def apply_update(self, progress: float, speed: str, eta: str,
                     status: str, error: str = "", output_path: str = "") -> None:
        self._progress_bar.set(progress / 100.0)
        color = STATUS_COLORS.get(status, "#888")
        self._status_label.configure(text=status.upper(), text_color=color)

        if status == "downloading":
            self._detail_label.configure(text=f"{speed}  ·  ETA {eta}")
        elif status == "done":
            self._detail_label.configure(text=f"✓ Saved to {output_path or 'output folder'}")
        elif status == "failed":
            self._detail_label.configure(text=f"✗ {error}", text_color="#ef4444")
        else:
            self._detail_label.configure(text="")

    def _pick_cookies(self) -> None:
        path = filedialog.askopenfilename(
            title="Select cookies.txt for this URL",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._on_set_cookies(self._job.job_id, path)

    @staticmethod
    def _truncate_url(url: str, max_len: int = 60) -> str:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            display = parsed.netloc + parsed.path
        except Exception:
            display = url
        return display if len(display) <= max_len else display[:max_len - 3] + "..."
```

- [ ] **Step 2: Commit**

```bash
git add ui/progress_panel.py
git commit -m "feat(ui): add DownloadRow widget with progress bar and status badge"
```

---

## Task 9: Queue Panel (Full Implementation)

**Files:**
- Replace: `ui/queue_panel.py`

- [ ] **Step 1: Replace ui/queue_panel.py**

```python
# ui/queue_panel.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from core.queue_manager import QueueManager, FORMAT_STRINGS
from core.settings import SettingsManager
from core.downloader import ProgressUpdate
from ui.progress_panel import DownloadRow

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

FORMATS = ["mp4-h264", "mp4-h265", "webm", "mp3", "mkv"]
QUALITIES = ["best", "1080p", "720p", "480p", "audio"]

class QueuePanel(ctk.CTkFrame):
    def __init__(self, master, queue_manager: QueueManager,
                 settings: SettingsManager, ffmpeg_available: bool, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._qm = queue_manager
        self._settings = settings
        self._ffmpeg_available = ffmpeg_available
        self._rows: dict[str, DownloadRow] = {}  # job_id → DownloadRow
        self._build()

    def _build(self) -> None:
        # Two-column layout
        self.columnconfigure(0, weight=2, minsize=280)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

    # ── LEFT PANEL ────────────────────────────────────────────────────────────

    def _build_left_panel(self) -> None:
        left = ctk.CTkFrame(self, corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Add URLs", font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        self._url_box = ctk.CTkTextbox(left, height=160, font=ctk.CTkFont(size=11))
        self._url_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self._url_box.insert("0.0", "Paste URLs here, one per line…")
        self._url_box.bind("<FocusIn>", self._clear_placeholder)

        # Format selector
        ctk.CTkLabel(left, text="Format", anchor="w", font=ctk.CTkFont(size=11)).grid(
            row=2, column=0, sticky="w", padx=12, pady=(0, 2)
        )
        self._format_var = ctk.StringVar(value=self._settings.get("default_format") or "mp4-h264")
        format_values = FORMATS if self._ffmpeg_available else ["webm"]
        ctk.CTkOptionMenu(left, variable=self._format_var, values=format_values).grid(
            row=3, column=0, sticky="ew", padx=12, pady=(0, 6)
        )

        # Quality selector
        ctk.CTkLabel(left, text="Quality", anchor="w", font=ctk.CTkFont(size=11)).grid(
            row=4, column=0, sticky="w", padx=12, pady=(0, 2)
        )
        self._quality_var = ctk.StringVar(value=self._settings.get("default_quality") or "best")
        ctk.CTkOptionMenu(left, variable=self._quality_var, values=QUALITIES).grid(
            row=5, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        # Add button
        ctk.CTkButton(left, text="Add to Queue", command=self._add_urls).grid(
            row=6, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        # Cookies zone
        self._cookies_label_var = ctk.StringVar(value=self._cookies_display_text())
        cookies_frame = ctk.CTkFrame(left, fg_color="#1e1e1e", corner_radius=6)
        cookies_frame.grid(row=7, column=0, sticky="ew", padx=12, pady=(0, 10))
        cookies_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(cookies_frame, textvariable=self._cookies_label_var,
                     font=ctk.CTkFont(size=10), text_color="#aaaaaa", anchor="w",
                     wraplength=200).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkButton(cookies_frame, text="Choose cookies.txt", height=28,
                      command=self._pick_global_cookies).grid(row=1, column=0,
                                                               sticky="ew", padx=8, pady=(0, 8))

        if DND_AVAILABLE:
            cookies_frame.drop_target_register(DND_FILES)
            cookies_frame.dnd_bind("<<Drop>>", self._on_cookies_drop)

    def _clear_placeholder(self, _event=None) -> None:
        content = self._url_box.get("0.0", "end").strip()
        if content == "Paste URLs here, one per line…":
            self._url_box.delete("0.0", "end")

    def _cookies_display_text(self) -> str:
        path = self._settings.get("cookies_path")
        if path and Path(path).exists():
            return f"🍪 {Path(path).name} ✓"
        elif path:
            return f"🍪 {Path(path).name} ✗ (not found)"
        return "🍪 No cookies loaded"

    def _pick_global_cookies(self) -> None:
        path = filedialog.askopenfilename(
            title="Select cookies.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._settings.set("cookies_path", path)
            self._cookies_label_var.set(self._cookies_display_text())

    def _on_cookies_drop(self, event) -> None:
        path = event.data.strip().strip("{}")
        if path.endswith(".txt"):
            self._settings.set("cookies_path", path)
            self._cookies_label_var.set(self._cookies_display_text())

    # ── RIGHT PANEL ───────────────────────────────────────────────────────────

    def _build_right_panel(self) -> None:
        right = ctk.CTkFrame(self, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(right, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkButton(toolbar, text="▶ Start All", width=90,
                      command=self._start_all).pack(side="left", padx=(0, 4))
        ctk.CTkButton(toolbar, text="■ Stop All", width=90, fg_color="#555",
                      command=self._stop_all).pack(side="left", padx=(0, 4))
        ctk.CTkButton(toolbar, text="Clear Done", width=90, fg_color="#555",
                      command=self._clear_done).pack(side="left")

        # Scrollable list
        self._scroll_frame = ctk.CTkScrollableFrame(right, label_text="")
        self._scroll_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._scroll_frame.columnconfigure(0, weight=1)

    # ── ACTIONS ───────────────────────────────────────────────────────────────

    def _add_urls(self) -> None:
        raw = self._url_box.get("0.0", "end").strip()
        if not raw or raw == "Paste URLs here, one per line…":
            return
        urls = [u for u in raw.splitlines() if u.strip()]
        if not urls:
            return
        cookies_path = self._settings.get("cookies_path") or ""
        output_dir = self._settings.get("output_dir") or str(Path.home() / "Downloads" / "Videos")
        jobs = self._qm.add_jobs(
            urls,
            format=self._format_var.get(),
            quality=self._quality_var.get(),
            cookies_path=cookies_path,
            output_dir=output_dir,
        )
        for job in jobs:
            row = DownloadRow(
                self._scroll_frame, job=job,
                on_remove=self._remove_job,
                on_set_cookies=self._set_job_cookies,
            )
            row.pack(fill="x", padx=4, pady=3)
            self._rows[job.job_id] = row
        self._url_box.delete("0.0", "end")

    def _start_all(self) -> None:
        cookies_path = self._settings.get("cookies_path") or ""
        if not cookies_path or not Path(cookies_path).exists():
            if cookies_path:
                proceed = messagebox.askyesno(
                    "Missing cookies.txt",
                    f"cookies.txt not found:\n{cookies_path}\n\nProceed without cookies?",
                )
                if not proceed:
                    return
        self._qm.start_all()

    def _stop_all(self) -> None:
        self._qm.stop_all()

    def _clear_done(self) -> None:
        done_ids = {j.job_id for j in self._qm.jobs if j.status in ("done", "failed")}
        self._qm.clear_done()
        for job_id in done_ids:
            row = self._rows.pop(job_id, None)
            if row:
                row.destroy()

    def _remove_job(self, job_id: str) -> None:
        self._qm.remove_job(job_id)
        row = self._rows.pop(job_id, None)
        if row:
            row.destroy()

    def _set_job_cookies(self, job_id: str, path: str) -> None:
        job = next((j for j in self._qm.jobs if j.job_id == job_id), None)
        if job:
            job.cookies_path = path

    # ── UPDATE HANDLER ────────────────────────────────────────────────────────

    def apply_update(self, update: ProgressUpdate) -> None:
        row = self._rows.get(update.job_id)
        if row:
            row.apply_update(
                progress=update.progress,
                speed=update.speed,
                eta=update.eta,
                status=update.status,
                error=update.error,
                output_path=update.output_path,
            )
```

- [ ] **Step 2: Launch and verify Queue tab visually**

```bash
python main.py
```

Expected: Queue tab shows left panel (URL box, format/quality dropdowns, Add button, cookies zone) and right panel (Start All / Stop All / Clear Done buttons, empty scrollable list).

- [ ] **Step 3: Commit**

```bash
git add ui/queue_panel.py
git commit -m "feat(ui): implement full queue panel with URL input, format selection, and cookies zone"
```

---

## Task 10: History Panel

**Files:**
- Replace: `ui/history_panel.py`

- [ ] **Step 1: Replace ui/history_panel.py**

```python
# ui/history_panel.py
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from core.queue_manager import DownloadJob

class HistoryPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._entries: list[DownloadJob] = []
        self._build()

    def _build(self) -> None:
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(self, label_text="Completed Downloads")
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self._scroll.columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._scroll, text="No completed downloads yet.",
            text_color="#666666", font=ctk.CTkFont(size=12)
        )
        self._empty_label.pack(pady=40)

    def add_entry(self, job: DownloadJob) -> None:
        self._entries.append(job)
        self._empty_label.pack_forget()
        self._render_entry(job)

    def _render_entry(self, job: DownloadJob) -> None:
        frame = ctk.CTkFrame(self._scroll, fg_color="#2b2b2b", corner_radius=8)
        frame.pack(fill="x", padx=4, pady=3)

        title = Path(job.output_path).stem if job.output_path else job.url
        size_str = self._file_size(job.output_path)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(top, text=title, anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkLabel(top, text=f"{job.format}  ·  {size_str}  ·  {timestamp}",
                     font=ctk.CTkFont(size=10), text_color="#888888").pack(side="right")

        bottom = ctk.CTkFrame(frame, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(2, 8))
        ctk.CTkLabel(bottom, text=job.output_path or "—", anchor="w",
                     font=ctk.CTkFont(size=10), text_color="#aaaaaa").pack(
            side="left", fill="x", expand=True
        )
        output_path = job.output_path
        ctk.CTkButton(bottom, text="Open Folder", width=90, height=26,
                      command=lambda: self._open_folder(output_path)).pack(side="right")

    @staticmethod
    def _file_size(path: str) -> str:
        try:
            size = Path(path).stat().st_size
            for unit in ("B", "KB", "MB", "GB"):
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        except Exception:
            return "—"

    @staticmethod
    def _open_folder(file_path: str) -> None:
        try:
            folder = str(Path(file_path).parent)
            if platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            elif platform.system() == "Windows":
                subprocess.Popen(["explorer", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass
```

- [ ] **Step 2: Launch and verify History tab**

```bash
python main.py
```

Expected: History tab shows "No completed downloads yet." message. After a real download completes, it will populate automatically.

- [ ] **Step 3: Commit**

```bash
git add ui/history_panel.py
git commit -m "feat(ui): implement history panel with file size and open folder"
```

---

## Task 11: End-to-End Smoke Test

**Goal:** Verify a real download works with a public video (no cookies needed).

- [ ] **Step 1: Launch the app**

```bash
python main.py
```

- [ ] **Step 2: Paste a public test URL**

Use a short public YouTube video URL (e.g., any video under 1 min). Paste into the URL box, select `webm` format (no ffmpeg needed), click "Add to Queue", then "▶ Start All".

Expected: progress bar animates from 0→100%, status badge turns green "DONE", History tab gains an entry.

- [ ] **Step 3: Verify error handling**

Paste an invalid URL (e.g., `https://not-a-real-site.xyz/video`), click Add → Start All.

Expected: status badge turns red "FAILED", error message shown below the progress bar.

- [ ] **Step 4: Verify cookies.txt remembered across restart**

Set a cookies.txt path in Settings → Save. Close the app, reopen it. Check that the cookies.txt path is still shown in the Queue tab cookies zone.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: complete PrivateVideoDownloader v1.0"
```

---

## Task 12: Enable TkinterDnD2 Drag-Drop (Optional Enhancement)

**Goal:** Replace the base `CTk` window with `TkinterDnD.Tk` so drag-drop works on the cookies zone.

> Skip this task if `tkinterdnd2` import fails during Task 11 testing. The app works without it.

- [ ] **Step 1: Modify main.py to use TkinterDnD**

```python
# main.py
import sys

def main():
    try:
        from tkinterdnd2 import TkinterDnD
        import customtkinter as ctk
        # Monkey-patch CTk to use TkinterDnD as the base Tk class
        ctk.CTk.__bases__ = (TkinterDnD.Tk,)
    except ImportError:
        pass  # drag-drop unavailable, app runs fine without it

    from ui.app import App
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Launch and test drag-drop**

```bash
python main.py
```

Drag a `cookies.txt` file from Finder/Explorer onto the cookies zone in the Queue tab. Expected: the file path is loaded and the label updates to show the filename with ✓.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: enable tkinterdnd2 drag-drop for cookies.txt"
```
