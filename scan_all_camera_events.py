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
    
    try:
        if method == 'GET':
            resp = requests.get(url, params=enc_params, headers=headers, cookies=cookies, timeout=10)
        else:
            resp = requests.post(url, data=enc_params, headers=headers, cookies=cookies, timeout=10)
            
        if resp.status_code == 200:
            text = resp.text
            if not ('error' in text or 'invalid' in text):
                dec = decrypt_rc4(s_nonce, text)
                return json.loads(dec.decode('utf-8'))
    except Exception as e:
        print(f"Error querying {url}: {e}")
    return None

with open("data/all_real_devices.json", "r", encoding="utf-8") as f:
    devices = json.load(f)

cameras = [d for d in devices if "camera" in d.get("model", "")]
print(f"Found {len(cameras)} cameras in user's account. Querying cloud events for each...")

now_ms = int(time.time() * 1000)
one_month_ago = now_ms - (30 * 24 * 3600 * 1000)

for cam in cameras:
    did = cam.get("did")
    name = cam.get("name")
    model = cam.get("model")
    is_online = cam.get("isOnline")
    
    url = "https://sg.business.smartcamera.api.io.mi.com/common/app/get/eventlist"
    res = request_smartcamera(url, method='GET', data_dict={
        'did': did,
        'model': model,
        'doorBell': False,
        'eventType': 'Default',
        'needMerge': True,
        'sortType': 'DESC',
        'region': 'SG',
        'language': 'th_TH',
        'beginTime': one_month_ago,
        'endTime': now_ms,
        'limit': 10
    })
    
    events = []
    if res and res.get("code") == 0:
        events = res.get("data", {}).get("thirdPartPlayUnits", [])
    
    # Try playlist limit
    url2 = "https://sg.business.smartcamera.api.io.mi.com/miot/camera/app/v1/alarm/playlist/limit"
    res2 = request_smartcamera(url2, method='GET', data_dict={
        'did': did,
        'region': 'SG',
        'language': 'th_TH',
        'beginTime': one_month_ago,
        'endTime': now_ms,
        'limit': 10
    })
    playlist = []
    if res2 and res2.get("code") == 0:
        playlist = res2.get("data", {}).get("playUnits", [])
        
    print(f"📹 [{did}] {name} (Online: {is_online}) -> Events: {len(events)}, Playlist units: {len(playlist)}")
    if events:
        print(f"   First event: {events[0]}")
    if playlist:
        print(f"   First playlist: {playlist[0]}")
