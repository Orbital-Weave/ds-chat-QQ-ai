# -*- coding: utf-8 -*-
"""入口：双击即用。窗口立即弹出；NapCat 检测/启动在后台执行，就绪后自动连接。"""
import ctypes
import os
import sys
import threading

os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from bot import config, napcat  # noqa: E402
from bot.core import BotCore  # noqa: E402
from gui.main_window import MainWindow  # noqa: E402
from gui.pages import LogBridge  # noqa: E402


def _single_instance_guard():
    """Windows 命名互斥锁：防止双击开多个实例导致消息重复回复。"""
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW(None, False, "Local\\QQBot_SingleInstance")
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return False
    except Exception:
        pass
    return True


def bootstrap():
    if not _single_instance_guard():
        QMessageBox.critical(None, "ds聊天智能",
                             "程序已在运行中，请勿重复打开。\n如需重启请先关闭现有窗口。")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("ds聊天智能")
    # 关窗口不退出进程（托盘模式下窗口隐藏但程序继续跑）
    app.setQuitOnLastWindowClosed(False)

    # 开机自启模式：命令行带 --tray 时静默到托盘，不弹主窗口
    tray_only = "--tray" in sys.argv

    bridge = LogBridge()

    def log(*a):
        bridge.log.emit(str(a[0]))

    def status(connected):
        bridge.status.emit(connected)

    # 1) 立即创建 BotCore 与窗口（秒开，不等待 NapCat）
    bot = BotCore(on_log=log, on_status=status)
    win = MainWindow(bot, bridge, tray_only=tray_only)
    win.show_from_start()

    # 2) 后台线程：NapCat 托管 + 机器人启动（NapCat 起来后 OneBot 自动重连）
    def worker():
        if not napcat.napcat_running():
            log("🔍 未检测到 NapCat，正在自动启动（首次会弹二维码）...")
            napcat.launch_napcat(on_log=log)
            napcat.wait_ready(timeout=120, on_log=log)
        else:
            log("✅ NapCat 已在运行")
        bot.start()

    threading.Thread(target=worker, daemon=True).start()

    # 3) 首次运行提示
    if not bot.api_key:
        QMessageBox.information(win, "需要配置", "请到「表情库+设置」页填入 DeepSeek API Key，并确认白名单。")

    return app.exec()


if __name__ == "__main__":
    sys.exit(bootstrap())
