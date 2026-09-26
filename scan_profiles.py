import os
import json
import base64
import sqlite3
import shutil
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

def scan_all_profiles():
    key = get_encryption_key()
    user_data = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
    profiles = [d for d in os.listdir(user_data) if 'Profile' in d or d == 'Default']
    
    total_found = {}
    for p in ["Profile 99", "Profile 97", "Profile 100", "Profile 79", "Default"]:
        cookie_db = os.path.join(user_data, p, "Network", "Cookies")
        if not os.path.exists(cookie_db):
            continue
        temp_db = f"temp_{p}.db"
        from locked_copy import copy_locked_file
        try:
            copy_locked_file(cookie_db, temp_db)
        except Exception as e:
            print(f"Skipping {p}: {e}")
            continue
        
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%mi.com%'")
        rows = cursor.fetchall()
        if rows:
            print(f"👉 Found {len(rows)} cookies in {p}!")
            for host_key, name, encrypted_value in rows:
                val = decrypt_value(encrypted_value, key)
                if val:
                    print(f"   [{host_key}] {name} = {val[:25]}...")
                    total_found[name] = val
        conn.close()
        try:
            os.remove(temp_db)
        except:
            pass

    with open("data/xiaomi_extracted_tokens.json", "w", encoding="utf-8") as f:
        json.dump(total_found, f, indent=2)
    print(f"\nTotal extracted: {len(total_found)} tokens!")

if __name__ == "__main__":
    scan_all_profiles()
