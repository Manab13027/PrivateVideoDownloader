# PrivateVideoDownloader — Design Spec
Date: 2026-05-03

## Goal
A cross-platform (macOS + Windows) standalone desktop application for downloading videos from YouTube and other platforms using cookies exported by the "Get Cookies.txt Locally" browser extension. Supports a multi-URL download queue, compressed output formats, and a real-time progress UI.

---

## Stack
- **Language:** Python 3.11+
- **GUI:** CustomTkinter (modern Tkinter wrapper — dark mode, clean widgets)
- **Downloader:** yt-dlp (subprocess, stdout-parsed for progress)
- **Concurrency:** `threading.ThreadPoolExecutor` (max 3 workers, configurable)
- **Settings persistence:** JSON at `~/.pvd_settings.json`

---

## Project Structure

```
PrivateVideoDownloader/
├── main.py                  # entry point — launches CTk app
├── ui/
│   ├── app.py               # main CTk window, tab container
│   ├── queue_panel.py       # URL input, queue list, per-row controls
│   ├── progress_panel.py    # per-job progress bars, status labels
│   └── settings_panel.py   # cookies path, output folder, format defaults
├── core/
│   ├── downloader.py        # yt-dlp subprocess wrapper, stdout parser
│   ├── queue_manager.py     # DownloadJob model, ThreadPoolExecutor
│   └── settings.py          # load/save ~/.pvd_settings.json
├── requirements.txt
└── docs/
    └── superpowers/specs/
        └── 2026-05-03-video-downloader-design.md
```

---

## UI Layout

Two-panel tabbed window (CustomTkinter CTkTabview):

### Tab 1 — Queue (default view)
**Left panel — URL Input:**
- Multi-line text area: paste one URL per line
- Format selector: MP4 H.264 | MP4 H.265 | WebM | MP3 | MKV
- Quality selector: Best | 1080p | 720p | 480p | Audio Only
- "Add to Queue" button
- Global cookies.txt indicator (filename + ✓/✗ status)
- Drag-and-drop zone for cookies.txt

**Right panel — Active Queue:**
- List of DownloadJob rows, each showing:
  - URL (truncated, domain shown)
  - Progress bar (0–100%)
  - Speed (MB/s) + ETA
  - Status badge: Queued | Downloading | Done | Failed
  - 🍪 button → per-URL cookies.txt override file picker
  - ✕ button → remove from queue
- "Start All" / "Stop All" / "Clear Done" toolbar buttons
  - Stop All: cancels active downloads, resets them to Queued status (restartable)

### Tab 2 — History
- Completed downloads log (title, format, size, timestamp, output path)
- "Open Folder" button per row

### Tab 3 — Settings
- Default cookies.txt path (file picker + remembered)
- Default output folder (file picker + remembered)
- Default format + quality
- Max concurrent downloads slider (1–5)

---

## Cookies Handling

- **Global default:** user loads one cookies.txt (drag-drop or file picker). Persisted to settings. Covers all domains — yt-dlp selects the right cookies per domain automatically.
- **Per-URL override:** each queue row has a 🍪 button. Clicking opens a file picker to assign a custom cookies.txt for that URL only. Falls back to global if not set.
- **Validation:** before starting the queue, app checks that the cookies.txt path exists. If missing, shows a warning dialog — does not silently proceed.

---

## Download Job Model

```python
@dataclass
class DownloadJob:
    url: str
    format: str          # e.g. "mp4-h264", "webm", "mp3", "mkv"
    quality: str         # e.g. "best", "1080p", "720p"
    cookies_path: str    # per-URL override, or global default
    status: str          # "queued" | "downloading" | "done" | "failed"
    progress: float      # 0.0–100.0
    speed: str           # e.g. "2.4 MB/s"
    eta: str             # e.g. "12s"
    error: str           # populated on failure
    output_path: str     # populated on success
```

---

## Data Flow

```
User pastes URLs + selects format/quality
  → QueueManager.add_jobs() creates DownloadJob per URL
  → ThreadPoolExecutor.submit(worker, job) for each

Worker (background thread):
  → builds yt-dlp command:
       yt-dlp --cookies <cookies_path>
              --format <format_string>
              --output "%(title)s.%(ext)s"
              --newline   (force line-by-line progress)
              <url>
  → streams stdout line by line
  → parses "[download]  67.3% of  128.5MiB at  2.41MiB/s ETA 00:12"
  → pushes ProgressUpdate(job_id, progress, speed, eta) to ui_queue

UI thread (polls every 100ms via CTk.after()):
  → drains ui_queue
  → updates progress bar + labels for each job_id
```

---

## Output Formats → yt-dlp Format Strings

| User selection | yt-dlp `--format` value |
|---|---|
| MP4 H.264 | `bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]` |
| MP4 H.265 | `bestvideo[ext=mp4][vcodec^=hev]+bestaudio[ext=m4a]/best[ext=mp4]` |
| WebM | `bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]` |
| MP3 | `bestaudio --extract-audio --audio-format mp3` |
| MKV | `bestvideo+bestaudio/best --merge-output-format mkv` |

Quality modifiers (1080p, 720p, etc.) added as `[height<=1080]` filters.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| yt-dlp exits non-zero | Job → Failed, error message shown inline under progress bar |
| Network drop mid-download | yt-dlp retries 3x (`--retries 3`), then marks Failed |
| Missing cookies.txt | Warning dialog before queue starts, queue blocked |
| Unsupported / invalid URL | Rejected immediately on "Add", shown as inline tooltip error |
| ffmpeg not found | Startup check — warning banner shown, format options requiring ffmpeg disabled |

---

## Settings File (`~/.pvd_settings.json`)

```json
{
  "cookies_path": "/Users/you/cookies.txt",
  "output_dir": "/Users/you/Downloads/Videos",
  "default_format": "mp4-h264",
  "default_quality": "best",
  "max_workers": 3
}
```

---

## Dependencies (`requirements.txt`)

```
customtkinter>=5.2.0
yt-dlp>=2024.1.0
```

**System requirements:**
- Python 3.11+
- ffmpeg (for format merging/conversion) — checked at startup

---

## Out of Scope
- Browser cookie auto-extraction (manual cookies.txt load only)
- Built-in video player or preview
- Scheduled/recurring downloads
- Subtitle download (can be added later via `--write-subs`)
