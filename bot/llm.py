# -*- coding: utf-8 -*-
"""DeepSeek API 调用：文本 + 视觉（识图）。模型默认 deepseek-flash（V4.1 Flash 原生多模态）。"""
import base64
import json
import time
import urllib.request

API_URL = "https://api.deepseek.com/chat/completions"


class LLMError(Exception):
    pass


class LLM:
    def __init__(self, api_key, model="deepseek-flash", timeout=60):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _post(self, payload):
        if not self.api_key:
            raise LLMError("未配置 DEEPSEEK_API_KEY")
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.api_key,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            raise LLMError(f"HTTP {e.code}: {body}")
        except Exception as e:
            raise LLMError(str(e))

    def chat(self, system, history, image_b64=None, image_mime="image/jpeg", max_tokens=512,
             temperature=0.9, json_mode=False):
        """调用聊天补全。image_b64 非空时附加视觉图片（识图）。"""
        messages = [{"role": "system", "content": system}]
        for h in history:
            messages.append(h)
        if image_b64:
            data_url = f"data:{image_mime};base64,{image_b64}"
            last = messages[-1]
            if last["role"] == "user":
                messages[-1] = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": last["content"]},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            else:
                messages.append({"role": "user", "content": [
                    {"type": "text", "text": "看看这张图。"},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]})
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self._post(payload)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise LLMError("响应解析失败: " + str(e))

    def count_tokens(self, text):
        """粗略估算 token（中英混合）：中文约 1 字≈1 token，英文约 4 字符≈1 token。"""
        cn = sum(1 for c in text if ord(c) > 127)
        en = len(text) - cn
        return cn + en // 4 + 1


def image_file_to_b64(path, max_bytes=8 * 1024 * 1024):
    """读取图片文件转 base64，超过 8MB 拒绝（API 单图限制 32MiB，8MB 保险）。"""
    import os
    size = os.path.getsize(path)
    if size > max_bytes:
        raise LLMError(f"图片过大({size // 1024}KB)，超过 8MB 限制")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def guess_mime(path):
    ext = os.path.splitext(path)[1].lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
    }.get(ext, "image/jpeg")
