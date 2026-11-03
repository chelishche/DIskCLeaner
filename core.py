from __future__ import annotations

import ctypes
import hashlib
import os
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from config import Settings

LogFn = Callable[[str, str], None]
StatusFn = Callable[[str], None]

EXEC_EXTS = {".exe", ".dll", ".sys", ".msi", ".bat", ".cmd", ".ps1", ".scr"}
MAX_SKIP_LOGS = 50

@dataclass
class Context:
    settings: Settings
    log: LogFn
    status: StatusFn
    cancelled: bool = False
    _skip_logs: int = 0

    def log_info(self, m: str) -> None:
        self.log(m, "info")

    def log_warn(self, m: str) -> None:
        self.log(m, "warning")

    def log_err(self, m: str) -> None:
        self.log(m, "error")

    def log_ok(self, m: str) -> None:
        self.log(m, "success")

    def log_skip(self, m: str) -> None:
        if self._skip_logs < MAX_SKIP_LOGS:
            self._skip_logs += 1
            self.log(m, "warning")
            if self._skip_logs == MAX_SKIP_LOGS:
                self.log("... дальнейшие пропуски не логируются", "debug")

@dataclass
class ScanItem:
    path: Path
    size: int
    is_dir: bool = False

@dataclass
class ScanResult:
    key: str
    title: str
    items: list[ScanItem] = field(default_factory=list)

    @property
    def total_size(self) -> int:
        return sum(i.size for i in self.items)

    def __len__(self) -> int:
        return len(self.items)

@dataclass
class CleanStats:
    deleted: int = 0
    freed: int = 0
    errors: int = 0

    def merge(self, other: "CleanStats") -> "CleanStats":
        self.deleted += other.deleted
        self.freed += other.freed
        self.errors += other.errors
        return self

def human_size(n: int) -> str:
    if n <= 0:
        return "0 Б"
    units = ("Б", "КБ", "МБ", "ГБ", "ТБ")
    f = float(n)
    for u in units:
        if f < 1024:
            return f"{f:.1f} {u}" if u != "Б" else f"{int(f)} Б"
        f /= 1024
    return f"{f:.1f} ПБ"

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False

def _is_excluded(path: Path, excludes: list[str]) -> bool:
    for ex in excludes:
        if not ex:
            continue
        try:
            if _is_within(path, Path(ex)):
                return True
        except OSError:
            continue
    return False

def _can_write(directory: Path) -> bool:
    try:
        test = directory / f".sdc_test_{os.getpid()}"
        test.touch()
        test.unlink()
        return True
    except OSError:
        return False

def basic_safety(path: Path, ctx: Context, allow_executables: bool = False) -> bool:
    try:
        st = path.stat()
    except OSError:
        return False
    if not path.is_file():
        return False
    if st.st_size > ctx.settings.max_file_size_mb * 1024 * 1024:
        ctx.log_skip(f"Пропуск большого файла: {path} ({human_size(st.st_size)})")
        return False
    if not allow_executables and path.suffix.lower() in EXEC_EXTS:
        ctx.log_skip(f"Пропуск исполняемого файла: {path}")
        return False
    if _is_excluded(path, ctx.settings.exclude_folders):
        return False
    return True

def _walk_files(root: Path):
    try:
        for dirpath, _dirnames, filenames in os.walk(root, onerror=lambda _e: None):
            for fn in filenames:
                yield Path(dirpath) / fn
    except OSError:
        return

def sha256_file(path: Path, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(block), b""):
            h.update(chunk)
    return h.hexdigest()

def _delete_file(path: Path, use_trash: bool, ctx: Context) -> bool:
    if use_trash:
        try:
            from send2trash import send2trash
            send2trash(str(path))
            return True
        except ImportError:
            ctx.log_warn("send2trash не установлен — удаление безвозвратное")
        except Exception as e:
            ctx.log_warn(f"Не удалось отправить в корзину {path}: {e}")
            return False
    try:
        path.unlink()
        return True
    except OSError as e:
        ctx.log_warn(f"Не удалось удалить {path}: {e}")
        return False

