# -*- coding: utf-8 -*-
"""主窗口：左侧导航 + 右侧页面栈 + 系统托盘。"""
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QStackedWidget, QLabel, QSystemTrayIcon, QMenu,
)
from PySide6.QtGui import QIcon, QAction

from .pages import (
    StatusPage, ChatPage, PersonaPage, WhitelistPage,
    ProactivePage, StickerSettingsPage,
)


def _app_dir():
    if getattr(__import__("sys"), "frozen", False):
        return os.path.dirname(os.path.abspath(__import__("sys").executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MainWindow(QMainWindow):
    def __init__(self, bot, bridge, tray_only=False):
        super().__init__()
        self.bot = bot
        self.bridge = bridge
        self._tray_only = tray_only
        self._quitting = False
        self.setWindowTitle("ds聊天智能 · 大肥鱼控制台")
        self.resize(980, 680)
        self._build()
        self._apply_style()
        self._build_tray()

    def _build_tray(self):
        icon_path = os.path.join(_app_dir(), "icon.ico")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else self.style().standardIcon(self.style().SP_ComputerIcon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("ds聊天智能 · 大肥鱼运行中")
        menu = QMenu()
        act_show = QAction("打开控制台", self)
        act_show.triggered.connect(self._show_window)
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(self._quit_app)
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self._show_window()

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self._quitting = True
        self.tray.hide()
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()

    def show_from_start(self):
        """根据启动模式决定：正常显示 或 静默到托盘。"""
        if self._tray_only:
            self.hide()
            self.tray.showMessage(
                "ds聊天智能",
                "大肥鱼已在后台运行，双击托盘图标打开控制台",
                QSystemTrayIcon.Information,
                3000,
            )
        else:
            self._show_window()

    def closeEvent(self, event):
        """点 X：最小化到托盘，不退出。"""
        if self._quitting:
            event.accept()
            return
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "QQ赛博群友",
            "大肥鱼仍在后台运行，双击托盘图标打开控制台",
            QSystemTrayIcon.Information,
            2000,
        )

    def _build(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左侧导航
        nav = QListWidget()
        nav.setObjectName("nav")
        nav.setFixedWidth(150)
        for t in ("状态", "聊天", "人格设计", "白名单", "主动聊天", "表情库+设置"):
            nav.addItem(QListWidgetItem(t))
        nav.currentRowChanged.connect(self._switch)

        # 右侧页面
        self.stack = QStackedWidget()
        self.pages = {
            "状态": StatusPage(self.bot, self.bridge),
            "聊天": ChatPage(self.bot),
            "人格设计": PersonaPage(self.bot),
            "白名单": WhitelistPage(self.bot),
            "主动聊天": ProactivePage(self.bot),
            "表情库+设置": StickerSettingsPage(self.bot, self.bridge),
        }
        for p in self.pages.values():
            self.stack.addWidget(p)

        root.addWidget(nav)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        nav.setCurrentRow(0)

    def _switch(self, row):
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)

    def _apply_style(self):
        self.setStyleSheet("""
QMainWindow { background: #f5f6fa; }
QListWidget#nav { background: #232946; border: none; padding-top: 12px; }
QListWidget#nav::item { color: #c8cce0; padding: 14px 18px; font-size: 14px;
    border-left: 3px solid transparent; }
QListWidget#nav::item:selected { background: #2d3561; color: #ffffff;
    border-left: 3px solid #ff9f1c; }
QListWidget#nav::item:hover { background: #2d3561; }
QGroupBox#card { background: #ffffff; border: 1px solid #e2e4ea;
    border-radius: 8px; margin-top: 12px; }
QGroupBox#card::title { subcontrol-origin: margin; left: 12px; padding: 0 4px;
    color: #232946; font-weight: bold; }
QGroupBox { background: #ffffff; border: 1px solid #e2e4ea; border-radius: 8px;
    margin-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px;
    color: #232946; font-weight: bold; }
QPushButton { background: #ff9f1c; color: #ffffff; border: none;
    border-radius: 6px; padding: 8px 18px; font-size: 13px; font-weight: bold; }
QPushButton:hover { background: #ffb347; }
QPushButton:pressed { background: #e88b00; }
QLineEdit, QPlainTextEdit, QSpinBox { background: #ffffff; border: 1px solid #d5d8e0;
    border-radius: 6px; padding: 6px 8px; font-size: 13px; }
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #ff9f1c; }
QListWidget { background: #ffffff; border: 1px solid #e2e4ea; border-radius: 6px; }
QListWidget::item { padding: 6px 8px; }
QListWidget::item:selected { background: #fff3e0; color: #232946; }
QLabel { color: #3a3f58; font-size: 13px; }
QSplitter::handle { background: #e2e4ea; width: 2px; }
""")
