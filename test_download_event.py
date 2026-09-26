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

# Let's inspect the 10 events of 262682799
did = "262682799"
model = "chuangmi.camera.ipc009"
now_ms = int(time.time() * 1000)
one_month_ago = now_ms - (30 * 24 * 3600 * 1000)

url = "https://sg.business.smartcamera.api.io.mi.com/common/app/get/eventlist"
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

data_dict = {
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
}

enc_params, s_nonce = rc4_params('GET', url, {'data': json.dumps(data_dict, separators=(',', ':'))})
resp = requests.get(url, params=enc_params, headers=headers, cookies=cookies)
dec = decrypt_rc4(s_nonce, resp.text)
events_data = json.loads(dec.decode('utf-8'))

units = events_data.get('data', {}).get('thirdPartPlayUnits', [])
print(f"Total events retrieved for {did}: {len(units)}")

for i, u in enumerate(units[:3]):
    file_id = u.get("fileId")
    img_store_id = u.get("imgStoreId")
    vid_store_id = u.get("videoStoreId")
    create_time = u.get("createTime")
    print(f"\n--- Event {i+1} ---")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(create_time/1000))}")
    print(f"Type: {u.get('eventType')}")
    print(f"FileId: {file_id}")
    
    # 1. Try Image URL
    img_api = "https://sg.processor.smartcamera.api.io.mi.com/miot/camera/app/v1/img"
    img_pms = {
        'did': did,
        'fileId': file_id,
        'stoId': img_store_id,
        'segmentIv': ''
    }
    pms, s_nonce_img = rc4_params('GET', img_api, {'data': json.dumps(img_pms, separators=(',', ':'))})
    pms['yetAnotherServiceToken'] = service_token
    full_img_url = f"{img_api}?{urllib.parse.urlencode(pms)}"
    print("Image Request URL generated.")
    
    # Test downloading image
    img_resp = requests.get(full_img_url, cookies=cookies, headers=headers, timeout=10)
    print(f"Image HTTP status: {img_resp.status_code}, length: {len(img_resp.content)}")
    if img_resp.status_code == 200 and len(img_resp.content) > 100:
        out_img = f"data/event_{i+1}.jpg"
        with open(out_img, "wb") as f:
            f.write(img_resp.content)
        print(f"🎉 Saved snapshot to {out_img} ({len(img_resp.content)} bytes)")
    else:
        print("Image body sample:", img_resp.text[:200])
        
    # 2. Try Video (m3u8 or mp4)
    # m3u8 endpoint
    m3u8_api = "https://sg.business.smartcamera.api.io.mi.com/common/app/m3u8"
    m3u8_pms = {
        'did': did,
        'model': model,
        'fileId': file_id,
        'isAlarm': True,
        'videoCodec': 'H265'
    }
    pms_v, s_nonce_v = rc4_params('GET', m3u8_api, {'data': json.dumps(m3u8_pms, separators=(',', ':'))})
    pms_v['yetAnotherServiceToken'] = service_token
    full_m3u8_url = f"{m3u8_api}?{urllib.parse.urlencode(pms_v)}"
    m3u8_resp = requests.get(full_m3u8_url, cookies=cookies, headers=headers, timeout=10)
    print(f"M3U8 HTTP status: {m3u8_resp.status_code}")
    if m3u8_resp.status_code == 200:
        try:
            m3u8_dec = decrypt_rc4(s_nonce_v, m3u8_resp.text)
            print("M3U8 response decrypted:", m3u8_dec.decode('utf-8')[:300])
        except Exception:
            print("M3U8 text response:", m3u8_resp.text[:300])