def _delete_items(ctx: Context, result: ScanResult, use_trash: bool = False) -> CleanStats:
    stats = CleanStats()
    for item in result.items:
        if ctx.cancelled:
            break
        if item.is_dir:
            try:
                item.path.rmdir()
                stats.deleted += 1
            except OSError as e:
                stats.errors += 1
                ctx.log_warn(f"Не удалось удалить папку {item.path}: {e}")
            continue
        if _delete_file(item.path, use_trash, ctx):
            stats.deleted += 1
            stats.freed += item.size
        else:
            stats.errors += 1
    return stats

class Category:
    key: str = ""
    title: str = ""
    enabled_attr: str = ""

    def is_enabled(self, s: Settings) -> bool:
        return bool(getattr(s, self.enabled_attr, False))

    def scan(self, ctx: Context) -> ScanResult:
        raise NotImplementedError

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        raise NotImplementedError

def _home() -> Path:
    return Path(os.environ.get("USERPROFILE") or Path.home())

def _sysroot() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows"))

class TempFilesCategory(Category):
    key = "temp"
    title = "Временные файлы"
    enabled_attr = "clean_temp"

    def _roots(self) -> list[Path]:
        profile = _home()
        return [
            _sysroot() / "Temp",
            profile / "AppData" / "Local" / "Temp",
            profile / "AppData" / "Local" / "Microsoft" / "Windows" / "INetCache",
            profile / "AppData" / "Local" / "Microsoft" / "Windows" / "INetCookies",
            Path(tempfile.gettempdir()),
        ]

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        seen: set[Path] = set()
        for root in self._roots():
            if ctx.cancelled:
                break
            if not root.is_dir():
                continue
            try:
                resolved = root.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)

            ctx.status(f"Сканирование: {root.name}")
            for path in _walk_files(root):
                if ctx.cancelled:
                    break
                if basic_safety(path, ctx, allow_executables=True):
                    try:
                        result.items.append(ScanItem(path, path.stat().st_size))
                    except OSError:
                        pass
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(ctx, result, use_trash=False)


class ThumbnailCacheCategory(Category):
    key = "thumbnails"
    title = "Кэш эскизов"
    enabled_attr = "clean_thumbnails"

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        explorer = _home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Explorer"
        if not explorer.is_dir():
            return result
        for path in explorer.glob("thumbcache_*.db"):
            if ctx.cancelled:
                break
            if basic_safety(path, ctx):
                try:
                    result.items.append(ScanItem(path, path.stat().st_size))
                except OSError:
                    pass
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(ctx, result, use_trash=False)


class DuplicatesCategory(Category):
    key = "duplicates"
    title = "Дубликаты файлов"
    enabled_attr = "clean_duplicates"

    USER_DIRS = ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos")

    def _roots(self) -> list[Path]:
        home = _home()
        return [home / d for d in self.USER_DIRS if (home / d).is_dir()]

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        size_map: dict[int, list[Path]] = defaultdict(list)
        for root in self._roots():
            if ctx.cancelled:
                break
            for path in _walk_files(root):
                if ctx.cancelled:
                    break
                if not basic_safety(path, ctx):
                    continue
                try:
                    size_map[path.stat().st_size].append(path)
                except OSError:
                    pass

        candidates = {s: ps for s, ps in size_map.items() if len(ps) > 1}
        total = len(candidates)

        for i, (_size, paths) in enumerate(candidates.items()):
            if ctx.cancelled:
                break
            ctx.status(f"Хэширование группы {i + 1}/{total}...")
            hash_map: dict[str, list[Path]] = defaultdict(list)
            for p in paths:
                if ctx.cancelled:
                    break
                try:
                    hash_map[sha256_file(p)].append(p)
                except OSError:
                    pass
            for group in hash_map.values():
                if len(group) < 2:
                    continue
                try:
                    group.sort(key=lambda p: p.stat().st_mtime)
                except OSError:
                    pass
                for dup in group[1:]:
                    try:
                        result.items.append(ScanItem(dup, dup.stat().st_size))
                    except OSError:
                        pass

        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(
            ctx, result, use_trash=ctx.settings.use_recycle_bin_for_user_files
        )


