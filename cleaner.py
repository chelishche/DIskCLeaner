from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import base64
from datetime import datetime
from pathlib import Path
import ctypes
from PyQt6.QtGui import QIcon
import psutil
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QTextCursor, QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QFormLayout, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSpinBox, QSplitter, QTextEdit,
    QVBoxLayout, QWidget,
)

from config import Settings
from core import CATEGORIES, CleanStats, ScanResult, human_size, is_admin
from worker import CleanWorker, ScanWorker


CHECK_SVG_B64 = base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    b'<path fill="#ffffff" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>'
    b'</svg>'
).decode()


STYLE = """
/* ---------- Base ---------- */
QWidget {
    background: #0e1014;
    color: #e6e8eb;
    font-family: "Segoe UI Variable", "Segoe UI", "Inter", -apple-system, sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background: #0e1014; }

/* ---------- Cards ---------- */
QFrame#Card {
    background: #16181f;
    border: 1px solid #232630;
    border-radius: 14px;
}
QFrame#StatCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1a1d24, stop:1 #15171d);
    border: 1px solid #232630;
    border-radius: 12px;
}

/* ---------- Labels ---------- */
QLabel { background: transparent; color: #e6e8eb; }
QLabel#Title {
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
}
QLabel#SectionTitle {
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
}
QLabel#MutedLabel { color: #7a7f94; font-size: 11px; }
QLabel#ValueLabel { color: #ff8c00; font-size: 22px; font-weight: 700; }
QLabel#CaptionLabel {
    color: #7a7f94;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
}

/* ---------- Buttons ---------- */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff8c00, stop:1 #ff6b00);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 12px 26px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.8px;
    min-height: 20px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffa033, stop:1 #ff8c00);
}
QPushButton:pressed { background: #d95f00; }
QPushButton:disabled { background: #22252f; color: #4d5161; }

QPushButton#Secondary {
    background: #1c1f28;
    color: #e6e8eb;
    border: 1px solid #2d3140;
}
QPushButton#Secondary:hover {
    background: #242836;
    border: 1px solid #3d4256;
    color: #ffffff;
}
QPushButton#Secondary:disabled {
    background: #16181f;
    color: #4d5161;
    border: 1px solid #232630;
}

QPushButton#Danger {
    background: #1c1013;
    color: #ff6b6b;
    border: 1px solid #3d1a22;
}
QPushButton#Danger:hover {
    background: #2a1418;
    border: 1px solid #6b292f;
    color: #ff8787;
}
QPushButton#Danger:disabled {
    background: #14161c;
    color: #3d4152;
    border: 1px solid #1d2028;
}

QPushButton#Ghost {
    background: transparent;
    color: #a0a4b8;
    border: 1px solid transparent;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0;
}
QPushButton#Ghost:hover { background: #1c1f28; color: #ffffff; }

/* ---------- Progress ---------- */
QProgressBar {
    background: #0a0c10;
    border: none;
    border-radius: 7px;
    text-align: center;
    height: 22px;
    color: #ffffff;
    font-size: 10px;
    font-weight: 700;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff8c00, stop:1 #ff6b00);
    border-radius: 7px;
}

/* ---------- Text / List ---------- */
QTextEdit, QListWidget {
    background: #0a0c10;
    border: 1px solid #1e2129;
    border-radius: 10px;
    color: #d4d7e0;
    font-family: "Cascadia Mono", "Consolas", "Menlo", monospace;
    font-size: 12px;
    padding: 10px;
    selection-background-color: #ff8c00;
    selection-color: #ffffff;
}
QListWidget::item { padding: 6px 8px; border-radius: 6px; }
QListWidget::item:selected { background: #ff8c00; color: #ffffff; }
QListWidget::item:hover:!selected { background: #1c1f28; }

/* ---------- Checkboxes ---------- */
QCheckBox {
    color: #d4d7e0;
    spacing: 12px;
    padding: 6px 0;
    background: transparent;
}
QCheckBox:hover { color: #ffffff; }
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #2d3140;
    background: #0a0c10;
}
QCheckBox::indicator:hover { border: 2px solid #ff8c00; }
QCheckBox::indicator:checked {
    background: #ff8c00;
    border: 2px solid #ff8c00;
    image: url(data:image/svg+xml;base64,__CHECK_SVG__);
}

/* ---------- SpinBox ---------- */
QSpinBox {
    background: #0a0c10;
    border: 1px solid #2d3140;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    selection-background-color: #ff8c00;
    min-width: 100px;
}
QSpinBox:focus { border: 1px solid #ff8c00; }
QSpinBox::up-button, QSpinBox::down-button {
    background: #1c1f28;
    border: none;
    width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #ff8c00; }

/* ---------- Scrollbar ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px; }
QScrollBar::handle:vertical {
    background: #2d3140; border-radius: 3px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #ff8c00; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 4px; }
QScrollBar::handle:horizontal {
    background: #2d3140; border-radius: 3px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #ff8c00; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ---------- Misc ---------- */
QToolTip {
    background: #1c1f28;
    color: #ffffff;
    border: 1px solid #2d3140;
    border-radius: 6px;
    padding: 6px 10px;
}
QSplitter::handle { background: transparent; width: 12px; }
QSplitter::handle:hover { background: #1c1f28; }
QScrollArea { background: transparent; border: none; }
""".replace("__CHECK_SVG__", CHECK_SVG_B64)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def resource_path(rel: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / rel
    return Path(__file__).resolve().parent / rel

def set_windows_app_id(app_id: str = "DiskCleaner.App") -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

class RingProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.setFixedSize(56, 56)

    def setValue(self, v: int) -> None:
        self._value = max(0, min(100, int(v)))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(6, 6, self.width() - 12, self.height() - 12)
        pen = QPen(QColor("#22252f"))
        pen.setWidth(5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)
        if self._value < 70:
            color = QColor("#4ade80")
        elif self._value < 90:
            color = QColor("#fbbf24")
        else:
            color = QColor("#ef4444")
        pen = QPen(color)
        pen.setWidth(5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        span = int(-self._value / 100 * 360 * 16)
        p.drawArc(rect, 90 * 16, span)
        p.setPen(QColor("#ffffff"))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{self._value}%")

class DiskIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self._ring = RingProgress()
        layout.addWidget(self._ring)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        cap = QLabel("ДИСК")
        cap.setObjectName("CaptionLabel")
        self._label = QLabel("—")
        self._label.setStyleSheet("color:#d4d7e0; font-size:12px;")
        text_layout.addWidget(cap)
        text_layout.addWidget(self._label)
        layout.addLayout(text_layout)
        self.refresh()

    def refresh(self) -> None:
        try:
            anchor = Path.home().anchor or "/"
            usage = psutil.disk_usage(anchor)
            self._ring.setValue(int(usage.percent))
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            self._label.setText(
                f"{free_gb:.1f} из {total_gb:.1f} ГБ свободно"
            )
        except Exception:
            self._label.setText("Нет данных")
            self._ring.setValue(0)

class ConfirmDialog(QDialog):
    def __init__(self, results: list[ScanResult], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Подтверждение очистки")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        title = QLabel("Подтвердить удаление?")
        title.setStyleSheet(
            "color:#fff; font-size:18px; font-weight:700;"
        )
        layout.addWidget(title)
        hint = QLabel("Будут удалены следующие элементы:")
        hint.setStyleSheet("color:#7a7f94; font-size:12px;")
        layout.addWidget(hint)
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)
        total_size = 0
        total_count = 0
        for res in results:
            if not len(res):
                continue
            row = QHBoxLayout()
            name = QLabel(f"•  {res.title}")
            name.setStyleSheet("color:#e6e8eb;")
            value = QLabel(f"{len(res)} элем.  ·  {human_size(res.total_size)}")
            value.setStyleSheet("color:#ff8c00; font-weight:600;")
            row.addWidget(name)
            row.addStretch()
            row.addWidget(value)
            card_layout.addLayout(row)
            total_size += res.total_size
            total_count += len(res)

        if total_count:
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setStyleSheet("background:#232630; border:none;")
            card_layout.addWidget(sep)

            row = QHBoxLayout()
            lbl = QLabel("Итого")
            lbl.setStyleSheet("color:#fff; font-weight:700; font-size:14px;")
            val = QLabel(f"{total_count} элем.  ·  {human_size(total_size)}")
            val.setStyleSheet(
                "color:#ff8c00; font-weight:700; font-size:14px;"
            )
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            card_layout.addLayout(row)
        layout.addWidget(card)
        warn = QLabel(
            "⚠  Часть файлов будет удалена безвозвратно."
        )
        warn.setStyleSheet(
            "color:#fbbf24; background:#1c1808; padding:12px 14px;"
            "border-radius:8px; border:1px solid #3d3216;"
        )
        layout.addWidget(warn)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Отмена")
        cancel.setObjectName("Secondary")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        ok = QPushButton("Удалить")
        ok.clicked.connect(self.accept)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    @classmethod
    def ask(cls, results, parent) -> bool:
        return cls(results, parent).exec() == QDialog.DialogCode.Accepted

class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.resize(580, 760)
        self.setMinimumSize(520, 560)
        self._settings = settings
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setStyleSheet("QWidget { background: transparent; }")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(16)
        header = QLabel("Настройки очистки")
        header.setStyleSheet(
            "color:#fff; font-size:18px; font-weight:700;"
        )
        cl.addWidget(header)
        cat_card = QFrame()
        cat_card.setObjectName("Card")
        cat_layout = QVBoxLayout(cat_card)
        cat_layout.setContentsMargins(18, 18, 18, 18)
        cat_layout.setSpacing(10)
        cat_title = QLabel("КАТЕГОРИИ")
        cat_title.setObjectName("CaptionLabel")
        cat_layout.addWidget(cat_title)
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(2)
        self._cat_vars: dict[str, QCheckBox] = {}
        for i, cat in enumerate(CATEGORIES):
            cb = QCheckBox(cat.title)
            cb.setChecked(getattr(settings, cat.enabled_attr))
            grid.addWidget(cb, i // 2, i % 2)
            self._cat_vars[cat.enabled_attr] = cb
        cat_layout.addLayout(grid)
        cl.addWidget(cat_card)
        opt_card = QFrame()
        opt_card.setObjectName("Card")
        opt_layout = QVBoxLayout(opt_card)
        opt_layout.setContentsMargins(18, 18, 18, 18)
        opt_layout.setSpacing(12)
        opt_title = QLabel("ОГРАНИЧЕНИЯ")
        opt_title.setObjectName("CaptionLabel")
        opt_layout.addWidget(opt_title)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._max_size = QSpinBox()
        self._max_size.setRange(1, 10000)
        self._max_size.setSuffix(" МБ")
        self._max_size.setValue(settings.max_file_size_mb)
        form.addRow("Макс. размер файла:", self._max_size)
        self._dl_age = QSpinBox()
        self._dl_age.setRange(1, 3650)
        self._dl_age.setSuffix(" дн.")
        self._dl_age.setValue(settings.downloads_max_age_days)
        form.addRow("Возраст старых загрузок:", self._dl_age)
        opt_layout.addLayout(form)
        self._confirm = QCheckBox("Подтверждать перед очисткой")
        self._confirm.setChecked(settings.confirm_deletions)
        opt_layout.addWidget(self._confirm)
        self._use_trash = QCheckBox(
            "Отправлять пользовательские файлы в корзину"
        )
        self._use_trash.setChecked(settings.use_recycle_bin_for_user_files)
        opt_layout.addWidget(self._use_trash)
        cl.addWidget(opt_card)
        ex_card = QFrame()
        ex_card.setObjectName("Card")
        ex_layout = QVBoxLayout(ex_card)
        ex_layout.setContentsMargins(18, 18, 18, 18)
        ex_layout.setSpacing(10)
        ex_title = QLabel("ИСКЛЮЧЁННЫЕ ПАПКИ")
        ex_title.setObjectName("CaptionLabel")
        ex_layout.addWidget(ex_title)
        self._excl = QListWidget()
        self._excl.setMinimumHeight(110)
        for ex in settings.exclude_folders:
            self._excl.addItem(ex)
        ex_layout.addWidget(self._excl)
        row = QHBoxLayout()
        add_btn = QPushButton("Добавить")
        add_btn.setObjectName("Secondary")
        add_btn.clicked.connect(self._add_exclusion)
        rem_btn = QPushButton("Удалить")
        rem_btn.setObjectName("Danger")
        rem_btn.clicked.connect(self._remove_exclusion)
        row.addWidget(add_btn)
        row.addWidget(rem_btn)
        row.addStretch()
        ex_layout.addLayout(row)
        cl.addWidget(ex_card)
        cl.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Отмена")
        cancel.setObjectName("Secondary")
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)
        save = QPushButton("Сохранить")
        save.clicked.connect(self._save)
        btn_row.addWidget(save)
        main_layout.addLayout(btn_row)

    def _add_exclusion(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Папка для исключения")
        if d and not self._excl.findItems(d, Qt.MatchFlag.MatchExactly):
            self._excl.addItem(d)

    def _remove_exclusion(self) -> None:
        for item in self._excl.selectedItems():
            self._excl.takeItem(self._excl.row(item))

    def _save(self) -> None:
        for attr, cb in self._cat_vars.items():
            setattr(self._settings, attr, cb.isChecked())
        self._settings.max_file_size_mb = self._max_size.value()
        self._settings.downloads_max_age_days = self._dl_age.value()
        self._settings.confirm_deletions = self._confirm.isChecked()
        self._settings.use_recycle_bin_for_user_files = (
            self._use_trash.isChecked()
        )
        self._settings.exclude_folders = [
            self._excl.item(i).text() for i in range(self._excl.count())
        ]
        self._settings.save()
        self.accept()

class StatCard(QFrame):
    def __init__(self, caption: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        cap = QLabel(caption)
        cap.setObjectName("CaptionLabel")
        self._value = QLabel(value)
        self._value.setObjectName("ValueLabel")
        layout.addWidget(cap)
        layout.addWidget(self._value)

    def setValue(self, text: str) -> None:
        self._value.setText(text)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Disk Cleaner")
        self.resize(1120, 760)
        self.setMinimumSize(940, 680)
        self._settings = Settings.load()
        self._scan_results: list[ScanResult] = []
        self._worker: ScanWorker | CleanWorker | None = None
        self._pending_clean = False
        self._setup_ui()
        if not is_admin():
            self._append_log(
                "Программа запущена без прав администратора. "
                "Очистка системных папок может быть ограничена.",
                "warning",
            )

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(18)
        header = QHBoxLayout()
        header.setSpacing(14)
        logo = QLabel("◆")
        logo.setStyleSheet("color:#ff8c00; font-size:26px; background:transparent;")
        header.addWidget(logo)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("DISK CLEANER")
        t.setObjectName("Title")
        sub = QLabel("Очистка диска · безопасно и быстро")
        sub.setObjectName("MutedLabel")
        titles.addWidget(t)
        titles.addWidget(sub)
        header.addLayout(titles)
        header.addStretch()
        self._disk = DiskIndicator()
        header.addWidget(self._disk)
        root.addLayout(header)
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setHandleWidth(12)
        left = QFrame()
        left.setObjectName("Card")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(22, 22, 22, 22)
        left_layout.setSpacing(18)
        st_title = QLabel("СТАТИСТИКА")
        st_title.setObjectName("SectionTitle")
        left_layout.addWidget(st_title)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._files_card = StatCard("УДАЛЕНО ФАЙЛОВ", "0")
        self._space_card = StatCard("ОСВОБОЖДЕНО", "0 Б")
        stats_row.addWidget(self._files_card)
        stats_row.addWidget(self._space_card)
        left_layout.addLayout(stats_row)
        left_layout.addSpacing(4)
        cap = QLabel("ТЕКУЩАЯ ОПЕРАЦИЯ")
        cap.setObjectName("CaptionLabel")
        left_layout.addWidget(cap)
        self._status_value = QLabel("Готов к работе")
        self._status_value.setStyleSheet(
            "color:#e6e8eb; font-size:14px; font-weight:500;"
        )
        self._status_value.setWordWrap(True)
        left_layout.addWidget(self._status_value)
        left_layout.addSpacing(10)
        pcap = QLabel("ПРОГРЕСС")
        pcap.setObjectName("CaptionLabel")
        left_layout.addWidget(pcap)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("%p%")
        left_layout.addWidget(self._progress)
        left_layout.addStretch()
        body.addWidget(left)
        right = QFrame()
        right.setObjectName("Card")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(22, 22, 22, 22)
        right_layout.setSpacing(12)
        log_header = QHBoxLayout()
        log_title = QLabel("ЖУРНАЛ ОПЕРАЦИЙ")
        log_title.setObjectName("SectionTitle")
        log_header.addWidget(log_title)
        log_header.addStretch()
        clear_btn = QPushButton("Очистить")
        clear_btn.setObjectName("Ghost")
        clear_btn.clicked.connect(lambda: self._log.clear())
        log_header.addWidget(clear_btn)
        right_layout.addLayout(log_header)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        right_layout.addWidget(self._log)
        body.addWidget(right)
        body.setSizes([420, 660])
        root.addWidget(body, 1)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._scan_btn = QPushButton("АНАЛИЗ")
        self._scan_btn.setObjectName("Secondary")
        self._scan_btn.clicked.connect(self._on_scan)
        btn_row.addWidget(self._scan_btn)
        self._clean_btn = QPushButton("ОЧИСТИТЬ")
        self._clean_btn.clicked.connect(self._on_clean)
        btn_row.addWidget(self._clean_btn)
        self._stop_btn = QPushButton("ОСТАНОВИТЬ")
        self._stop_btn.setObjectName("Danger")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._stop_btn)
        btn_row.addStretch()
        self._settings_btn = QPushButton("НАСТРОЙКИ")
        self._settings_btn.setObjectName("Secondary")
        self._settings_btn.clicked.connect(self._on_settings)
        btn_row.addWidget(self._settings_btn)
        root.addLayout(btn_row)
        self._disk_timer = QTimer(self)
        self._disk_timer.timeout.connect(self._disk.refresh)
        self._disk_timer.start(5000)

    def _append_log(self, message: str, level: str = "info") -> None:
        colors = {
            "info":    "#60a5fa",
            "success": "#4ade80",
            "warning": "#fbbf24",
            "error":   "#ef4444",
            "debug":   "#6b7280",
        }
        color = colors.get(level, "#d4d7e0")
        ts = datetime.now().strftime("%H:%M:%S")
        html = (
            f'<span style="color:#7a7f94;">{ts}</span>&nbsp;'
            f'<span style="color:{color};font-weight:600;">{level.upper()}</span>&nbsp;'
            f'<span style="color:#d4d7e0;">{_escape(message)}</span>'
        )
        self._log.append(html)

        doc = self._log.document()
        if doc.blockCount() > 2000:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                500,
            )
            cursor.removeSelectedText()

    def _enabled_categories(self) -> list:
        return [c for c in CATEGORIES if getattr(self._settings, c.enabled_attr)]

    def _on_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._append_log("Настройки сохранены", "success")

    def _on_scan(self) -> None:
        if self._worker is not None:
            return
        cats = self._enabled_categories()
        if not cats:
            QMessageBox.warning(self, "Внимание", "Не выбрано ни одной категории.")
            return

        self._scan_results = []
        self._reset_for_work()
        self._append_log("Начат анализ...", "info")

        self._worker = ScanWorker(self._settings, cats)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.status.connect(self._status_value.setText)
        self._worker.log.connect(self._append_log)
        self._worker.category_done.connect(self._on_scan_category)
        self._worker.completed.connect(self._on_scan_complete)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_scan_category(self, res: ScanResult) -> None:
        self._scan_results.append(res)
        if len(res):
            self._append_log(
                f"{res.title}: {len(res)} элем., {human_size(res.total_size)}",
                "info",
            )
            for item in res.items[:5]:
                self._append_log(f"  • {item.path}", "debug")
            if len(res) > 5:
                self._append_log(f"  ... и ещё {len(res) - 5}", "debug")
        else:
            self._append_log(f"{res.title}: ничего не найдено", "debug")

    def _on_scan_complete(self, results: list[ScanResult]) -> None:
        total_size = sum(r.total_size for r in results)
        total_count = sum(len(r) for r in results)
        self._append_log(
            f"Анализ завершён. Найдено {total_count} элем., {human_size(total_size)}",
            "success",
        )
        self._status_value.setText("Анализ завершён")

    def _on_clean(self) -> None:
        if self._worker is not None:
            return
        cats = self._enabled_categories()
        if not cats:
            QMessageBox.warning(self, "Внимание", "Не выбрано ни одной категории.")
            return

        if not self._scan_results:
            if self._pending_clean:
                self._pending_clean = False
                QMessageBox.information(self, "Пусто", "Нет файлов для очистки.")
                return
            self._pending_clean = True
            self._append_log("Анализ перед очисткой...", "info")
            self._on_scan()
            return

        cats_map = {c.key: c for c in cats}
        have = {r.key for r in self._scan_results}
        missing = [c for c in cats if c.key not in have]
        if missing:
            self._append_log(
                "Для новых категорий нужен повторный анализ: "
                + ", ".join(c.title for c in missing),
                "warning",
            )

        tasks = [
            (cats_map[r.key], r) for r in self._scan_results
            if r.key in cats_map and len(r)
        ]
        if not tasks:
            self._pending_clean = False
            QMessageBox.information(
                self, "Пусто", "Нет файлов для очистки. Запустите анализ."
            )
            return

        if self._settings.confirm_deletions:
            if not ConfirmDialog.ask([r for _, r in tasks], self):
                self._pending_clean = False
                self._append_log("Очистка отменена пользователем", "warning")
                return

        self._pending_clean = False
        self._reset_for_work()
        self._append_log("Начата очистка...", "info")

        self._worker = CleanWorker(self._settings, tasks)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.status.connect(self._status_value.setText)
        self._worker.log.connect(self._append_log)
        self._worker.completed.connect(self._on_clean_complete)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_clean_complete(self, stats: CleanStats) -> None:
        self._files_card.setValue(str(stats.deleted))
        self._space_card.setValue(human_size(stats.freed))
        self._append_log(
            f"Очистка завершена. Удалено: {stats.deleted}, "
            f"освобождено: {human_size(stats.freed)}, ошибок: {stats.errors}",
            "success" if stats.errors == 0 else "warning",
        )
        self._status_value.setText("Очистка завершена")
        self._disk.refresh()
        self._scan_results = []

    def _on_worker_failed(self, msg: str) -> None:
        self._append_log(f"Ошибка: {msg}", "error")
        self._status_value.setText("Ошибка")

    def _on_worker_finished(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        self._scan_btn.setEnabled(True)
        self._clean_btn.setEnabled(True)
        self._settings_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

        if self._pending_clean:
            QTimer.singleShot(50, self._on_clean)

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._pending_clean = False
            self._append_log("Запрошена остановка...", "warning")
            self._stop_btn.setEnabled(False)

    def _reset_for_work(self) -> None:
        self._progress.setValue(0)
        self._files_card.setValue("0")
        self._space_card.setValue("0 Б")
        self._status_value.setText("Работа...")
        self._scan_btn.setEnabled(False)
        self._clean_btn.setEnabled(False)
        self._settings_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

    def closeEvent(self, event):
        if self._worker is not None:
            ans = QMessageBox.question(
                self,
                "Подтверждение",
                "Идёт операция. Прервать и закрыть?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._worker.cancel()
            self._worker.wait(3000)
        event.accept()


def main() -> None:
    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    icon_path = resource_path("icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

match __name__:
    case "__main__":
        main()