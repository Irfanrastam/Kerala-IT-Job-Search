from __future__ import annotations

import requests

API_ROOT = "https://api.telegram.org/bot{token}/{method}"


class TelegramError(RuntimeError):
    pass


def _api(token: str, method: str, payload: dict | None = None) -> dict:
    response = requests.post(
        API_ROOT.format(token=token, method=method),
        json=payload or {},
        timeout=25,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise TelegramError(data.get("description", "Telegram API request failed"))
    return data["result"]


def send_text(token: str, chat_id: str, message: str) -> None:
    # Telegram text messages are limited to 4096 characters. Keep a safety margin.
    chunks: list[str] = []
    remaining = message.strip()
    while len(remaining) > 3900:
        split_at = remaining.rfind("\n", 0, 3900)
        if split_at < 500:
            split_at = 3900
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    for chunk in chunks:
        _api(token, "sendMessage", {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True})


def find_chat_ids(token: str) -> list[tuple[str, str]]:
    """Return private chats that have sent /start to this bot."""
    result = _api(token, "getUpdates", {"limit": 100, "timeout": 0})
    chats: dict[str, str] = {}
    for update in result:
        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        text = (message.get("text") or "").strip()
        if chat.get("type") == "private" and text.startswith("/start"):
            chat_id = str(chat.get("id"))
            name = " ".join(part for part in (chat.get("first_name"), chat.get("last_name")) if part)
            chats[chat_id] = name or "Telegram user"
    return sorted(chats.items())
