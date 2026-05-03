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
