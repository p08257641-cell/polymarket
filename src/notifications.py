import logging
import requests
from config.settings import settings

logger = logging.getLogger("polymarket_bot")

class NotificationService:
    def __init__(self):
        self.telegram_token = settings.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = settings.TELEGRAM_CHAT_ID
        self.discord_webhook = settings.DISCORD_WEBHOOK_URL

    def send(self, message: str, level: str = "INFO"):
        """Send notification across configured channels."""
        prefix = {
            "INFO": "ℹ️ [INFO]",
            "TRADE": "🚀 [TRADE EXECUTED]",
            "ALERT": "⚠️ [ALERT]",
            "ERROR": "🚨 [ERROR]"
        }.get(level.upper(), f"[{level.upper()}]")

        formatted_message = f"{prefix}\n{message}"

        # Send to Telegram
        if self.telegram_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": formatted_message,
                    "parse_mode": "HTML"
                }
                requests.post(url, json=payload, timeout=5)
            except Exception as e:
                logger.debug(f"Failed to send Telegram message: {e}")

        # Send to Discord
        if self.discord_webhook:
            try:
                payload = {"content": formatted_message}
                requests.post(self.discord_webhook, json=payload, timeout=5)
            except Exception as e:
                logger.debug(f"Failed to send Discord notification: {e}")

notifier = NotificationService()
