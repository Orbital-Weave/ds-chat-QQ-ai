# -*- coding: utf-8 -*-
"""桌面 UI（PySide6）：状态 / 聊天 / 人格 / 白名单 / 主动聊天 / 表情库+设置 六页。"""
import os
import threading
import time

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QStackedWidget, QPushButton, QLineEdit, QTextEdit, QPlainTextEdit,
    QSpinBox, QCheckBox, QMessageBox, QFileDialog, QSplitter, QGroupBox,
    QFormLayout, QScrollArea, QFrame, QComboBox,
)
from PySide6.QtGui import QFont, QColor

from bot import config


class LogBridge(QObject):
    """线程安全日志桥：BotCore 回调 → Qt 信号。"""
    log = Signal(str)
    status = Signal(bool)


def _mono_font(size=10):
    f = QFont("Microsoft YaHei UI", size)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def _card(title, inner):
    box = QGroupBox(title)
    box.setObjectName("card")
    lay = QVBoxLayout(box)
    lay.addWidget(inner)
    return box


# ================= 状态页 =================
class StatusPage(QWidget):
    def __init__(self, bot, bridge):
        super().__init__()
        self.bot = bot
        self._build()
        bridge.log.connect(self._append_log)
        bridge.status.connect(self._set_conn)

    def _build(self):
        lay = QVBoxLayout(self)
        info = QFormLayout()
        self.lbl_qq = QLabel("未知")
        self.lbl_napcat = QLabel("未连接")
        self.lbl_persona = QLabel(self.bot.cfg.get("persona", {}).get("default", "dsh"))
        self.lbl_model = QLabel(self.bot.llm.model)
        info.addRow("机器人 QQ", self.lbl_qq)
        info.addRow("NapCat 状态", self.lbl_napcat)
        info.addRow("当前人格", self.lbl_persona)
        info.addRow("模型", self.lbl_model)
        top = QHBoxLayout()
        self.btn_refresh = QPushButton("刷新状态")
        self.btn_refresh.clicked.connect(self.refresh)
        top.addLayout(info)
        top.addWidget(self.btn_refresh, 0, Qt.AlignTop)
        lay.addLayout(top)
        lay.addWidget(QLabel("运行日志"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setFont(_mono_font())
        lay.addWidget(self.log_view, 1)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._periodic)
        self.timer.start(5000)

    def refresh(self):
        try:
            if self.bot.client and self.bot.client.connected:
                info = self.bot.client.get_login_info()
                if info:
                    self.lbl_qq.setText(str(info.get("user_id", "未知")))
                    self.bot.self_id = str(info.get("user_id", ""))
        except Exception:
            pass
        self.lbl_napcat.setText("已连接" if (self.bot.client and self.bot.client.connected) else "未连接")
        self.lbl_persona.setText(self.bot.cfg.get("persona", {}).get("default", "dsh"))
        self.lbl_model.setText(self.bot.llm.model)

    def _periodic(self):
        if self.bot.client and self.bot.client.connected and not self.bot.self_id:
            self.refresh()

    def _set_conn(self, ok):
        self.lbl_napcat.setText("已连接" if ok else "未连接")

    def _append_log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{ts}] {msg}")


# ================= 聊天页 =================
class ChatPage(QWidget):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("测试对话（直接调用当前人格与模型，不影响 QQ 消息）"))
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setFont(_mono_font())
        lay.addWidget(self.out, 1)
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("输入一句话，回车发送")
        self.inp.returnPressed.connect(self.send)
        self.btn = QPushButton("发送")
        self.btn.clicked.connect(self.send)
        row.addWidget(self.inp, 1)
        row.addWidget(self.btn)
        lay.addLayout(row)

    def send(self):
        text = self.inp.text().strip()
        if not text:
            return
        self.inp.clear()
        self.out.appendPlainText(f"你: {text}")
        self.out.appendPlainText("（思考中...）")

        def work():
            try:
                reply = self.bot.llm.chat(self.bot._build_system(), [], max_tokens=200)
            except Exception as e:
                reply = f"❌ {e}"
            self.out.appendPlainText(f"DSH: {reply}")

        threading.Thread(target=work, daemon=True).start()


