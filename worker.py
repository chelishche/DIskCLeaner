from __future__ import annotations
from PyQt6.QtCore import QThread, pyqtSignal
from config import Settings
from core import Category, CleanStats, Context, ScanResult, human_size

class ScanWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    log = pyqtSignal(str, str)
    category_done = pyqtSignal(object)
    completed = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, settings: Settings, categories: list[Category], parent=None):
        super().__init__(parent)
        self._settings = settings
        self._categories = categories
        self._ctx = Context(
            settings=settings,
            log=lambda m, lvl: self.log.emit(m, lvl),
            status=lambda s: self.status.emit(s),
        )

    def cancel(self) -> None:
        self._ctx.cancelled = True

    def run(self) -> None:
        try:
            results: list[ScanResult] = []
            n = max(1, len(self._categories))
            for i, cat in enumerate(self._categories):
                if self._ctx.cancelled:
                    break
                self.status.emit(f"Анализ: {cat.title}")
                res = cat.scan(self._ctx)
                results.append(res)
                self.category_done.emit(res)
                self.progress.emit(int((i + 1) / n * 100))
            self.completed.emit(results)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")

class CleanWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    log = pyqtSignal(str, str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        settings: Settings,
        tasks: list[tuple[Category, ScanResult]],
        parent=None,
    ):
        super().__init__(parent)
        self._settings = settings
        self._tasks = tasks
        self._ctx = Context(
            settings=settings,
            log=lambda m, lvl: self.log.emit(m, lvl),
            status=lambda s: self.status.emit(s),
        )

    def cancel(self) -> None:
        self._ctx.cancelled = True

    def run(self) -> None:
        try:
            total = CleanStats()
            n = max(1, len(self._tasks))
            for i, (cat, res) in enumerate(self._tasks):
                if self._ctx.cancelled:
                    break
                self.status.emit(f"Очистка: {cat.title}")
                stats = cat.clean(self._ctx, res)
                total.merge(stats)
                self.log.emit(
                    f"{cat.title}: удалено {stats.deleted}, "
                    f"освобождено {human_size(stats.freed)}, "
                    f"ошибок {stats.errors}",
                    "success" if stats.errors == 0 else "warning",
                )
                self.progress.emit(int((i + 1) / n * 100))
            self.completed.emit(total)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")