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
    s.settimeout(2.5)
    hello = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    s.sendto(hello, (IP, PORT))
    resp, _ = s.recvfrom(1024)
    did_bytes = resp[8:12]
    ts_int = int.from_bytes(resp[12:16], 'big')
    
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

print("=== Attempting to enable motion_record on Camera 263288748 ===")
res = call_miio("set_motion_record", ["on"])
print("set_motion_record ['on'] ->", res)

# Verify
verify = call_miio("get_prop", ["motion_record"])
print("Verified motion_record status ->", verify)
