"""
Configuration settings for Mi Home Store Analytics System
Using pure Python (no external dependencies required)
"""
import os

class Settings:
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Xiaomi Account Credentials (for Cloud P2P stream)
    XIAOMI_USER: str = os.getenv("XIAOMI_USER", "+66830737979")
    XIAOMI_PASSWORD: str = os.getenv("XIAOMI_PASSWORD", "P*awin123123")
    XIAOMI_SERVER: str = os.getenv("XIAOMI_SERVER", "sg")  # 'sg' (Singapore/Thailand), 'cn'
    XIAOMI_DEVICE_ID: str = os.getenv("XIAOMI_DEVICE_ID", "")

    # Video & Analytics Settings
    CLIP_DURATION_SEC: int = 15
    SESSION_TIMEOUT_MINUTES: int = 3
    STORAGE_DIR: str = os.path.join(os.path.dirname(__file__), "data")

    # Store Metadata
    STORE_NAME: str = "Central Khon Kaen Store"

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "clips"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "snapshots"), exist_ok=True)
