from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

APP_NAME = "DiskCleaner"

def config_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

SETTINGS_PATH = config_dir() / "settings.json"

@dataclass
class Settings:
    clean_temp: bool = True
    clean_thumbnails: bool = True
    clean_duplicates: bool = True
    clean_logs: bool = False
    clean_empty_folders: bool = False
    clean_browser_cache: bool = False
    clean_recycle_bin: bool = False
    clean_old_windows: bool = False
    clean_downloads: bool = False
    clean_memory_dumps: bool = False
    exclude_folders: list[str] = field(default_factory=list)
    max_file_size_mb: int = 500
    confirm_deletions: bool = True
    use_recycle_bin_for_user_files: bool = True
    downloads_max_age_days: int = 30

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        if not SETTINGS_PATH.exists():
            return s
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return s

        for k, v in data.items():
            if not hasattr(s, k):
                continue
            current = getattr(s, k)
            try:
                if isinstance(current, bool):
                    setattr(s, k, bool(v))
                elif isinstance(current, int):
                    setattr(s, k, int(v))
                elif isinstance(current, list):
                    setattr(s, k, [str(x) for x in v])
                else:
                    setattr(s, k, v)
            except (TypeError, ValueError):
                pass
        return s

    def save(self) -> None:
        try:
            SETTINGS_PATH.write_text(
                json.dumps(asdict(self), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            print(f"[settings] ошибка сохранения настроек: {e}")