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
        ctk.CTkLabel(top, text=title, anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(
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
