# -*- coding: utf-8 -*-
"""配置加载/保存：主配置、白名单、人格、表情库。全部 yaml，改动即时生效（部分需重启）。"""
import os
import sys
import threading
import yaml

# 打包(exe)后：以 exe 所在目录为基准，方便用户直接改旁边的 config/
# 源码运行时：以项目根目录为基准
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
PERSONA_DIR = os.path.join(CONFIG_DIR, "personas")
STICKER_DIR = os.path.join(BASE_DIR, "stickers")
LOG_DIR = os.path.join(BASE_DIR, "logs")
ENV_FILE = os.path.join(BASE_DIR, ".env")

for d in (CONFIG_DIR, DATA_DIR, PERSONA_DIR, STICKER_DIR, LOG_DIR):
    os.makedirs(d, exist_ok=True)

_lock = threading.Lock()


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return default or {}


def _save(path, data):
    with _lock:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp, path)


def load_config():
    cfg = _load(os.path.join(CONFIG_DIR, "config.yaml"), {})
    return cfg


def save_config(cfg):
    _save(os.path.join(CONFIG_DIR, "config.yaml"), cfg)


def load_whitelist():
    return _load(os.path.join(CONFIG_DIR, "whitelist.yaml"),
                 {"mode": "whitelist", "groups": [], "users": [], "admin_qq": [],
                  "reply_rule": "at_or_prefix", "command_prefix": "/"})


def save_whitelist(wl):
    _save(os.path.join(CONFIG_DIR, "whitelist.yaml"), wl)


def load_personas():
    personas = {}
    for fn in os.listdir(PERSONA_DIR):
        if fn.endswith(".yaml") or fn.endswith(".yml"):
            p = _load(os.path.join(PERSONA_DIR, fn))
            if p and p.get("name"):
                personas[p["name"]] = p
    return personas


def save_persona(p):
    path = os.path.join(PERSONA_DIR, p["name"] + ".yaml")
    _save(path, p)


def load_env_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key and os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DEEPSEEK_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return key


def save_env_key(key):
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    found = False
    for i, ln in enumerate(lines):
        if ln.strip().startswith("DEEPSEEK_API_KEY="):
            lines[i] = "DEEPSEEK_API_KEY=" + key + "\n"
            found = True
            break
    if not found:
        lines.append("DEEPSEEK_API_KEY=" + key + "\n")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


def load_usage():
    return _load(os.path.join(DATA_DIR, "usage.json"), {"date": "", "tokens": 0, "messages": 0})


def save_usage(u):
    with _lock:
        with open(os.path.join(DATA_DIR, "usage.json"), "w", encoding="utf-8") as f:
            import json
            json.dump(u, f, ensure_ascii=False, indent=2)


def today():
    import datetime
    return datetime.date.today().isoformat()
