"""
Real-Time Device Synchronizer
Continuously fetches and caches live device list and online/offline statuses from Xiaomi Cloud.
"""
import os
import json
import time
import logging
from query_devices_encrypted import execute_api_call

logger = logging.getLogger("device_sync")
DEVICES_CACHE_FILE = "data/all_real_devices.json"
CACHE_TTL = 20 # seconds

_last_sync_time = 0
_cached_devices = []

def refresh_device_list_from_cloud():
    """Fetches real-time device list directly from Xiaomi Singapore Cloud."""
    global _last_sync_time, _cached_devices
    try:
        res = execute_api_call("sg", "/home/device_list", {
            "data": json.dumps({"getVirtualModel": False, "getHuamiDevices": 0})
        })
        if res and res.get("code") == 0:
            devs = res.get("result", {}).get("list", [])
            _cached_devices = devs
            _last_sync_time = time.time()
            os.makedirs("data", exist_ok=True)
            with open(DEVICES_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(devs, f, indent=2, ensure_ascii=False)
            logger.info(f"Refreshed {len(devs)} devices from Xiaomi Cloud.")
            return devs
    except Exception as e:
        logger.error(f"Error fetching devices from cloud: {e}")

    # Fallback to local cache if available
    if os.path.exists(DEVICES_CACHE_FILE):
        try:
            with open(DEVICES_CACHE_FILE, "r", encoding="utf-8") as f:
                _cached_devices = json.load(f)
                return _cached_devices
        except Exception:
            pass
    return _cached_devices

def get_all_devices(force_refresh=False):
    global _last_sync_time, _cached_devices
    if force_refresh or (time.time() - _last_sync_time > CACHE_TTL) or not _cached_devices:
        return refresh_device_list_from_cloud()
    return _cached_devices

def get_cameras(force_refresh=False):
    devs = get_all_devices(force_refresh=force_refresh)
    return [d for d in devs if "camera" in d.get("model", "").lower()]

def get_online_cameras(force_refresh=False):
    cams = get_cameras(force_refresh=force_refresh)
    return [c for c in cams if c.get("isOnline") is True]

if __name__ == "__main__":
    cams = get_cameras(force_refresh=True)
    print(f"Total cameras: {len(cams)}")
    for c in cams:
        status = "🟢 ONLINE" if c.get("isOnline") else "⚪ offline"
        print(f"{status} | DID: {c.get('did')} | Name: {c.get('name')} | IP: {c.get('localip')}")
