import os
import json
import base64
import sqlite3
import subprocess
import time
import sys
import requests
from Crypto.Cipher import AES

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import win32crypt

def get_encryption_key():
    local_state_path = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.loads(f.read())
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:]
    decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return decrypted_key

def decrypt_value(encrypted_value, key):
    try:
        iv = encrypted_value[3:15]
        payload = encrypted_value[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)
        return decrypted_pass[:-16].decode('utf-8')
    except Exception as e:
        return ""

def extract_and_fetch_devices():
    # 1. Close background chrome processes cleanly so file locks are released
    print("Stopping lingering background Chrome processes to release cookie lock...")
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    key = get_encryption_key()
    user_data = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
    profiles = [d for d in os.listdir(user_data) if 'Profile' in d or d == 'Default']

    found_cookies = {}
    service_token = None
    user_id = "6274970591"

    print("Scanning profiles for Xiaomi serviceToken...")
    for p in profiles:
        cookie_db = os.path.join(user_data, p, "Network", "Cookies")
        if not os.path.exists(cookie_db):
            continue
        try:
            conn = sqlite3.connect(cookie_db)
            cursor = conn.cursor()
            cursor.execute("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%api.io.mi.com%' OR host_key LIKE '%xiaomi.com%'")
            for host_key, name, encrypted_value in cursor.fetchall():
                val = decrypt_value(encrypted_value, key)
                if val:
                    found_cookies[name] = val
                    if name == "serviceToken":
                        service_token = val
                        print(f"🎯 FOUND serviceToken in {p}!")
                    if name == "userId":
                        user_id = val
            conn.close()
            if service_token:
                break
        except Exception as e:
            pass

    print(f"Extracted {len(found_cookies)} cookies. serviceToken found: {bool(service_token)}, userId: {user_id}")
    
    # Save cookies
    with open("data/extracted_xiaomi_tokens.json", "w", encoding="utf-8") as f:
        json.dump(found_cookies, f, indent=2)

    # 2. Re-open Chrome so user can continue browsing seamlessly
    subprocess.Popen(["cmd", "/c", "start", "chrome", "--restore-last-session"])

    return service_token, user_id, found_cookies

if __name__ == "__main__":
    extract_and_fetch_devices()