class SystemLogsCategory(Category):
    key = "logs"
    title = "Системные логи"
    enabled_attr = "clean_logs"

    EXTS = {".log", ".txt", ".dmp", ".tmp"}

    def _roots(self) -> list[Path]:
        sr = _sysroot()
        return [sr / "Logs", sr / "System32" / "LogFiles", sr / "Debug"]

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        for root in self._roots():
            if ctx.cancelled:
                break
            if not root.is_dir():
                continue
            if not _can_write(root):
                ctx.log_warn(f"Нет прав на запись в {root} — запустите от администратора")
                continue
            for path in _walk_files(root):
                if ctx.cancelled:
                    break
                if path.suffix.lower() not in self.EXTS:
                    continue
                if basic_safety(path, ctx):
                    try:
                        result.items.append(ScanItem(path, path.stat().st_size))
                    except OSError:
                        pass
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(ctx, result, use_trash=False)


class EmptyFoldersCategory(Category):
    key = "empty_folders"
    title = "Пустые папки"
    enabled_attr = "clean_empty_folders"
    USER_DIRS = DuplicatesCategory.USER_DIRS

    def _roots(self) -> list[Path]:
        home = _home()
        return [home / d for d in self.USER_DIRS if (home / d).is_dir()]

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        for root in self._roots():
            if ctx.cancelled:
                break
            for dirpath, _dirnames, _filenames in os.walk(
                root, topdown=False, onerror=lambda _e: None
            ):
                if ctx.cancelled:
                    break
                p = Path(dirpath)
                if p == root:
                    continue
                try:
                    if _is_excluded(p, ctx.settings.exclude_folders):
                        continue
                    if not any(p.iterdir()):
                        result.items.append(ScanItem(p, 0, is_dir=True))
                except OSError:
                    pass
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(ctx, result, use_trash=False)

class BrowserCacheCategory(Category):
    key = "browser_cache"
    title = "Кэш браузеров"
    enabled_attr = "clean_browser_cache"

    def _roots(self) -> list[Path]:
        profile = _home()
        appdata = profile / "AppData" / "Local"
        roots = [
            appdata / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
            appdata / "Google" / "Chrome" / "User Data" / "Default" / "Media Cache",
            appdata / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
            appdata / "Opera Software" / "Opera Stable" / "Cache",
        ]
        firefox = appdata / "Mozilla" / "Firefox" / "Profiles"
        if firefox.is_dir():
            try:
                for prof in firefox.iterdir():
                    cache = prof / "cache2"
                    if cache.is_dir():
                        roots.append(cache)
            except OSError:
                pass
        return [r for r in roots if r.is_dir()]

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        for root in self._roots():
            if ctx.cancelled:
                break
            ctx.status(f"Сканирование: {root.parent.name}/{root.name}")
            for path in _walk_files(root):
                if ctx.cancelled:
                    break
                if basic_safety(path, ctx):
                    try:
                        result.items.append(ScanItem(path, path.stat().st_size))
                    except OSError:
                        pass
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(ctx, result, use_trash=False)

