import os
import json
import time
import base64
import hashlib
import urllib.parse
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

def sha1_sign(method, url, dat: dict, nonce):
    path = urllib.parse.urlparse(url).path
    if path[:5] == '/app/':
        path = path[4:]
    arr = [str(method).upper(), path]
    for k, v in dat.items():
        arr.append(f'{k}={v}')
    arr.append(nonce)
    raw = hashlib.sha1('&'.join(arr).encode('utf-8')).digest()
    return base64.b64encode(raw).decode()

def rc4_params(method, url, params: dict):
    millis = round(time.time() * 1000)
    nonce = generate_nonce(millis)
    s_nonce = signed_nonce(ssecurity, nonce)
    
    p = params.copy()
    p['rc4_hash__'] = sha1_sign(method, url, p, s_nonce)
    for k, v in params.items():
        p[k] = encrypt_rc4(s_nonce, v)
    p.update({
        'signature': sha1_sign(method, url, p, s_nonce),
        'ssecurity': ssecurity,
        '_nonce': nonce,
    })
    return p, s_nonce

def request_smartcamera(url, method='GET', data_dict=None):
    headers = {
        'MIOT-ENCRYPT-ALGORITHM': 'ENCRYPT-RC4',
        'Accept-Encoding': 'identity',
        'User-Agent': 'APP/com.xiaomi.mihome APPV/10.5.201'
    }
    cookies = {
        'userId': str(user_id),
        'yetAnotherServiceToken': str(service_token),
        'serviceToken': str(service_token),
        'locale': 'th_TH',
        'timezone': 'GMT+07:00'
    }
    
    raw_params = {}
    if data_dict is not None:
        raw_params['data'] = json.dumps(data_dict, separators=(',', ':'))
        
    enc_params, s_nonce = rc4_params(method, url, raw_params)
    
    if method == 'GET':
        resp = requests.get(url, params=enc_params, headers=headers, cookies=cookies, timeout=10)
    else:
        resp = requests.post(url, data=enc_params, headers=headers, cookies=cookies, timeout=10)
        
    print(f"[{method}] {url} -> Status: {resp.status_code}")
    if resp.status_code == 200:
        text = resp.text
        if 'error' in text or 'invalid' in text or '"code":' in text:
            print("Raw text response:", text[:300])
        else:
            try:
                dec = decrypt_rc4(s_nonce, text)
                dec_json = json.loads(dec.decode('utf-8'))
                return dec_json
            except Exception as e:
                print("Decryption error:", e, text[:200])
    return None

now_ms = int(time.time() * 1000)
one_day_ago_ms = now_ms - (7 * 24 * 3600 * 1000) # Past 7 days

print("=== 1. Testing eventlist on SG and Default servers ===")
for host in ["sg.business.smartcamera.api.io.mi.com", "business.smartcamera.api.io.mi.com"]:
    url = f"https://{host}/common/app/get/eventlist"
    res = request_smartcamera(url, method='GET', data_dict={
        'did': '263288748',
        'model': 'chuangmi.camera.ipc009',
        'doorBell': False,
        'eventType': 'Default',
        'needMerge': True,
        'sortType': 'DESC',
        'region': 'SG',
        'language': 'th_TH',
        'beginTime': one_day_ago_ms,
        'endTime': now_ms,
        'limit': 10
    })
    print("Result eventlist:", json.dumps(res, indent=2, ensure_ascii=False) if res else "None")

print("\n=== 2. Testing alarm playlist limit ===")
for host in ["sg.business.smartcamera.api.io.mi.com", "business.smartcamera.api.io.mi.com"]:
    url = f"https://{host}/miot/camera/app/v1/alarm/playlist/limit"
    res = request_smartcamera(url, method='GET', data_dict={
        'did': '263288748',
        'region': 'SG',
        'language': 'th_TH',
        'beginTime': one_day_ago_ms,
        'endTime': now_ms,
        'limit': 10
    })
    print("Result playlist:", json.dumps(res, indent=2, ensure_ascii=False) if res else "None")
