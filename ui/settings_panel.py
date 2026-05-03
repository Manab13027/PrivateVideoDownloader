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
