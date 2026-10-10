# -*- coding: utf-8 -*-
"""OneBot 11 正向 WebSocket 客户端：连接 NapCat，收发消息，支持文本与图片。"""
import json
import threading
import time
import urllib.request

try:
    import websocket  # websocket-client
    HAS_WS = True
except Exception:
    HAS_WS = False


class OneBotClient:
    def __init__(self, ws_url, access_token="", on_event=None, on_state=None,
                 napcat_http="http://127.0.0.1:3000"):
        self.ws_url = ws_url
        self.access_token = access_token
        self.on_event = on_event          # callable(dict event)
        self.on_state = on_state          # callable(bool connected)
        self.napcat_http = napcat_http
        self._ws = None
        self._stop = False
        self._thread = None
        self.connected = False
        self.seq = 1000

    # ---------- 连接 ----------
    def start(self):
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass

    def _run(self):
        if not HAS_WS:
            self._notify_state(False)
            return
        while not self._stop:
            try:
                headers = None
                if self.access_token:
                    headers = {"Authorization": "Bearer " + self.access_token}
                # timeout 用 40s：NapCat 心跳间隔 30s，留足余量；
                # 超时不视为断开，改为发 ping 保活，避免 15s 一次的假断开循环
                self._ws = websocket.create_connection(
                    self.ws_url, timeout=40, header=headers or {})
                self.connected = True
                self._notify_state(True)
                while not self._stop:
                    try:
                        raw = self._ws.recv()
                    except websocket.WebSocketTimeoutException:
                        # 服务端无数据：发 ping 保活，不重连
                        try:
                            self._ws.ping("ping")
                        except Exception:
                            raise
                        continue
                    if not raw:
                        continue
                    try:
                        evt = json.loads(raw)
                    except Exception:
                        continue
                    if self.on_event:
                        try:
                            self.on_event(evt)
                        except Exception:
                            pass
            except Exception as e:
                self.connected = False
                self._notify_state(False)
                if not self._stop:
                    time.sleep(3)
            finally:
                try:
                    if self._ws:
                        self._ws.close()
                except Exception:
                    pass
                self._ws = None

    def _notify_state(self, ok):
        if self.on_state:
            try:
                self.on_state(ok)
            except Exception:
                pass

    # ---------- 调用 NapCat API（统一走 HTTP，避免 WS+HTTP 双发导致消息重复） ----------
    def _call(self, action, params=None):
        params = params or {}
        # WS 仅用于接收事件；所有发送动作一律走 HTTP 单通道，杜绝重复发送
        try:
            url = self.napcat_http + "/" + action
            data = json.dumps(params).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            return None

    # ---------- 业务动作 ----------
    def send_private_msg(self, user_id, message):
        return self._call("send_private_msg", {"user_id": int(user_id), "message": message})

    def send_group_msg(self, group_id, message):
        return self._call("send_group_msg", {"group_id": int(group_id), "message": message})

    def send_msg(self, msg_type, target_id, message):
        if msg_type == "private":
            return self.send_private_msg(target_id, message)
        return self.send_group_msg(target_id, message)

    def get_login_info(self):
        r = self._call("get_login_info", {})
        return (r or {}).get("data") or {}


def image_to_cq(path_or_url, is_local=True):
    """构造 CQ 图片段：本地文件用 file://，否则原样 url。"""
    if is_local:
        return f"[CQ:image,file=file:///{path_or_url.replace('/', '\\\\').replace('\\', '/')}]"
    return f"[CQ:image,file={path_or_url}]"
