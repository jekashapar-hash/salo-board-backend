import contextlib
import os

import requests

from salocore.models import UserProfile
from salocore.repositories.notification.dto import MessageDTO


class TelegramNotificationRepositoryImpl:
    def send(self, message: MessageDTO, to: UserProfile) -> None:
        if not to.telegram:
            return

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        telegram_text = f"<b>{message.title}</b>\n\n{message.text}"

        payload = {"chat_id": to.telegram, "text": telegram_text, "parse_mode": "HTML"}

        with contextlib.suppress(Exception):
            requests.post(url, json=payload, timeout=5)
