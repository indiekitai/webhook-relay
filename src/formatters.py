"""
Smart formatters for common webhook sources
"""
import json
from typing import Any


def format_github(payload: dict, event: str | None) -> str:
    """Format GitHub webhook payload."""
    repo = payload.get("repository", {}).get("full_name", "unknown")
    sender = payload.get("sender", {}).get("login", "unknown")
    
    if event == "push":
        branch = payload.get("ref", "").replace("refs/heads/", "")
        commits = payload.get("commits", [])
        lines = [
            f"🔨 <b>Push to {repo}</b>",
            f"Branch: <code>{branch}</code>",
            f"By: {sender}",
            f"Commits: {len(commits)}",
        ]
        for c in commits[:3]:
            msg = c.get("message", "").split("\n")[0][:50]
            lines.append(f"  • {msg}")
        if len(commits) > 3:
            lines.append(f"  ... and {len(commits) - 3} more")
        return "\n".join(lines)
    
    elif event == "pull_request":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        title = pr.get("title", "")[:50]
        number = pr.get("number", "?")
        return f"🔀 <b>PR #{number} {action}</b>\n{repo}\n{title}\nBy: {sender}"
    
    elif event == "issues":
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        title = issue.get("title", "")[:50]
        number = issue.get("number", "?")
        return f"📋 <b>Issue #{number} {action}</b>\n{repo}\n{title}\nBy: {sender}"
    
    elif event == "star":
        action = payload.get("action", "created")
        stars = payload.get("repository", {}).get("stargazers_count", "?")
        return f"⭐ <b>{repo}</b>\n{sender} {'starred' if action == 'created' else 'unstarred'}\nTotal: {stars}"
    
    elif event == "release":
        action = payload.get("action", "")
        release = payload.get("release", {})
        tag = release.get("tag_name", "?")
        return f"🚀 <b>Release {action}: {tag}</b>\n{repo}\nBy: {sender}"
    
    else:
        return f"📦 <b>GitHub: {event or 'event'}</b>\n{repo}\nBy: {sender}"


def format_stripe(payload: dict) -> str:
    """Format Stripe webhook payload."""
    event_type = payload.get("type", "unknown")
    data = payload.get("data", {}).get("object", {})
    
    if "payment_intent" in event_type:
        amount = data.get("amount", 0) / 100
        currency = data.get("currency", "usd").upper()
        status = data.get("status", "unknown")
        return f"💳 <b>Stripe: {event_type}</b>\nAmount: {amount} {currency}\nStatus: {status}"
    
    elif "customer" in event_type:
        email = data.get("email", "unknown")
        return f"👤 <b>Stripe: {event_type}</b>\nCustomer: {email}"
    
    elif "subscription" in event_type:
        status = data.get("status", "unknown")
        return f"🔄 <b>Stripe: {event_type}</b>\nStatus: {status}"
    
    else:
        return f"💳 <b>Stripe: {event_type}</b>"


def format_generic(payload: dict, source: str = "webhook") -> str:
    """Format any webhook payload generically."""
    # Try to extract useful info
    lines = [f"📨 <b>{source}</b>"]
    
    # Common fields to look for
    interesting_keys = ["action", "event", "type", "status", "message", "name", "email", "url"]
    
    for key in interesting_keys:
        if key in payload:
            value = str(payload[key])[:100]
            lines.append(f"{key}: {value}")
    
    # If payload is small, include it
    if len(lines) == 1:
        preview = json.dumps(payload, ensure_ascii=False)[:200]
        lines.append(f"<code>{preview}</code>")
    
    return "\n".join(lines)


def auto_format(payload: dict, headers: dict) -> str:
    """Auto-detect source and format accordingly."""
    # GitHub
    if "X-GitHub-Event" in headers or "x-github-event" in headers:
        event = headers.get("X-GitHub-Event") or headers.get("x-github-event")
        return format_github(payload, event)
    
    # Stripe
    if payload.get("type", "").startswith(("payment_intent", "customer", "subscription", "invoice")):
        return format_stripe(payload)
    
    # Try to guess source from payload
    if "repository" in payload and "sender" in payload:
        return format_github(payload, payload.get("action"))
    
    # Generic
    return format_generic(payload)