class RecycleBinCategory(Category):
    key = "recycle_bin"
    title = "Корзина"
    enabled_attr = "clean_recycle_bin"

    def _info(self) -> tuple[int, int]:
        if os.name != "nt":
            return (0, 0)
        from ctypes import wintypes, Structure, c_longlong, sizeof, byref

        class RBInfo(Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("i64Size", c_longlong),
                ("i64NumItems", c_longlong),
            ]

        info = RBInfo()
        info.cbSize = sizeof(RBInfo)
        try:
            res = ctypes.windll.shell32.SHQueryRecycleBinW(None, byref(info))
            if res == 0:
                return (info.i64Size, info.i64NumItems)
        except Exception:
            pass
        return (0, 0)

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        size, count = self._info()
        if count > 0:
            result.items.append(ScanItem(Path("<recycle_bin>"), size))
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        stats = CleanStats()
        if os.name != "nt":
            ctx.log_warn("Очистка корзины поддерживается только в Windows")
            return stats
        SHERB_NOCONFIRMATION = 0x1
        SHERB_NOPROGRESSUI = 0x2
        SHERB_NOSOUND = 0x4
        flags = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        try:
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
            stats.deleted = 1
            stats.freed = result.total_size
        except Exception as e:
            stats.errors += 1
            ctx.log_warn(f"Не удалось очистить корзину: {e}")
        return stats


class OldWindowsCategory(Category):
    key = "old_windows"
    title = "Старые файлы Windows"
    enabled_attr = "clean_old_windows"

    def _roots(self) -> list[Path]:
        sr = _sysroot()
        return [
            sr / "SoftwareDistribution" / "Download",
            sr / "Logs",
            sr / "Minidump",
            sr / "Prefetch",
        ]

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        for root in self._roots():
            if ctx.cancelled:
                break
            if not root.is_dir():
                continue
            if not _can_write(root):
                ctx.log_warn(f"Нет прав на {root} — запустите от администратора")
                continue
            ctx.status(f"Сканирование: {root.name}")
            for path in _walk_files(root):
                if ctx.cancelled:
                    break
                if basic_safety(path, ctx):
                    try:
                        result.items.append(ScanItem(path, path.stat().st_size))
                    except OSError:
                        pass
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(ctx, result, use_trash=False)


class DownloadsCategory(Category):
    key = "downloads"
    title = "Старые загрузки"
    enabled_attr = "clean_downloads"

    def _roots(self) -> list[Path]:
        return [_home() / "Downloads"]

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        cutoff = time.time() - ctx.settings.downloads_max_age_days * 86400
        for root in self._roots():
            if not root.is_dir():
                continue
            for path in _walk_files(root):
                if ctx.cancelled:
                    break
                try:
                    if path.stat().st_mtime >= cutoff:
                        continue
                except OSError:
                    continue
                if basic_safety(path, ctx):
                    try:
                        result.items.append(ScanItem(path, path.stat().st_size))
                    except OSError:
                        pass
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(ctx, result, use_trash=True)


class MemoryDumpsCategory(Category):
    key = "memory_dumps"
    title = "Дампы памяти"
    enabled_attr = "clean_memory_dumps"

    def scan(self, ctx: Context) -> ScanResult:
        result = ScanResult(self.key, self.title)
        sr = _sysroot()
        targets = [
            (sr / "Minidump", "*.dmp"),
            (sr / "MEMORY.DMP", None),
            (_home() / "AppData" / "Local" / "CrashDumps", "*.dmp"),
        ]
        for base, pattern in targets:
            if ctx.cancelled:
                break
            if pattern is None:
                paths = [base] if base.is_file() else []
            else:
                if not base.is_dir():
                    continue
                paths = list(base.glob(pattern))
            for path in paths:
                if ctx.cancelled:
                    break
                if basic_safety(path, ctx):
                    try:
                        result.items.append(ScanItem(path, path.stat().st_size))
                    except OSError:
                        pass
        return result

    def clean(self, ctx: Context, result: ScanResult) -> CleanStats:
        return _delete_items(ctx, result, use_trash=False)

CATEGORIES: list[Category] = [
    TempFilesCategory(),
    ThumbnailCacheCategory(),
    DuplicatesCategory(),
    SystemLogsCategory(),
    EmptyFoldersCategory(),
    BrowserCacheCategory(),
    RecycleBinCategory(),
    OldWindowsCategory(),
    DownloadsCategory(),
    MemoryDumpsCategory(),
]