import os
import json
import base64
import sqlite3
import sys
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

def inspect_profile_100():
    key = get_encryption_key()
    user_data = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
    
    for p in ["Profile 100", "Profile 97", "Profile 85"]:
        cookie_db = os.path.join(user_data, p, "Network", "Cookies")
        if not os.path.exists(cookie_db):
            continue
        try:
            conn = sqlite3.connect(cookie_db)
            cursor = conn.cursor()
            cursor.execute("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%xiaomi%' OR host_key LIKE '%mi.com%'")
            rows = cursor.fetchall()
            print(f"\nProfile {p}: found {len(rows)} cookies")
            for host, name, enc in rows:
                val = decrypt_value(enc, key)
                print(f"  [{host}] {name} = {val[:30]}...")
            conn.close()
        except Exception as e:
            print(f"Error reading {p}: {e}")

if __name__ == "__main__":
    inspect_profile_100()
