"""install.py 寫回 settings.json 的格式。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import install  # noqa: E402


def test_save_settings_writes_lf_only(tmp_path, monkeypatch):
    """Windows 上不得把換行寫成 CRLF，否則同步 settings.json 的 repo 會出現假修改。"""
    path = tmp_path / "settings.json"
    path.write_bytes(b'{\n  "env": {}\n}\n')
    monkeypatch.setattr(install, "SETTINGS_PATH", path)

    install.save_settings({"env": {}, "hooks": {"Stop": []}})

    data = path.read_bytes()
    assert b"\r\n" not in data
    assert data.endswith(b"}\n")
