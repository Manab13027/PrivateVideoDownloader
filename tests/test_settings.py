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
