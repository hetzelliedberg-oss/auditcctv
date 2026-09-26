"""
Cloud Worker Service (24/7 Background Pipeline)
Polls online Xiaomi cameras, captures live frames/clips on activity, runs AI Vision,
and writes structured retail facts directly into SQLite & Telegram alerts.
"""
import os
import time
import json
import logging
from datetime import datetime
from config import settings
from camera_auto_stream import execute_auto_workflow_for_camera, capture_live_frame
from session_manager import session_mgr
from telegram_alert import send_telegram_alert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud_worker")

def load_online_cameras():
    dev_path = "data/all_real_devices.json"
    if os.path.exists(dev_path):
        try:
            with open(dev_path, "r", encoding="utf-8") as f:
                devs = json.load(f)
                return [d for d in devs if "camera" in d.get("model", "").lower() and d.get("isOnline")]
        except Exception:
            pass
    # Fallback to known online camera
    return [{"did": "263288748", "name": "หลังบ้าน 1"}]

def run_worker_cycle():
    online_cams = load_online_cameras()
    logger.info(f"Worker cycle started: Found {len(online_cams)} online camera(s)")
    for cam in online_cams:
        did = cam.get("did")
        name = cam.get("name")
        logger.info(f"Checking camera: {name} (DID: {did})...")
        try:
            res, err = execute_auto_workflow_for_camera(did, name)
            if res:
                logger.info(f"Fact data generated for {name}: Party {res.get('party_code')} | People {res.get('people_count')}")
                # Optional telegram alert
                send_telegram_alert(res, photo_path=res.get("snapshot_path"), is_exit_summary=False)
            elif err:
                logger.warning(f"Workflow skipped for {name}: {err}")
        except Exception as e:
            logger.error(f"Error processing camera {did}: {e}")

if __name__ == "__main__":
    logger.info("24/7 Cloud Background Worker Started...")
    POLL_INTERVAL_SEC = 120 # Poll every 2 minutes
    while True:
        try:
            run_worker_cycle()
        except Exception as e:
            logger.error(f"Worker error: {e}")
        time.sleep(POLL_INTERVAL_SEC)
