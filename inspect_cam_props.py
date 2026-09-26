import socket
import json
import hashlib
from Crypto.Cipher import AES

IP = "192.168.1.120"
PORT = 54321
TOKEN_HEX = "646b7078693339556256484e54633836"

token = bytes.fromhex(TOKEN_HEX)
key = hashlib.md5(token).digest()
iv = hashlib.md5(key + token).digest()

def call_miio(method, params=[]):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.0)
    
    # Handshake
    hello = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    s.sendto(hello, (IP, PORT))
    resp, _ = s.recvfrom(1024)
    did_bytes = resp[8:12]
    ts_int = int.from_bytes(resp[12:16], 'big')
    
    # Encrypt
    cmd = {"id": 1, "method": method, "params": params}
    payload = json.dumps(cmd).encode('utf-8')
    pad_len = 16 - (len(payload) % 16)
    payload += bytes([pad_len]) * pad_len
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    enc = cipher.encrypt(payload)
    
    new_ts = (ts_int + 1).to_bytes(4, 'big')
    packet_len = (32 + len(enc)).to_bytes(2, 'big')
    header = bytes.fromhex("2131") + packet_len + bytes(4) + did_bytes + new_ts
    checksum = hashlib.md5(header + token + enc).digest()
    full_packet = header + checksum + enc
    
    s.sendto(full_packet, (IP, PORT))
    try:
        cmd_resp, _ = s.recvfrom(2048)
        enc_resp = cmd_resp[32:]
        dec_cipher = AES.new(key, AES.MODE_CBC, iv)
        dec = dec_cipher.decrypt(enc_resp)
        pad = dec[-1]
        dec_text = dec[:-pad].decode('utf-8', errors='ignore')
        s.close()
        return json.loads(dec_text)
    except Exception as e:
        s.close()
        return {"error": str(e)}

print("=== 1. Testing get_prop ===")
test_props = [
    "power", "motion_record", "light", "flip", "full_color", "wdr", 
    "sdcard_status", "time_watermark", "alarm_status", "alarm_motion",
    "night_mode", "nas_state"
]
res = call_miio("get_prop", test_props)
print("get_prop result:", res)

print("\n=== 2. Testing get_alarm ===")
print("get_alarm:", call_miio("get_alarm"))

print("\n=== 3. Testing get_arm ===")
print("get_arm:", call_miio("get_arm"))

print("\n=== 4. Testing camera commands ===")
for m in [
    "get_record_mode",
    "get_sdcard_status",
    "get_nas_config",
    "get_rtsp_url",
    "get_live_stream",
    "take_photo",
    "get_snapshot",
    "get_alarm_record"
]:
    print(f"Method {m} -> {call_miio(m)}")