# ================= 人格页 =================
class PersonaPage(QWidget):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._build()
        self._reload_list()

    def _build(self):
        split = QSplitter(Qt.Horizontal)
        self.persona_list = QListWidget()
        self.persona_list.currentItemChanged.connect(self._on_select)
        split.addWidget(self.persona_list)
        form = QWidget()
        fl = QVBoxLayout(form)
        self.ed_name = QLineEdit()
        self.ed_display = QLineEdit()
        self.ed_prompt = QPlainTextEdit()
        self.ed_prompt.setPlaceholderText("system_prompt：人格核心设定，像真人一样聊天...")
        self.ed_rules = QPlainTextEdit()
        self.ed_rules.setPlaceholderText("安全铁律，每行一条（自动拼进 system prompt）")
        self.ed_maxchars = QSpinBox()
        self.ed_maxchars.setRange(50, 2000)
        self.ed_maxchars.setValue(200)
        fl.addWidget(QLabel("人格名（文件名）"))
        fl.addWidget(self.ed_name)
        fl.addWidget(QLabel("显示名"))
        fl.addWidget(self.ed_display)
        fl.addWidget(QLabel("人格设定 system_prompt"))
        fl.addWidget(self.ed_prompt, 3)
        fl.addWidget(QLabel("安全铁律（每行一条）"))
        fl.addWidget(self.ed_rules, 2)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("回复上限字符"))
        r2.addWidget(self.ed_maxchars)
        r2.addStretch(1)
        fl.addLayout(r2)
        btns = QHBoxLayout()
        b_save = QPushButton("保存")
        b_new = QPushButton("新建")
        b_del = QPushButton("删除")
        b_set = QPushButton("设为默认")
        b_save.clicked.connect(self._save)
        b_new.clicked.connect(self._new)
        b_del.clicked.connect(self._delete)
        b_set.clicked.connect(self._set_default)
        btns.addWidget(b_save)
        btns.addWidget(b_new)
        btns.addWidget(b_del)
        btns.addWidget(b_set)
        btns.addStretch(1)
        fl.addLayout(btns)
        split.addWidget(form)
        split.setSizes([180, 520])
        lay = QVBoxLayout(self)
        lay.addWidget(split)

    def _reload_list(self):
        self.bot.personas = config.load_personas()
        cur = self.ed_name.text()
        self.persona_list.clear()
        for name in self.bot.personas:
            self.persona_list.addItem(name)
        default = self.bot.cfg.get("persona", {}).get("default", "dsh")
        for i in range(self.persona_list.count()):
            it = self.persona_list.item(i)
            if it.text() == (cur or default):
                self.persona_list.setCurrentItem(it)
                self._on_select(it, None)
                break

    def _on_select(self, cur, _prev):
        if not cur:
            return
        p = self.bot.personas.get(cur.text(), {})
        self.ed_name.setText(p.get("name", cur.text()))
        self.ed_display.setText(p.get("display_name", ""))
        self.ed_prompt.setPlainText(p.get("system_prompt", ""))
        rules = p.get("safety_rules", [])
        self.ed_rules.setPlainText("\n".join(rules) if rules else "")
        self.ed_maxchars.setValue(p.get("style", {}).get("max_reply_chars", 200))

    def _save(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "人格名不能为空")
            return
        p = {
            "name": name,
            "display_name": self.ed_display.text().strip() or name,
            "system_prompt": self.ed_prompt.toPlainText().strip(),
            "safety_rules": [x.strip() for x in self.ed_rules.toPlainText().splitlines() if x.strip()],
            "style": {"max_reply_chars": self.ed_maxchars.value()},
        }
        config.save_persona(p)
        self._reload_list()
        QMessageBox.information(self, "已保存", f"人格「{name}」已保存")

    def _new(self):
        self.ed_name.clear()
        self.ed_display.clear()
        self.ed_prompt.clear()
        self.ed_rules.clear()
        self.ed_maxchars.setValue(200)
        self.ed_name.setFocus()

    def _delete(self):
        name = self.ed_name.text().strip()
        if not name:
            return
        path = os.path.join(config.PERSONA_DIR, name + ".yaml")
        if os.path.exists(path) and QMessageBox.question(self, "确认", f"删除人格「{name}」？") == QMessageBox.Yes:
            os.remove(path)
            self._reload_list()

    def _set_default(self):
        name = self.ed_name.text().strip()
        if name in self.bot.personas:
            self.bot.cfg.setdefault("persona", {})["default"] = name
            config.save_config(self.bot.cfg)
            QMessageBox.information(self, "完成", f"默认人格已设为「{name}」")


