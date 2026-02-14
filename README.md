# 📨 Webhook Relay

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Receive webhooks from any service, forward to Telegram.

接收任何服务的 webhook，转发到 Telegram。GitHub、Stripe、自定义服务都支持。

## Features

- 🔗 多 channel 支持，每个 channel 独立 URL
- 🤖 自动识别 GitHub/Stripe 等常见格式
- 🔐 可选签名验证（GitHub 风格）
- 📝 Webhook 日志记录
- ⚡ 零配置快速启动

## Quick Start

```bash
cd /root/source/side-projects/webhook-relay

# Install
pip install fastapi uvicorn httpx python-dotenv

# Configure
cp .env.example .env
# Edit .env: add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# Run
uvicorn src.main:app --port 8082
```

## Usage

### 1. Default Channel

直接发送到 `/hook/default`:

```bash
curl -X POST http://localhost:8082/hook/default \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "message": "Hello!"}'
```

### 2. Create Custom Channel

```bash
# Create channel
curl -X POST http://localhost:8082/channels \
  -H "Content-Type: application/json" \
  -d '{"name": "GitHub Repo", "secret": "my-webhook-secret"}'

# Response: {"id": "abc123", "url": "/hook/abc123", ...}
```

### 3. GitHub Webhook Setup

1. Go to repo Settings → Webhooks
2. Payload URL: `https://your-domain.com/hook/{channel_id}`
3. Content type: `application/json`
4. Secret: (same as channel secret)
5. Events: Choose what to monitor

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hook/{channel}` | POST | Receive webhook |
| `/channels` | GET | List channels |
| `/channels` | POST | Create channel |
| `/channels/{id}` | DELETE | Delete channel |
| `/logs` | GET | Recent webhook logs |

### 在线体验

```bash
# 发送测试 webhook
curl -X POST https://hook.indiekit.ai/hook/test \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "message": "Hello from curl!"}'

# 查看最近的 webhook 日志
curl https://hook.indiekit.ai/logs?limit=5
```

## Smart Formatting

自动识别并美化常见 webhook 格式：

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

## Data Storage

```
data/
├── channels.json     # Channel configuration
└── logs/
    └── 2026-02-13.jsonl  # Daily webhook logs
```

## License

MIT
