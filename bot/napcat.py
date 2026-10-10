# -*- coding: utf-8 -*-
"""NapCat 托管：自动查找并启动 NapCat，等待 OneBot 端口就绪。

NapCat 扫码登录由 NapCat 自带窗口处理；本模块只负责拉起进程与探活。
"""
import os
import socket
import subprocess
import threading
import time

# 常见 NapCat 安装位置（Node 绿色版优先，其次 Shell 版）
SEARCH_PATHS = [
    "C:\\NapCatNode",                              # Node 版（自带 QQ，绿色免管理员）
    "C:\\NapCat",                                  # Shell 版（借用系统 QQ）
    os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Downloads", "packinput", "NapCat.Shell"),
    os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Downloads", "NapCat.Shell"),
    os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop", "NapCat.Shell"),
    "C:\\NapCat.Shell",
]


def find_napcat():
    for p in SEARCH_PATHS:
        if os.path.isdir(p):
            return p
    return None


def _port_open(host, port, timeout=2):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def napcat_running(ws_port=3001, http_port=3000):
    return _port_open("127.0.0.1", ws_port) or _port_open("127.0.0.1", http_port)


def launch_napcat(on_log=None):
    """若 NapCat 已在运行则直接返回 True；否则尝试启动。"""
    log = on_log or (lambda *a: None)
    if napcat_running():
        log("✅ NapCat 已在运行")
        return True
    root = find_napcat()
    if not root:
        log("⚠️ 未找到 NapCat（请先安装 NapCat.Shell）")
        return False
    # 常见启动器（Node 版 napcat.bat / 绿色一键；Shell 版 exe/bat）
    candidates = [
        os.path.join(root, "napcat.bat"),          # Node/OneKey 绿色版（自带 QQ）
        os.path.join(root, "NapCat.Shell.exe"),
        os.path.join(root, "napcat.napcat.exe"),
        os.path.join(root, "启动.bat"),
        os.path.join(root, "start.bat"),
        os.path.join(root, "napcat", "launcher.bat"),  # Shell 版入口
    ]
    for exe in candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe], cwd=root, shell=True)
                log(f"🚀 已启动 NapCat: {os.path.basename(exe)}")
                return True
            except Exception as e:
                log(f"❌ 启动失败: {e}")
                continue
    log(f"⚠️ NapCat 目录存在但未找到可执行入口：{root}")
    return False


def wait_ready(ws_port=3001, timeout=120, on_log=None):
    """等待 NapCat 端口就绪（登录后可连接）。"""
    log = on_log or (lambda *a: None)
    start = time.time()
    while time.time() - start < timeout:
        if napcat_running(ws_port):
            log("✅ NapCat 端口就绪")
            return True
        time.sleep(3)
    log("⏰ 等待 NapCat 超时（请确认扫码登录完成）")
    return False
