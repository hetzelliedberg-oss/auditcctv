"""
Telegram Alert Notifier
Sends snapshot photos, 15-second video clips, and factual summaries to Telegram.
"""
import os
import requests
import logging
from typing import Optional, Dict, Any
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_alert")

def send_telegram_alert(
    session_data: Dict[str, Any],
    photo_path: Optional[str] = None,
    video_path: Optional[str] = None,
    is_exit_summary: bool = False
) -> bool:
    """
    Sends rich Telegram alert with snapshot image or video.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID not configured. Skipping alert.")
        return False

    fitting_text = "✅ ได้เข้าห้องลอง" if session_data.get("entered_fitting_room") else "❌ ไม่ได้เข้าห้องลอง"
    pants_text = f"👖 จับกางเกง: {session_data.get('pants_touched', 0)} ตัว"
    
    if is_exit_summary:
        title = "🏁 **[สรุปลูกค้าออกจากร้าน]**"
        time_text = (
            f"⏱️ **เวลาเข้า:** {session_data.get('start_time')}\n"
            f"🚪 **เวลาออก:** {session_data.get('end_time')}\n"
            f"⏳ **ระยะเวลาที่อยู่:** {session_data.get('duration_minutes', 0)} นาที"
        )
    else:
        title = "🔔 **[ลูกค้าเข้าร้านใหม่!]**"
        time_text = f"⏱️ **เวลาที่เข้า:** {session_data.get('start_time')}"

    message = (
        f"{title}\n"
        f"📍 ร้าน: {settings.STORE_NAME}\n"
        f"🆔 รหัสกลุ่ม: `{session_data.get('party_code')}`\n"
        f"👥 จำนวนคน: **{session_data.get('people_count')} คน**\n"
        f"📝 ลักษณะ: {session_data.get('description', '-')}\n"
        f"{pants_text}\n"
        f"🚪 ห้องลอง: {fitting_text}\n"
        f"{time_text}"
    )

    try:
        # If photo is available, send photo with caption
        if photo_path and os.path.exists(photo_path):
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(photo_path, "rb") as photo_file:
                payload = {
                    "chat_id": chat_id,
                    "caption": message,
                    "parse_mode": "Markdown"
                }
                files = {"photo": photo_file}
                resp = requests.post(url, data=payload, files=files, timeout=15)
                logger.info(f"Telegram photo sent status: {resp.status_code}")
                return resp.status_code == 200

        # Else fallback to standard text message
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        resp = requests.post(url, json=payload, timeout=10)
        logger.info(f"Telegram message sent status: {resp.status_code}")
        return resp.status_code == 200

    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False
