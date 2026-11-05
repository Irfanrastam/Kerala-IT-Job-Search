"""Print the private Telegram chat ID after the user has sent /start."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.telegram_bot import find_chat_ids  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Set TELEGRAM_BOT_TOKEN in .env first.")
        return 1
    chats = find_chat_ids(token)
    if not chats:
        print("No /start message found. Open your bot in Telegram, press Start, then run this script again.")
        return 1
    print("Private chats that sent /start:")
    for chat_id, name in chats:
        print(f"Name: {name} | Chat ID: {chat_id}")
    print("Copy your chat ID into TELEGRAM_CHAT_ID in .env and GitHub Actions secrets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
