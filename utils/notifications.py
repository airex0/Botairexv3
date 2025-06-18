import httpx
import logging
from dotenv import load_dotenv  # لتحميل المتغيرات من .env
import os

# تحميل المتغيرات من .env
load_dotenv()

class Notifier:
    def __init__(self, cfg):
        # تحميل البيانات من المتغيرات البيئية في .env
        self.token = cfg.TELEGRAM_TOKEN
        self.chat_id = cfg.TELEGRAM_CHAT_ID

    async def send_telegram(self, message: str):
        """
        إرسال إشعار عبر Telegram.
        :param message: الرسالة التي سيتم إرسالها عبر Telegram.
        """
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # إرسال الطلب عبر HTTP
                await client.post(url, json=payload)
            logging.info("Telegram notification sent successfully.")
        except httpx.RequestError as e:
            logging.error(f"Telegram notification failed: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while sending the notification: {e}")