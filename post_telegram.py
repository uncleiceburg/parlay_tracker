#!/usr/bin/env python3
"""Send Telegram messages for Parlay Tracker."""
import os
import requests
from pathlib import Path

# Load bot token from ~/.hermes/.env
TOKEN = None
CHAT_ID = "6313996149"

env_file = Path.home() / ".hermes" / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if "TELEGRAM_BOT_TOKEN" in line:
                TOKEN = line.split("=")[1].strip().strip('"')
                break

if not TOKEN:
    # Try TELEGRAM_TOKEN
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("TELEGRAM_TOKEN"):
                    TOKEN = line.split("=")[1].strip().strip('"')
                    break

if not TOKEN:
    print("Warning: TELEGRAM_BOT_TOKEN not found in ~/.hermes/.env")


def send_message(text, chat_id=CHAT_ID):
    """Send a text message to Telegram."""
    if not TOKEN:
        print("No Telegram token - skipping send")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            print(f"Message sent to {chat_id}")
            return True
        else:
            print(f"Telegram error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def send_document(filepath, chat_id=CHAT_ID, caption=None):
    """Send a document to Telegram."""
    if not TOKEN:
        print("No Telegram token - skipping send")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    try:
        with open(filepath, "rb") as f:
            resp = requests.post(url, data=data, files={"document": f}, timeout=30)
        if resp.status_code == 200:
            print(f"Document sent to {chat_id}")
            return True
        else:
            print(f"Telegram error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    else:
        msg = "Parlay Tracker test message"
    send_message(msg)
