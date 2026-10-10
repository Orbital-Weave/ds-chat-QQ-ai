# ds-chat-QQ-ai

基于 DeepSeek Flash 的 QQ 聊天机器人桌面客户端。用真实 QQ 号登录，支持自定义人格、白名单、识图斗图、主动聊天，双击即用，最小化到系统托盘后台运行。

## 功能特性

- **真实 QQ 号登录**：通过 NapCat 协议端扫码登录，不是群管机器人
- **自定义人格**：在桌面 UI 里写系统提示词，打造专属聊天角色
- **白名单安全**：只回应你允许的 QQ 号/群，不跟陌生人说话
- **识图与斗图**：能看你发的图片说话，也能发表情包回击
- **主动聊天**：定时自动找白名单用户发起对话
- **桌面托盘运行**：关闭窗口不退出，最小化到托盘后台跑
- **开机自启**：开机自动启动，静默托盘运行
- **双击即用**：打包成 exe，不需要装 Python 环境

## 技术架构

```
QQ 消息 ←→ NapCat (OneBot 协议) ←→ 本程序 (Python) ←→ DeepSeek API
                                         ↓
                                    PySide6 桌面 UI
```

- **协议端**：[NapCat](https://github.com/NapNeko/NapCatQQ)（QQ 协议实现）
- **AI 内核**：DeepSeek Flash API
- **桌面框架**：PySide6 (Qt)
- **打包**：PyInstaller

## 下载与安装

### 方式一：下载打包好的 exe（推荐）

去 [Releases 页面](https://github.com/Orbital-Weave/ds-chat-QQ-ai/releases) 下载最新版压缩包，解压后双击 `QQBot.exe` 即可。

### 方式二：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/Orbital-Weave/ds-chat-QQ-ai.git
cd ds-chat-QQ-ai

# 2. 安装依赖
pip install -r requirements.txt

# 3. 复制配置模板
copy .env.example .env

# 4. 编辑 .env，填入你的 DeepSeek API Key
#    DEEPSEEK_API_KEY=sk-xxxxxxxx

# 5. 运行
python main.py
```

## 首次配置

### 1. 获取 DeepSeek API Key

1. 打开 https://platform.deepseek.com/
2. 注册并创建 API Key
3. 复制 `sk-` 开头的 Key，粘贴到程序「表情库+设置」页

### 2. 部署 NapCat 协议端

本程序通过 NapCat 连接 QQ。下载 [NapCat Node 版](https://github.com/NapNeko/NapCatQQ) 并启动，扫码登录你要当机器人的 QQ 号。

NapCat 默认配置：
- HTTP 端口：`3000`
- WebSocket 端口：`3001`
- WebUI：`http://127.0.0.1:6099`

程序启动时会自动检测并拉起 NapCat。

### 3. 设置白名单

在程序「白名单」页填入你自己的 QQ 号（机器人只回应白名单里的人）。

### 4. 选择/创建人格

在「人格设计」页选择已有模板，或自己写一个系统提示词。人格文件放在 `config/personas/` 目录。

## 使用方法

| 操作 | 效果 |
|------|------|
| 双击 `QQBot.exe` | 打开控制台窗口 |
| 点窗口右上角 X | 最小化到托盘（不退出） |
| 双击托盘图标 | 打开/隐藏控制台 |
| 右键托盘图标 | 「打开控制台」/「退出」 |
| 开机 | 自动启动并静默托盘运行 |

## 目录结构

```
ds-chat-QQ-ai/
├── main.py              # 入口
├── bot/
│   ├── config.py       # 配置加载
│   ├── core.py         # 机器人核心逻辑
│   ├── llm.py          # DeepSeek API 调用
│   ├── onebot.py       # OneBot 协议客户端
│   ├── napcat.py       # NapCat 自动拉起
│   └── stickers.py      # 表情库/斗图
├── gui/
│   ├── main_window.py   # 主窗口+托盘
│   └── pages.py         # 6 个设置页面
├── config/
│   └── personas/        # 人格配置（example.yaml 为模板）
├── .env.example         # API Key 配置模板
├── requirements.txt     # Python 依赖
└── build.ps1            # Windows 打包脚本
```

## 安全说明

- API Key 存在本地 `.env` 文件，**不会上传到仓库**
- 白名单存在本地 `config/whitelist.yaml`，机器人只回应你允许的人
- 不修改系统 hosts、代理、网络设置
- 单实例锁防止重复打开导致消息重复回复

## 常见问题

**Q：重启电脑后需要重新扫码登录吗？**
A：NapCat 登录态一般能维持几天。如果掉线，打开 `http://127.0.0.1:6099` 重新扫码即可。

**Q：机器人不回消息？**
A：检查：① NapCat 是否在线 ② API Key 是否有效 ③ 你的 QQ 号是否在白名单里。

**Q：如何取消开机自启？**
A：任务管理器 → 启动 → 禁用「ds聊天智能」。

## License

MIT
