# -*- coding: utf-8 -*-
"""表情包库：扫描目录、标签管理、按关键词/随机选图（斗图）。"""
import os
import random
import re

from . import config

SUPPORTED = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


class StickerLib:
    def __init__(self, root=None):
        self.root = root or config.STICKER_DIR
        os.makedirs(self.root, exist_ok=True)

    def list_all(self):
        """返回 [(路径, 文件名, 标签字符串), ...]"""
        items = []
        for fn in os.listdir(self.root):
            path = os.path.join(self.root, fn)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext not in SUPPORTED:
                continue
            base = os.path.splitext(fn)[0]
            tags = re.split(r"[_\-\s]+", base)
            items.append((path, fn, " ".join(tags)))
        return items

    def random_pick(self):
        items = self.list_all()
        if not items:
            return None
        return random.choice(items)[0]

    def pick_by_keywords(self, keywords):
        """按关键词匹配标签选图；匹配不到回退随机。keywords 可为 str 或 list。"""
        items = self.list_all()
        if not items:
            return None
        if isinstance(keywords, str):
            keywords = [keywords]
        kws = [k.lower() for k in keywords if k]
        if kws:
            scored = []
            for path, fn, tags in items:
                tag_low = tags.lower()
                score = sum(1 for k in kws if k.lower() in tag_low)
                if score > 0:
                    scored.append((score, path))
            if scored:
                scored.sort(key=lambda x: -x[0])
                top = max(s[0] for s in scored)
                pool = [p for s, p in scored if s == top]
                return random.choice(pool)
        return random.choice(items)[0]
