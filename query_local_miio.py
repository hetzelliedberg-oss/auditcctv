import socket
import json
import hashlib
from Crypto.Cipher import AES

def send_miio_cmd(ip, did_hex, token_hex, cmd_dict):
    token = bytes.fromhex(token_hex)
    key = hashlib.md5(token).digest()
    iv = hashlib.md5(key + token).digest()
    
    payload = json.dumps(cmd_dict).encode('utf-8')
    # Pad to 16 bytes (PKCS7 or zeros)
    pad_len = 16 - (len(payload) % 16)
    payload += bytes([pad_len]) * pad_len
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    enc_payload = cipher.encrypt(payload)
    
    packet_len = 32 + len(enc_payload)
    header = bytes.fromhex("2131") + packet_len.to_bytes(2, 'big') + bytes(4) + bytes.fromhex(did_hex) + bytes(4)
    
    # Checksum = MD5(header + token + enc_payload)
    checksum = hashlib.md5(header + token + enc_payload).digest()
    packet = header + checksum + enc_payload
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2.0)
    s.sendto(packet, (ip, 54321))
    try:
        resp, addr = s.recvfrom(2048)
        print("Received response length:", len(resp))
        resp_payload = resp[32:]
        dec_cipher = AES.new(key, AES.MODE_CBC, iv)
        dec_payload = dec_cipher.decrypt(resp_payload)
        # unpad
        unpad_len = dec_payload[-1]
        print("DECRYPTED:", dec_payload[:-unpad_len].decode('utf-8', errors='ignore'))
    except Exception as e:
        print("Error/Timeout:", e)
    s.close()

if __name__ == "__main__":
    for tok in ["ffffffffffffffffffffffffffffffff", "00000000000000000000000000000000"]:
        print(f"\nTrying token: {tok}")
        send_miio_cmd("192.168.1.120", "0fb177ac", tok, {"id": 1, "method": "miIO.info", "params": []})
