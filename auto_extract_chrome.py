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
    encrypted_key = encrypted_key[5:] # Remove DPAPI prefix 'DPAPI'
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

def extract_xiaomi_cookies():
    key = get_encryption_key()
    cookie_db = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\Network\Cookies")
    temp_db = "Cookies_temp.db"
    shutil.copy2(cookie_db, temp_db)

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%mi.com%' OR host_key LIKE '%xiaomi.com%'")
    
    found_cookies = {}
    for host_key, name, encrypted_value in cursor.fetchall():
        val = decrypt_value(encrypted_value, key)
        if val:
            found_cookies[name] = val
            print(f"Cookie [{host_key}]: {name} = {val[:20]}...")
            
    conn.close()
    try:
        os.remove(temp_db)
    except:
        pass

    with open("data/xiaomi_extracted_tokens.json", "w", encoding="utf-8") as f:
        json.dump(found_cookies, f, indent=2)
    print(f"\nExtracted {len(found_cookies)} Xiaomi cookies successfully!")
    return found_cookies

if __name__ == "__main__":
    extract_xiaomi_cookies()
