"""
Webhook Relay - Receive and forward webhooks to Telegram
"""
import os
import json
import hashlib
import hmac
import secrets
from datetime import datetime, date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx

from .formatters import auto_format, format_generic

load_dotenv()

# Config
DATA_DIR = Path(os.getenv("WEBHOOK_DATA_DIR", "/root/source/side-projects/webhook-relay/data"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# In-memory channel registry (load from file on startup)
channels: dict[str, dict] = {}


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "logs").mkdir(exist_ok=True)


def load_channels():
    """Load channel config from file."""
    global channels
    config_file = DATA_DIR / "channels.json"
    
    if config_file.exists():
        channels = json.loads(config_file.read_text())
    else:
        # Create default channel
        channels = {
            "default": {
                "name": "Default",
                "telegram_chat_id": TELEGRAM_CHAT_ID,
                "secret": None,  # No signature verification
                "created_at": datetime.utcnow().isoformat(),
            }
        }
        save_channels()


def save_channels():
    """Save channel config to file."""
    ensure_dirs()
    config_file = DATA_DIR / "channels.json"
    config_file.write_text(json.dumps(channels, indent=2))


def log_webhook(channel_id: str, payload: dict, headers: dict, forwarded: bool):
    """Log webhook to daily file."""
    ensure_dirs()
    log_file = DATA_DIR / "logs" / f"{date.today().isoformat()}.jsonl"
    
    record = {
        "channel": channel_id,
        "received_at": datetime.utcnow().isoformat(),
        "forwarded": forwarded,
        "headers": {k: v for k, v in headers.items() if k.lower().startswith(("x-", "content-"))},
        "payload_preview": json.dumps(payload)[:500],
    }
    
    with open(log_file, "a") as f:
        f.write(json.dumps(record) + "\n")


async def send_telegram(chat_id: str, message: str) -> bool:
    """Send message to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print(f"⚠️ No bot token, would send to {chat_id}: {message[:100]}...")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            })
            return resp.status_code == 200
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False


def verify_signature(payload: bytes, signature: str, secret: str, algorithm: str = "sha256") -> bool:
    """Verify webhook signature (GitHub style: sha256=xxx)."""
    if "=" in signature:
        algo, sig = signature.split("=", 1)
    else:
        sig = signature
    
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


# FastAPI app
app = FastAPI(
    title="Webhook Relay",
    description="Receive webhooks, forward to Telegram",
    version="0.1.0",
)


@app.on_event("startup")
async def startup():
    ensure_dirs()
    load_channels()
    print(f"🚀 Webhook Relay started with {len(channels)} channels")


@app.get("/")
async def root():
    return {
        "name": "Webhook Relay",
        "channels": len(channels),
        "usage": {
            "receive": "POST /hook/{channel_id}",
            "channels": "GET /channels",
            "create": "POST /channels",
            "logs": "GET /logs",
        }
    }


@app.post("/hook/{channel_id}")
async def receive_webhook(
    channel_id: str,
    request: Request,
    x_hub_signature_256: str | None = Header(None),
    x_webhook_signature: str | None = Header(None),
):
    """Receive a webhook and forward to Telegram."""
    
    # Get channel config
    channel = channels.get(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    
    # Read body
    body = await request.body()
    
    # Verify signature if channel has a secret
    if channel.get("secret"):
        signature = x_hub_signature_256 or x_webhook_signature
        if not signature:
            raise HTTPException(status_code=401, detail="Missing signature")
        if not verify_signature(body, signature, channel["secret"]):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {"raw": body.decode("utf-8", errors="replace")[:1000]}
    
    # Get headers as dict
    headers = dict(request.headers)
    
    # Format message
    message = auto_format(payload, headers)
    
    # Add channel tag
    message = f"[{channel.get('name', channel_id)}]\n{message}"
    
    # Send to Telegram
    chat_id = channel.get("telegram_chat_id") or TELEGRAM_CHAT_ID
    if chat_id:
        forwarded = await send_telegram(chat_id, message)
    else:
        forwarded = False
        print(f"⚠️ No chat_id for channel {channel_id}")
    
    # Log
    log_webhook(channel_id, payload, headers, forwarded)
    
    return {"ok": True, "forwarded": forwarded}


# Also accept GET for simple ping/health checks
@app.get("/hook/{channel_id}")
async def webhook_ping(channel_id: str):
    if channel_id not in channels:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    return {"ok": True, "channel": channel_id, "message": "Use POST to send webhooks"}


class ChannelCreate(BaseModel):
    name: str
    telegram_chat_id: str | None = None
    secret: str | None = None  # If provided, webhooks must be signed


@app.get("/channels")
async def list_channels():
    """List all webhook channels."""
    return {
        "channels": [
            {
                "id": cid,
                "name": c.get("name"),
                "url": f"/hook/{cid}",
                "has_secret": bool(c.get("secret")),
                "created_at": c.get("created_at"),
            }
            for cid, c in channels.items()
        ]
    }


@app.post("/channels")
async def create_channel(data: ChannelCreate):
    """Create a new webhook channel."""
    # Generate unique ID
    channel_id = secrets.token_urlsafe(8)
    
    channels[channel_id] = {
        "name": data.name,
        "telegram_chat_id": data.telegram_chat_id,
        "secret": data.secret,
        "created_at": datetime.utcnow().isoformat(),
    }
    save_channels()
    
    return {
        "id": channel_id,
        "url": f"/hook/{channel_id}",
        "name": data.name,
    }


@app.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str):
    """Delete a webhook channel."""
    if channel_id not in channels:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    del channels[channel_id]
    save_channels()
    
    return {"ok": True}


@app.get("/logs")
async def get_logs(limit: int = 50):
    """Get recent webhook logs."""
    logs = []
    log_dir = DATA_DIR / "logs"
    
    if not log_dir.exists():
        return {"logs": []}
    
    # Read from most recent files
    for log_file in sorted(log_dir.glob("*.jsonl"), reverse=True):
        with open(log_file) as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
                    if len(logs) >= limit:
                        break
        if len(logs) >= limit:
            break
    
    return {"logs": logs[:limit]}


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)
