import os
import json
import base64
import requests
import hashlib
import time
import urllib.parse
from Crypto.Cipher import ARC4, AES

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

did = "262682799"
file_id = "eyJkdXJhdGlvbiI6MCwib2Zmc2V0IjowLCJpSWQiOiI1ODY5MjczMDkyNzM2OTY4OTgiLCJhSWQiOiI1ODY5MjczMDkyNzM2OTY4OTciLCJmaWxlSWQiOiI1ODY5MjczMDkyNzM2OTY4OTYifQ"
img_store_id = "FREE_HOME_SUR_DEFAULT_STORE_ID"

iv_bytes = os.urandom(16)
segment_iv_b64 = base64.b64encode(iv_bytes).decode()

img_api = "https://sg.processor.smartcamera.api.io.mi.com/miot/camera/app/v1/img"
img_pms = {
    'did': did,
    'fileId': file_id,
    'stoId': img_store_id,
    'segmentIv': segment_iv_b64
}

pms, s_nonce = rc4_params('GET', img_api, {'data': json.dumps(img_pms, separators=(',', ':'))})
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
print(f"Status: {resp.status_code}")
dec = decrypt_rc4(s_nonce, resp.text)
print("Decrypted RC4 with s_nonce:", dec)
