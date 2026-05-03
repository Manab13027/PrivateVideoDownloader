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
