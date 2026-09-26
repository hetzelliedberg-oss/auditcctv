import os
import json
import time
import base64
import hashlib
import urllib.parse
import requests
import sys
from Crypto.Cipher import ARC4, AES

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

did = "262682799"
file_id = "eyJkdXJhdGlvbiI6MCwib2Zmc2V0IjowLCJpSWQiOiI1ODY5MjczMDkyNzM2OTY4OTgiLCJhSWQiOiI1ODY5MjczMDkyNzM2OTY4OTciLCJmaWxlSWQiOiI1ODY5MjczMDkyNzM2OTY4OTYifQ"
img_store_id = "FREE_HOME_SUR_DEFAULT_STORE_ID"

# Generate 16 bytes random IV
iv_bytes = os.urandom(16)
segment_iv_b64 = base64.b64encode(iv_bytes).decode()

img_api = "https://sg.processor.smartcamera.api.io.mi.com/miot/camera/app/v1/img"
img_pms = {
    'did': did,
    'fileId': file_id,
    'stoId': img_store_id,
    'segmentIv': segment_iv_b64
}

pms, _ = rc4_params('GET', img_api, {'data': json.dumps(img_pms, separators=(',', ':'))})
pms['yetAnotherServiceToken'] = service_token
full_img_url = f"{img_api}?{urllib.parse.urlencode(pms)}"

cookies = {
    'userId': str(user_id),
    'yetAnotherServiceToken': str(service_token),
    'serviceToken': str(service_token),
    'locale': 'th_TH',
    'timezone': 'GMT+07:00'
}

resp = requests.get(full_img_url, cookies=cookies, timeout=10)
print(f"Response status: {resp.status_code}, length: {len(resp.content)}")

# Decrypt with AES-128-CBC using ssecurity as key and iv_bytes as IV
key_bytes = base64.b64decode(ssecurity)
aes_cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
dec_bytes = aes_cipher.decrypt(resp.content)

print(f"Decrypted bytes len: {len(dec_bytes)}, magic: {dec_bytes[:10].hex()}")
if dec_bytes[:2] == b'\xff\xd8':
    print("🎯 BINGO! Valid JPEG Image magic (0xFFD8) detected!")
    out_file = "data/real_camera_motion_snapshot.jpg"
    with open(out_file, "wb") as f:
        f.write(dec_bytes)
    print(f"Saved real camera motion snapshot to {out_file}!")
else:
    print("First 50 decrypted bytes:", dec_bytes[:50])
