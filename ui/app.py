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

        self._show_ffmpeg_warning_if_needed()
        self._build_ui()
        self._start_poll()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
            # Pack banner before tabview so it isn't hidden by expand=True
            banner.pack(side="bottom", fill="x", padx=10, pady=(0, 4))

    def _start_poll(self) -> None:
        self._poll_ui_queue()

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                update = self.ui_queue.get_nowait()
                try:
                    self.queue_panel.apply_update(update)
                    if update.status == "done":
                        job = next(
                            (j for j in self.queue_manager.jobs if j.job_id == update.job_id),
                            None,
                        )
                        if job:
                            self.history_panel.add_entry(job)
                except Exception:
                    pass
        except queue_module.Empty:
            pass
        self.after(100, self._poll_ui_queue)

    def _on_close(self) -> None:
        self.queue_manager.shutdown()
        self.destroy()
