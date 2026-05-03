import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from core.queue_manager import QueueManager, FORMAT_STRINGS
from core.settings import SettingsManager
from core.downloader import ProgressUpdate
from ui.progress_panel import DownloadRow

try:
    from tkinterdnd2 import DND_FILES
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
        self._rows: dict[str, DownloadRow] = {}
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=2, minsize=280)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

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

        ctk.CTkLabel(left, text="Format", anchor="w", font=ctk.CTkFont(size=11)).grid(
            row=2, column=0, sticky="w", padx=12, pady=(0, 2)
        )
        self._format_var = ctk.StringVar(value=self._settings.get("default_format") or "mp4-h264")
        format_values = FORMATS if self._ffmpeg_available else ["webm"]
        ctk.CTkOptionMenu(left, variable=self._format_var, values=format_values).grid(
            row=3, column=0, sticky="ew", padx=12, pady=(0, 6)
        )

        ctk.CTkLabel(left, text="Quality", anchor="w", font=ctk.CTkFont(size=11)).grid(
            row=4, column=0, sticky="w", padx=12, pady=(0, 2)
        )
        self._quality_var = ctk.StringVar(value=self._settings.get("default_quality") or "best")
        ctk.CTkOptionMenu(left, variable=self._quality_var, values=QUALITIES).grid(
            row=5, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        ctk.CTkButton(left, text="Add to Queue", command=self._add_urls).grid(
            row=6, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

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
            try:
                cookies_frame.drop_target_register(DND_FILES)
                cookies_frame.dnd_bind("<<Drop>>", self._on_cookies_drop)
            except Exception:
                pass

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

    def _build_right_panel(self) -> None:
        right = ctk.CTkFrame(self, corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(right, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        ctk.CTkButton(toolbar, text="▶ Start All", width=90,
                      command=self._start_all).pack(side="left", padx=(0, 4))
        ctk.CTkButton(toolbar, text="■ Stop All", width=90, fg_color="#555",
                      command=self._stop_all).pack(side="left", padx=(0, 4))
        ctk.CTkButton(toolbar, text="Clear Done", width=90, fg_color="#555",
                      command=self._clear_done).pack(side="left")

        self._scroll_frame = ctk.CTkScrollableFrame(right, label_text="")
        self._scroll_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self._scroll_frame.columnconfigure(0, weight=1)

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
        if cookies_path and not Path(cookies_path).exists():
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