# ================= 白名单页 =================
class WhitelistPage(QWidget):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._build()
        self._reload()

    def _build(self):
        lay = QVBoxLayout(self)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("白名单模式（仅允许列表内可聊）", "whitelist")
        self.mode_combo.addItem("黑名单模式（仅禁止列表内）", "blacklist")
        lay.addWidget(self.mode_combo)
        split = QSplitter(Qt.Horizontal)
        self.lst_users = QListWidget()
        self.lst_groups = QListWidget()
        self.lst_admin = QListWidget()
        split.addWidget(self._listbox("可聊用户", self.lst_users, "users"))
        split.addWidget(self._listbox("可聊群", self.lst_groups, "groups"))
        split.addWidget(self._listbox("管理员", self.lst_admin, "admin_qq"))
        lay.addWidget(split, 1)
        self.ed_reply = QLineEdit()
        self.ed_reply.setPlaceholderText("群触发规则：at / prefix / at_or_prefix / all")
        lay.addWidget(self.ed_reply)
        b = QPushButton("保存白名单")
        b.clicked.connect(self._save)
        lay.addWidget(b)

    def _listbox(self, title, lst, field):
        box = QGroupBox(title)
        v = QVBoxLayout(box)
        v.addWidget(lst, 1)
        row = QHBoxLayout()
        ed = QLineEdit()
        ed.setPlaceholderText("QQ/群号")
        btn = QPushButton("添加")
        btn.clicked.connect(lambda: self._add(field, ed))
        row.addWidget(ed, 1)
        row.addWidget(btn)
        v.addLayout(row)
        return box

    def _reload(self):
        self.wl = config.load_whitelist()
        mode = self.wl.get("mode", "whitelist")
        idx = self.mode_combo.findData(mode)
        self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.ed_reply.setText(self.wl.get("reply_rule", "at_or_prefix"))
        for lst, field in ((self.lst_users, "users"), (self.lst_groups, "groups"),
                           (self.lst_admin, "admin_qq")):
            lst.clear()
            for x in self.wl.get(field, []):
                lst.addItem(str(x))

    def _add(self, field, ed):
        v = ed.text().strip()
        if not v:
            return
        self.wl.setdefault(field, [])
        if v not in self.wl[field]:
            self.wl[field].append(v)
            config.save_whitelist(self.wl)
        self._reload()

    def _save(self):
        self.wl["mode"] = self.mode_combo.currentData()
        self.wl["reply_rule"] = self.ed_reply.text().strip() or "at_or_prefix"
        for lst, field in ((self.lst_users, "users"), (self.lst_groups, "groups"),
                           (self.lst_admin, "admin_qq")):
            items = [lst.item(i).text() for i in range(lst.count())]
            self.wl[field] = items
        config.save_whitelist(self.wl)
        self.bot.wl = config.load_whitelist()
        QMessageBox.information(self, "完成", "白名单已保存并生效")


# ================= 主动聊天页 =================
class ProactivePage(QWidget):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self._build()
        self._load()

    def _build(self):
        lay = QVBoxLayout(self)
        self.chk_enable = QCheckBox("启用主动聊天")
        lay.addWidget(self.chk_enable)
        f = QFormLayout()
        self.sp_interval = QSpinBox()
        self.sp_interval.setRange(5, 1440)
        self.sp_interval.setSuffix(" 分钟")
        f.addRow("间隔", self.sp_interval)
        self.ed_targets = QLineEdit()
        self.ed_targets.setPlaceholderText("逗号分隔的 QQ，留空=用白名单用户")
        f.addRow("私聊对象", self.ed_targets)
        self.ed_quiet = QLineEdit()
        self.ed_quiet.setPlaceholderText("如 23:00-08:00，多段用逗号")
        f.addRow("安静时段", self.ed_quiet)
        lay.addLayout(f)
        b = QPushButton("保存主动聊天设置")
        b.clicked.connect(self._save)
        lay.addWidget(b)
        lay.addStretch(1)

    def _load(self):
        p = self.bot.cfg.get("proactive", {})
        self.chk_enable.setChecked(p.get("enabled", True))
        self.sp_interval.setValue(p.get("interval_minutes", 40))
        self.ed_targets.setText(",".join(str(x) for x in p.get("private_targets", [])))
        self.ed_quiet.setText(",".join(p.get("quiet_hours", ["23:00-08:00"])))

    def _save(self):
        p = {
            "enabled": self.chk_enable.isChecked(),
            "interval_minutes": self.sp_interval.value(),
            "private_targets": [x.strip() for x in self.ed_targets.text().split(",") if x.strip()],
            "group_targets": self.bot.cfg.get("proactive", {}).get("group_targets", []),
            "quiet_hours": [x.strip() for x in self.ed_quiet.text().split(",") if x.strip()],
            "max_chars": 100,
        }
        self.bot.cfg["proactive"] = p
        config.save_config(self.bot.cfg)
        QMessageBox.information(self, "完成", "主动聊天设置已保存（下次重启生效）")


