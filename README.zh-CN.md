[English](README.md) | [中文](README.zh-CN.md)

# 📨 Webhook Relay

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

接收任何服务的 Webhook，转发到 Telegram。GitHub、Stripe、自定义服务都支持。

## 功能

- 🔗 多 Channel 支持，每个 Channel 独立 URL
- 🤖 自动识别 GitHub/Stripe 等常见格式
- 🔐 可选签名验证（GitHub 风格）
- 📝 Webhook 日志记录
- ⚡ 零配置快速启动

## 快速开始

```bash
cd /root/source/side-projects/webhook-relay

# 安装依赖
pip install fastapi uvicorn httpx python-dotenv

# 配置
cp .env.example .env
# 编辑 .env：添加 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID

# 运行
uvicorn src.main:app --port 8082
```

## 使用

### 1. 默认 Channel

直接发送到 `/hook/default`：

```bash
curl -X POST http://localhost:8082/hook/default \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "message": "Hello!"}'
```

### 2. 创建自定义 Channel

```bash
curl -X POST http://localhost:8082/channels \
  -H "Content-Type: application/json" \
  -d '{"name": "GitHub Repo", "secret": "my-webhook-secret"}'
```

### 3. GitHub Webhook 配置

1. 进入仓库 Settings → Webhooks
2. Payload URL：`https://your-domain.com/hook/{channel_id}`
3. Content type：`application/json`
4. Secret：与 Channel secret 相同
5. Events：选择要监控的事件

## API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/hook/{channel}` | POST | 接收 Webhook |
| `/channels` | GET | 列出 Channel |
| `/channels` | POST | 创建 Channel |
| `/channels/{id}` | DELETE | 删除 Channel |
| `/logs` | GET | 最近的 Webhook 日志 |

### 在线体验

```bash
# 发送测试 Webhook
curl -X POST https://hook.indiekit.ai/hook/test \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "message": "Hello from curl!"}'

# 查看最近的 Webhook 日志
curl https://hook.indiekit.ai/logs?limit=5
```

## 智能格式化

自动识别并美化常见 Webhook 格式：

**GitHub Push:**
```
[My Repo]
🔨 Push to user/repo
Branch: main
By: username
Commits: 3
  • Fix bug in login
  • Add new feature
  • Update docs
```

**Stripe Payment:**
```
[Payments]
💳 Stripe: payment_intent.succeeded
Amount: 99.00 USD
Status: succeeded
```

## 数据存储

```
data/
├── channels.json     # Channel 配置
└── logs/
    └── 2026-02-13.jsonl  # 每日 Webhook 日志
```

## License

MIT
