import os
import json
import time
import base64
import hashlib
import hmac
import random
import requests
import sys
from Crypto.Cipher import ARC4

sys.stdout.reconfigure(encoding='utf-8')

with open("data/authenticated_credentials.json", "r", encoding="utf-8") as f:
    creds = json.load(f)

user_id = creds["userId"]
ssecurity = creds["ssecurity"]
service_token = creds["serviceToken"]

def generate_nonce(millis):
    nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder="big")
    return base64.b64encode(nonce_bytes).decode()

def signed_nonce(ssec, nonce):
    hash_obj = hashlib.sha256(base64.b64decode(ssec) + base64.b64decode(nonce))
    return base64.b64encode(hash_obj.digest()).decode("utf-8")

def encrypt_rc4(password, payload):
    r = ARC4.new(base64.b64decode(password))
    r.encrypt(bytes(1024))
    return base64.b64encode(r.encrypt(payload.encode())).decode()

def decrypt_rc4(password, payload):
    r = ARC4.new(base64.b64decode(password))
    r.encrypt(bytes(1024))
    return r.encrypt(base64.b64decode(payload))

def generate_enc_signature(url, method, signed_nonce_str, params):
    signature_params = [str(method).upper(), url.split("com")[1].replace("/app/", "/")]
    for k, v in params.items():
        signature_params.append(f"{k}={v}")
    signature_params.append(signed_nonce_str)
    signature_string = "&".join(signature_params)
    return base64.b64encode(hashlib.sha1(signature_string.encode("utf-8")).digest()).decode()

def execute_api_call(country, endpoint, params_data):
    url = f"https://{country + '.' if country != 'cn' else ''}api.io.mi.com/app{endpoint}"
    
    agent = "APP/com.xiaomi.mihome APPV/10.5.201"
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": agent,
        "Content-Type": "application/x-www-form-urlencoded",
        "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
        "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
    }
    cookies = {
        "userId": str(user_id),
        "yetAnotherServiceToken": str(service_token),
        "serviceToken": str(service_token),
        "locale": "th_TH",
        "timezone": "GMT+07:00",
        "channel": "MI_APP_STORE"
    }
    
    millis = round(time.time() * 1000)
    nonce = generate_nonce(millis)
    s_nonce = signed_nonce(ssecurity, nonce)
    
    params = params_data.copy()
    params["rc4_hash__"] = generate_enc_signature(url, "POST", s_nonce, params)
    for k, v in params_data.items():
        params[k] = encrypt_rc4(s_nonce, v)
        
    params.update({
        "signature": generate_enc_signature(url, "POST", s_nonce, params),
        "ssecurity": ssecurity,
        "_nonce": nonce,
    })
    
    resp = requests.post(url, headers=headers, cookies=cookies, params=params, timeout=10)
    if resp.status_code == 200:
        dec = decrypt_rc4(s_nonce, resp.text)
        return json.loads(dec)
    return None

if __name__ == "__main__":
    print("Querying Xiaomi Cloud across all servers (sg, cn, i2, de, us)...")
    all_devices = []

    for s in ["sg", "cn", "i2", "de", "us", "ru"]:
        try:
            # 1. Query Home room (fetch_share and fetch_own)
            home_res = execute_api_call(s, "/v2/homeroom/gethome", {
                "data": json.dumps({"fg": True, "fetch_share": True, "fetch_share_dev": True, "limit": 300, "app_ver": 7})
            })
            if home_res and home_res.get("code") == 0:
                result = home_res.get("result", {})
                homes = result.get("homelist", [])
                share_homes = result.get("share_home_list", [])
                print(f"[{s.upper()}] Found {len(homes)} homes and {len(share_homes)} shared homes!")
                
                # 2. Query device list directly
                for h in homes + share_homes:
                    h_id = h.get("id")
                    owner_id = h.get("owner") or user_id
                    dev_res = execute_api_call(s, "/v2/home/home_device_list", {
                        "data": json.dumps({
                            "home_owner": owner_id,
                            "home_id": h_id,
                            "limit": 200,
                            "get_split_device": True,
                            "support_smart_home": True
                        })
                    })
                    if dev_res and dev_res.get("code") == 0:
                        devs = dev_res.get("result", {}).get("device_list", [])
                        print(f"  👉 Home '{h.get('name')}': found {len(devs)} devices!")
                        for d in devs:
                            print(f"     📹 {d.get('name')} | Model: {d.get('model')} | DID: {d.get('did')} | Online: {d.get('isOnline')} | Token: {d.get('token')}")
                            all_devices.append(d)
                            
        except Exception as e:
            print(f"[{s}] Error: {e}")

    with open("data/all_real_devices.json", "w", encoding="utf-8") as f:
        json.dump(all_devices, f, indent=2)

    print(f"\n🎉 TOTAL REAL DEVICES RETRIEVED: {len(all_devices)}")