# ================= 表情库 + 设置页 =================
class StickerSettingsPage(QWidget):
    def __init__(self, bot, bridge):
        super().__init__()
        self.bot = bot
        self.bridge = bridge
        self._build()
        self._reload_stickers()
        self._load_settings()

    def _build(self):
        lay = QVBoxLayout(self)
        split = QSplitter(Qt.Horizontal)
        left = QGroupBox("表情包库（斗图图库）")
        lv = QVBoxLayout(left)
        self.sticker_list = QListWidget()
        lv.addWidget(self.sticker_list, 1)
        row = QHBoxLayout()
        b_open = QPushButton("打开目录")
        b_refresh = QPushButton("刷新")
        b_add = QPushButton("添加图片")
        b_open.clicked.connect(self._open_dir)
        b_refresh.clicked.connect(self._reload_stickers)
        b_add.clicked.connect(self._add_stickers)
        row.addWidget(b_open)
        row.addWidget(b_refresh)
        row.addWidget(b_add)
        lv.addLayout(row)
        right = QGroupBox("模型与安全设置")
        rv = QVBoxLayout(right)
        f = QFormLayout()
        self.ed_key = QLineEdit()
        self.ed_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_key.setPlaceholderText("DeepSeek API Key（sk-...）")
        f.addRow("API Key", self.ed_key)
        self.ed_model = QLineEdit()
        f.addRow("模型", self.ed_model)
        self.sp_daily_tokens = QSpinBox()
        self.sp_daily_tokens.setRange(1000, 5000000)
        self.sp_daily_tokens.setSuffix(" tokens")
        f.addRow("每日预算", self.sp_daily_tokens)
        self.ed_banned = QLineEdit()
        self.ed_banned.setPlaceholderText("屏蔽词，逗号分隔")
        f.addRow("屏蔽词", self.ed_banned)
        rv.addLayout(f)
        b_save = QPushButton("保存设置")
        b_save.clicked.connect(self._save_settings)
        rv.addWidget(b_save)
        rv.addStretch(1)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([400, 360])
        lay.addWidget(split)

    def _reload_stickers(self):
        self.sticker_list.clear()
        for path, fn, tags in self.bot.stickers.list_all():
            it = QListWidgetItem(f"{fn}   [{tags}]")
            it.setToolTip(path)
            self.sticker_list.addItem(it)

    def _open_dir(self):
        os.startfile(config.STICKER_DIR)  # noqa

    def _add_stickers(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择表情包图片", "",
            "图片 (*.jpg *.jpeg *.png *.gif *.webp *.bmp)")
        for src in files:
            dst = os.path.join(config.STICKER_DIR, os.path.basename(src))
            try:
                import shutil
                shutil.copy2(src, dst)
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))
        self._reload_stickers()

    def _load_settings(self):
        self.ed_key.setText(self.bot.api_key)
        self.ed_model.setText(self.bot.llm.model)
        b = self.bot.cfg.get("safety", {}).get("budget", {})
        self.sp_daily_tokens.setValue(b.get("daily_max_tokens", 200000))
        banned = self.bot.cfg.get("safety", {}).get("content_filter", {}).get("banned_words", [])
        self.ed_banned.setText(",".join(banned))

    def _save_settings(self):
        key = self.ed_key.text().strip()
        if key:
            config.save_env_key(key)
            self.bot.api_key = key
            self.bot.llm.api_key = key
        model = self.ed_model.text().strip()
        if model:
            self.bot.cfg.setdefault("llm", {})["model"] = model
            self.bot.llm.model = model
        self.bot.cfg.setdefault("safety", {}).setdefault("budget", {})["daily_max_tokens"] = \
            self.sp_daily_tokens.value()
        self.bot.cfg.setdefault("safety", {}).setdefault("content_filter", {})["banned_words"] = \
            [x.strip() for x in self.ed_banned.text().split(",") if x.strip()]
        config.save_config(self.bot.cfg)
        self.bot.cfg = config.load_config()
        QMessageBox.information(self, "完成", "设置已保存并生效")
