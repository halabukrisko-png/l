#!/usr/bin/env python3
"""
Telegram sender for WC 2026 Analysis Agent.

Usage:
  from agent.telegram_bot import send_message, send_analysis

Config via environment variables (or .env file):
  TELEGRAM_BOT_TOKEN=<your_bot_token>
  TELEGRAM_CHAT_ID=<your_chat_id>
"""

import os
import sys
import logging
from pathlib import Path

# Load .env if present
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

MAX_MESSAGE_LENGTH = 4096


def _get_token_and_chat() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set. Add it to .env or environment.")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID not set. Add it to .env or environment.")
    return token, chat_id


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a plain text message to the configured Telegram chat."""
    try:
        import requests
        token, chat_id = _get_token_and_chat()

        # Split into chunks if too long
        chunks = _split_text(text, MAX_MESSAGE_LENGTH)
        for chunk in chunks:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
            }, timeout=15)
            if not resp.ok:
                logger.error(f"Telegram error {resp.status_code}: {resp.text[:200]}")
                return False
        return True
    except Exception as e:
        logger.error(f"Telegram send_message failed: {e}")
        return False


def send_analysis(cycle: str, match: str, content: str) -> bool:
    """Format and send a full analysis output."""
    header = _cycle_header(cycle, match)
    full_text = f"{header}\n\n{content}"
    return send_message(full_text, parse_mode="HTML")


def send_notification(notification_type: str, match: str, content: str) -> bool:
    """Send a short notification (lineup, live alert, post-match)."""
    icon = {
        "lineup": "📋",
        "live": "🔴",
        "postmatch": "🏁",
        "evening": "🌙",
    }.get(notification_type, "📢")
    header = f"{icon} <b>{match}</b>"
    full_text = f"{header}\n\n{content}"
    return send_message(full_text, parse_mode="HTML")


def test_connection() -> bool:
    """Verify bot token works and can reach the chat."""
    try:
        import requests
        token, chat_id = _get_token_and_chat()
        url = f"https://api.telegram.org/bot{token}/getMe"
        resp = requests.get(url, timeout=10)
        if not resp.ok:
            print(f"❌ Bot token invalid: {resp.status_code} {resp.text[:100]}")
            return False
        bot_info = resp.json().get("result", {})
        print(f"✅ Bot connected: @{bot_info.get('username')} ({bot_info.get('first_name')})")
        print(f"   Chat ID: {chat_id}")
        return True
    except ValueError as e:
        print(f"❌ Config error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def _cycle_header(cycle: str, match: str) -> str:
    headers = {
        "morning": f"🌅 <b>⚽ WC 2026 — Morning Analysis</b>\n<i>{match}</i>",
        "prematch": f"⚡ <b>⚽ WC 2026 — Pre-Match Refresh</b>\n<i>{match}</i>",
        "lastminute": f"🔴 <b>⚽ WC 2026 — Last Minute Tip</b>\n<i>{match}</i>",
        "lineup": f"📋 <b>⚽ WC 2026 — Lineup Confirmed</b>\n<i>{match}</i>",
        "postmatch": f"🏁 <b>⚽ WC 2026 — Match Report</b>\n<i>{match}</i>",
    }
    return headers.get(cycle, f"📊 <b>WC 2026 — {cycle.upper()}</b>\n<i>{match}</i>")


def _split_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


if __name__ == "__main__":
    if "--test" in sys.argv:
        ok = test_connection()
        if ok:
            send_message("✅ <b>WC 2026 Agent</b> — Telegram connection working!\n\nAnalysis outputs will be sent here automatically.", parse_mode="HTML")
            print("✅ Test message sent.")
        sys.exit(0 if ok else 1)
    print("Usage: python3 telegram_bot.py --test")
