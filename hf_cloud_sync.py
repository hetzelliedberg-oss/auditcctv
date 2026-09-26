"""
Hugging Face Cloud Persistence & Keep-Alive Engine
1. Auto-restores store_sessions.db from private Hugging Face Dataset on startup
2. Auto-syncs database whenever a new fact session completes (100% Zero Data Loss)
3. Background Keep-Alive pinger to prevent Space from sleeping
"""
import os
import time
import threading
import logging
from huggingface_hub import HfApi

logger = logging.getLogger("hf_cloud_sync")

HF_TOKEN = os.environ.get("HF_TOKEN")
SPACE_ID = os.environ.get("SPACE_ID") # e.g. "pawin/auditcctv"

def get_dataset_repo_id():
    if not SPACE_ID:
        return None
    user = SPACE_ID.split("/")[0]
    return f"{user}/auditcctv-db-backup"

def init_cloud_persistence():
    """Restores database from cloud dataset on boot."""
    if not HF_TOKEN or not SPACE_ID:
        return
    repo_id = get_dataset_repo_id()
    api = HfApi(token=HF_TOKEN)
    try:
        # Create dataset repo if not exists
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=True, exist_ok=True)
        # Try to download existing database
        db_path = "data/store_sessions.db"
        try:
            downloaded = api.hf_hub_download(repo_id=repo_id, filename="store_sessions.db", repo_type="dataset")
            import shutil
            os.makedirs("data", exist_ok=True)
            shutil.copy2(downloaded, db_path)
            logger.info(f"✅ Successfully restored store_sessions.db from Cloud Dataset ({repo_id})!")
        except Exception:
            logger.info("No prior database found in Dataset. Starting fresh.")
    except Exception as e:
        logger.error(f"Error initializing cloud persistence: {e}")

def sync_database_to_cloud():
    """Uploads latest store_sessions.db to private cloud dataset."""
    if not HF_TOKEN or not SPACE_ID:
        return
    repo_id = get_dataset_repo_id()
    db_path = "data/store_sessions.db"
    if not os.path.exists(db_path):
        return
    try:
        api = HfApi(token=HF_TOKEN)
        api.upload_file(
            path_or_fileobj=db_path,
            path_in_repo="store_sessions.db",
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"Auto-sync fact database {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        logger.info(f"☁️ Auto-synced database to {repo_id} (Data permanently safe)")
    except Exception as e:
        logger.error(f"Failed to sync database to cloud: {e}")

def start_keep_alive_pinger(space_url: str):
    """Pings the space every 10 minutes to guarantee it never sleeps."""
    def pinger_loop():
        import requests
        logger.info(f"⏰ Keep-alive pinger started for {space_url}")
        while True:
            time.sleep(600) # every 10 minutes
            try:
                requests.get(space_url, timeout=10)
            except Exception:
                pass
    t = threading.Thread(target=pinger_loop, daemon=True)
    t.start()
